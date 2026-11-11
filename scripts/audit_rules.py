#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""远程分流规则语义审计脚本（v2，真机裁决修正版）。

模拟 Quantumult X 的分流匹配语义，对 [filter_remote] 全部远程清单做四类检查，
并输出探针表：

  语义模型（官方 sample.conf + 社区文档 + 2026-11-11 真机实测裁决，详见
  .trellis/tasks/11-10-remote-rules-deep-maintenance/research/qx-official-semantics.md）：
  1. host 类"最具体优先"（跨清单生效）：host 精确层 → host-suffix 层
     （value 最长者赢，等长取"本地→远程清单声明序→行序"首个）→
     host-wildcard 层 → host-keyword 层；
  2. host 类未命中才做 DNS 解析，随后评估 IP 类规则
     （ip-cidr/ip6-cidr/geoip）：本地 → 远程，按序；
  3. 都未命中走本地 final 兜底（本地 final 不短路远程链）。
  user-agent 规则仅在请求携带对应 UA 时参与，探针不模拟（文档化近似）。

四类检查：
  A. force-policy 引用但 [policy] 不存在的策略组（FAIL）
  B. CIDR 掩码 / IP-ASN / IDN（非 ASCII 域名）格式错误（FAIL）
  C. 同清单内永不可达的死规则（最具体优先语义下仅"类型+值完全相同的
     重复条目"不可达；自维护清单 FAIL，上游清单 INFO）
  D. 跨清单接管（同值重复自维护清单 FAIL；子域接管：自维护清单被
     更具体规则接管且策略不同 WARN，其余 INFO）

另含：探针表（≥30 代表性域名 → 预期策略 vs 实际命中）、
三处同步检查（config/filter_remote.conf / profile/QX_Config.conf /
config/quantumultx.conf.template / checks/rule_urls.txt）。

自维护清单（rules/ 目录）优先读取本地文件而非远程 URL，便于在推送前审计。
geoip 模拟依赖 APNIC delegated 数据（缓存 24h，不可用时相关探针记 SKIP）。

用法：
    python3 scripts/audit_rules.py [--fresh] [--offline] [--timeout 60]
                                   [--workers 6] [--device-checklist]
                                   [--probe host=期望tag ...]

退出码：0 无 FAIL；1 存在 FAIL；2 配置/网络错误。
"""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
REMOTE_CONF = os.path.join(BASE_DIR, "config", "filter_remote.conf")
LOCAL_CONF = os.path.join(BASE_DIR, "config", "filter_local.conf")
POLICY_CONF = os.path.join(BASE_DIR, "config", "policy.conf")
PROFILE_CONF = os.path.join(BASE_DIR, "profile", "QX_Config.conf")
TEMPLATE_CONF = os.path.join(BASE_DIR, "config", "quantumultx.conf.template")
RULE_URLS_TXT = os.path.join(BASE_DIR, "checks", "rule_urls.txt")
RULES_DIR = os.path.join(BASE_DIR, "rules")

CACHE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "qx-rule-audit-cache")
CACHE_TTL = 6 * 3600
APNIC_CACHE_TTL = 24 * 3600
APNIC_URL = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
DOH_URL = "https://223.5.5.5/resolve?name={}&type=A"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RuleAudit/1.0"
MAX_BODY_BYTES = 16 * 1024 * 1024

BUILTIN_POLICIES = {"direct", "proxy", "reject"}

# 规则类型归一化（Surge 风格 domain 系列等价于 QX host 系列）
HOST_TYPES = {"host", "domain",
              "host-suffix", "domain-suffix",
              "host-keyword", "domain-keyword",
              "host-wildcard", "domain-wildcard"}
IP_TYPES = {"ip-cidr", "ip6-cidr", "geoip", "ip-asn"}
KNOWN_TYPES = HOST_TYPES | IP_TYPES | {"user-agent", "final"}

# 自维护清单的 URL 文件名（审计时优先读本地 rules/ 下同名文件）
SELF_HOSTED_MARKER = "taotie6/QuantumultX"


def normalize_type(t):
    t = t.strip().lower()
    return {"domain": "host", "domain-suffix": "host-suffix",
            "domain-keyword": "host-keyword", "domain-wildcard": "host-wildcard",
            "ip-cidr6": "ip6-cidr"}.get(t, t)


def wildcard_to_regex(value):
    """把 QX 通配符（* 与 ?）转换为整域锚定的正则。"""
    escaped = re.escape(value.lower())
    escaped = escaped.replace(r"\*", ".*").replace(r"\?", ".")
    return re.compile("^" + escaped + "$")


class Rule(object):
    __slots__ = ("rtype", "value", "policy", "lineno", "source", "raw")

    def __init__(self, rtype, value, policy, lineno, source, raw):
        self.rtype = rtype      # 归一化类型
        self.value = value      # 匹配值（域名/IP/ASN/geoip 国家码）
        self.policy = policy    # 策略字段（远程清单配合 force-policy 时被忽略）
        self.lineno = lineno
        self.source = source    # tag 或 "filter_local"
        self.raw = raw

    def __repr__(self):  # pragma: no cover - 调试用
        return "{}:{},{} (line {})".format(self.source, self.rtype, self.value, self.lineno)


# ----------------------------------------------------------- 配置解析 --

def parse_remote_conf(path):
    """解析 [filter_remote] 维护源，返回 [(url, params)]，保持声明顺序。"""
    entries = []
    in_section = False
    for lineno, raw in enumerate(open(path, encoding="utf-8"), start=1):
        line = raw.strip()
        if line.startswith("["):
            in_section = (line == "[filter_remote]")
            continue
        if not in_section or not line or line.startswith(("#", ";")):
            continue
        if not line.startswith("http"):
            raise ValueError("{} 第 {} 行不是 URL 开头: {}".format(path, lineno, line))
        parts = [p.strip() for p in line.split(",")]
        url = parts[0]
        params = {}
        for kv in parts[1:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip().lower()] = v.strip()
            elif kv:
                params[kv.lower()] = None
        entries.append((url, params))
    return entries


def extract_remote_section(path):
    """从完整配置（profile/模板）提取 [filter_remote] 段的行列表。"""
    lines = []
    in_section = False
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if line.startswith("["):
            in_section = (line == "[filter_remote]")
            continue
        if in_section and line and not line.startswith(("#", ";")):
            lines.append(line)
    return lines


def parse_remote_lines(lines, origin):
    """把 URL 行解析为 (url, params)，供三处同步比较。"""
    entries = []
    for lineno, line in enumerate(lines, start=1):
        if not line.startswith("http"):
            raise ValueError("{} 第 {} 行不是 URL 开头: {}".format(origin, lineno, line))
        parts = [p.strip() for p in line.split(",")]
        params = {}
        for kv in parts[1:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip().lower()] = v.strip()
        entries.append((parts[0], params))
    return entries


def parse_local_conf(path):
    """解析 [filter_local] 维护源为规则列表。"""
    rules = []
    in_section = False
    for lineno, raw in enumerate(open(path, encoding="utf-8"), start=1):
        line = raw.strip()
        if line.startswith("["):
            in_section = (line == "[filter_local]")
            continue
        if not in_section or not line or line.startswith(("#", ";")):
            continue
        parts = [p.strip() for p in line.split(",")]
        rules.append(Rule(normalize_type(parts[0]), parts[1],
                          parts[2] if len(parts) > 2 else "",
                          lineno, "filter_local", line))
    return rules


def parse_policy_conf(path):
    """解析 [policy] 段，返回 {策略名: 候选列表}。"""
    policies = {}
    in_section = False
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if line.startswith("["):
            in_section = (line == "[policy]")
            continue
        if not in_section or not line or line.startswith(("#", ";")):
            continue
        m = re.match(r"^(\S+)\s*=\s*([^,]+),(.*)$", line)
        if not m:
            continue
        name = m.group(2).strip()
        candidates = [c.strip() for c in m.group(3).split(",")
                      if c.strip() and "=" not in c]
        policies[name] = candidates
    return policies


def parse_list_text(text, tag):
    """解析远程清单文本为规则列表（兼容 Surge 风格前缀与无策略列）。"""
    rules = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(("#", ";", "!")):
            continue
        parts = [p.strip() for p in line.split(",")]
        rtype = normalize_type(parts[0])
        value = parts[1] if len(parts) > 1 else ""
        policy = parts[2] if len(parts) > 2 else ""
        rules.append(Rule(rtype, value, policy, lineno, tag, line))
    return rules


# ----------------------------------------------------------- 资源下载 --

def cache_path(key):
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode("utf-8")).hexdigest())


def cached_fetch(url, ttl, timeout, fresh=False, offline=False):
    """带磁盘缓存的下载，返回 (text, 来源说明, error)。"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cpath = cache_path(url)
    if not fresh and os.path.exists(cpath):
        age = time.time() - os.path.getmtime(cpath)
        if age < ttl:
            with open(cpath, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read(), "缓存({}s 前)".format(int(age)), None
    if offline:
        if os.path.exists(cpath):
            with open(cpath, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read(), "缓存(过期,离线模式)", None
        return None, None, "离线模式且无缓存"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(3):  # 连接级错误重试 2 次（对齐 check_rules.py）
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return None, None, "HTTP {}".format(resp.status)
                body = resp.read(MAX_BODY_BYTES)
            break
        except Exception as exc:  # 网络层错误重试后统一上报
            last_err = exc
            if attempt < 2:
                time.sleep(2)
    else:
        return None, None, "下载失败: {}".format(last_err)
    text = body.decode("utf-8", errors="replace")
    with open(cpath, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text, "网络", None


def resolve_host(host, timeout):
    """解析域名 IPv4：优先阿里 DoH JSON 接口（避免本机 DNS 污染），失败回退系统。"""
    try:
        req = urllib.request.Request(DOH_URL.format(urllib.parse.quote(host)),
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for ans in data.get("Answer", []):
            if ans.get("type") == 1:  # A 记录
                return ans["data"]
    except Exception:
        pass
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        return infos[0][4][0]
    except Exception:
        return None


def load_cn_networks(timeout, fresh=False, offline=False):
    """解析 APNIC delegated 数据中的 CN IPv4/IPv6 段；失败返回 None。"""
    text, _, err = cached_fetch(APNIC_URL, APNIC_CACHE_TTL, timeout,
                                fresh=fresh, offline=offline)
    if err:
        return None
    networks = []
    for line in text.splitlines():
        if line.startswith("#") or "|" not in line:
            continue
        fields = line.split("|")
        if len(fields) < 7 or fields[1] != "CN":
            continue
        registry, cc, typ, start, value, _date, _status = fields[:7]
        try:
            if typ == "ipv4":
                # value 是地址数（2 的幂），前缀 = 32 - log2(value)
                count = int(value)
                prefix = 33 - count.bit_length()
                networks.append(ipaddress.ip_network(
                    "{}/{}".format(start, prefix), strict=False))
            elif typ == "ipv6":
                networks.append(ipaddress.ip_network("{}/{}".format(start, value)))
        except ValueError:
            continue
    return networks


# ----------------------------------------------------------- 匹配引擎 --

def rule_matches_host(rule, host):
    t, v = rule.rtype, rule.value.lower()
    if t == "host":
        return host == v
    if t == "host-suffix":
        return host == v or host.endswith("." + v)
    if t == "host-keyword":
        return v in host
    if t == "host-wildcard":
        return bool(wildcard_to_regex(rule.value).match(host))
    return False


def rule_matches_ip(rule, ip, cn_networks):
    t, v = rule.rtype, rule.value
    try:
        if t == "ip-cidr":
            return ip.version == 4 and ip in ipaddress.ip_network(v, strict=False)
        if t == "ip6-cidr":
            return ip.version == 6 and ip in ipaddress.ip_network(v, strict=False)
        if t == "geoip":
            if cn_networks is None or v.lower() != "cn":
                return None  # 无法判定
            return any(ip in n for n in cn_networks)
    except ValueError:
        return False
    return False  # ip-asn / user-agent 不参与探针模拟


class Engine(object):
    """匹配引擎（v2）：host 类最具体优先（_match_host）→ IP 相 → 本地 final。"""

    def __init__(self, local_rules, remote_lists, cn_networks, resolver):
        self.local_rules = local_rules        # [Rule]
        self.remote_lists = remote_lists      # [(tag, [Rule])] 声明序
        self.cn_networks = cn_networks
        self.resolver = resolver

    def match(self, probe):
        """probe 为域名或 IP 字符串，返回 (命中描述, 规则, unresolved)。

        host 类采用真机裁决修正的"最具体优先"模型（见 research/
        qx-official-semantics.md §4）：host 精确层 → host-suffix 层
        （value 最长者赢，等长取"本地→清单序→行序"首个）→ host-wildcard
        层 → host-keyword 层。"""
        try:
            ip = ipaddress.ip_address(probe)
            host = None
        except ValueError:
            ip, host = None, probe.lower()

        if host is not None:
            hit = self._match_host(host)
            if hit:
                return hit
        else:
            return self._match_ip(str(ip), ip)
        # host 未命中 → 解析后进入 IP 相
        resolved = self.resolver(host) if host else None
        if resolved is None:
            return "未解析(跳过 IP 相)", None, True
        ip_obj = ipaddress.ip_address(resolved)
        return self._match_ip(host + "→" + resolved, ip_obj)

    def _match_host(self, host):
        """按类型层级（host > suffix(长优先) > wildcard > keyword）匹配。
        返回 (描述, 规则, False) 或 None。"""
        def scan(rtype):
            """该类型层内收集命中：返回 [(order, rule)]，order 为声明序。"""
            hits = []
            for rule in self.local_rules:  # 本地最先
                if rule.rtype == rtype and rule_matches_host(rule, host):
                    hits.append((-1, rule))
            for idx, (tag, rules) in enumerate(self.remote_lists):
                for rule in rules:
                    if rule.rtype == rtype and rule_matches_host(rule, host):
                        hits.append((idx, rule))
            return hits

        # host 精确层：命中即停（等价规则取声明序首个）
        hits = scan("host")
        if hits:
            _, rule = hits[0]
            return self._desc(rule), rule, False
        # host-suffix 层：更长 value 更具体
        hits = scan("host-suffix")
        if hits:
            _, rule = max(hits, key=lambda h: (len(h[1].value), -h[0]))
            return self._desc(rule), rule, False
        # host-wildcard 层：取声明序首个
        hits = scan("host-wildcard")
        if hits:
            _, rule = hits[0]
            return self._desc(rule), rule, False
        # host-keyword 层：取声明序首个
        hits = scan("host-keyword")
        if hits:
            _, rule = hits[0]
            return self._desc(rule), rule, False
        return None

    def _desc(self, rule):
        if rule.source == "filter_local":
            return "local({},{})".format(rule.rtype, rule.value)
        return "{}(line {},{})".format(rule.source, rule.lineno,
                                       rule.rtype + "," + rule.value)

    def _match_ip(self, desc, ip_obj):
        for rule in self.local_rules:
            if rule.rtype in IP_TYPES:
                hit = rule_matches_ip(rule, ip_obj, self.cn_networks)
                if hit:
                    return "local({},{}) {}".format(rule.rtype, rule.value, desc), rule, False
        for tag, rules in self.remote_lists:
            for rule in rules:
                if rule.rtype in IP_TYPES:
                    hit = rule_matches_ip(rule, ip_obj, self.cn_networks)
                    if hit is None:
                        continue
                    if hit:
                        return "{}(line {},{}) {}".format(tag, rule.lineno,
                                                          rule.rtype + "," + rule.value, desc), rule, False
        for rule in self.local_rules:
            if rule.rtype == "final":
                return "local(final) {}".format(desc), rule, False
        return "无 final 兜底 {}".format(desc), None, True


# ------------------------------------------------------- 遮蔽与死规则 --

def find_cross_list_shadow(remote_lists, force_policies):
    """跨清单接管分析（真机裁决修正版）：QX host 类为"最具体优先"，
    完全遮蔽的概念不复存在。改报两类：
    - exact-dup：HOST,v 与更早清单 HOST,v 完全重复（后者永不可达）
    - subdomain：SUFFIX,v 的子域被任意清单更具体规则（精确 HOST 或
      更长 SUFFIX）接管（子域级冲突，不影响 v 自身与多数子域）
    返回 [(winner_tag, loser_tag, rule, 同策略, kind)]。"""
    # children[parent] = (kind, value, list_idx, rule)；kind: 'host'/'suffix'
    # exact_hosts[value] = (list_idx, tag, rule)：HOST 精确值索引
    children = {}
    exact_hosts = {}
    tags = []
    for idx, (tag, rules) in enumerate(remote_lists):
        tags.append(tag)
        for rule in rules:
            v = rule.value.lower()
            if rule.rtype == "host":
                kind = "host"
                exact_hosts.setdefault(v, (idx, tag, rule))
            elif rule.rtype == "host-suffix":
                kind = "suffix"
            else:
                continue
            parts = v.split(".")
            for i in range(len(parts) - 1):
                parent = ".".join(parts[i + 1:])
                children.setdefault(parent, []).append((kind, v, idx, rule))
    result = []
    for j, (tag, rules) in enumerate(remote_lists):
        for rule in rules:
            v = rule.value.lower()
            if rule.rtype == "host":
                # 完全重复：更早清单同值 HOST
                if v in exact_hosts and exact_hosts[v][0] < j:
                    idx, wtag, _r = exact_hosts[v]
                    result.append((wtag, tag, rule,
                                   force_policies.get(wtag) == force_policies.get(tag),
                                   "exact-dup"))
            elif rule.rtype == "host-suffix":
                # 子域接管：任意清单（含更晚）的 HOST,w（w==v 或 w 以 .v 结尾）
                # 或更长 SUFFIX,w（w 以 .v 结尾）
                best = None
                for kind, w, idx, r in children.get(v, []):
                    if kind == "host" and (w == v or w.endswith("." + v)):
                        cand = (0, idx, kind, w)   # HOST 层级最高
                    elif kind == "suffix" and w.endswith("." + v):
                        cand = (1, idx, kind, w)
                    else:
                        continue
                    if best is None or cand[:2] < best[:2]:
                        best = cand
                if best:
                    wtag = tags[best[1]]
                    result.append((wtag, tag, rule,
                                   force_policies.get(wtag) == force_policies.get(tag),
                                   "subdomain"))
    return result



def find_intra_list_dead(rules, tag):
    """同清单内死规则（真机裁决修正版）：最具体优先语义下，不同长度的
    SUFFIX 互不覆盖、KEYWORD 不覆盖 SUFFIX——仅"类型+值完全相同的更早
    条目（重复）"才永不可达。返回 [(rule, 覆盖者描述)]。"""
    dead = []
    seen = {}
    for rule in rules:
        if rule.rtype in HOST_TYPES:
            key = (rule.rtype, rule.value.lower())
            if key in seen:
                dead.append((rule, "与第 {} 行重复".format(seen[key])))
            else:
                seen[key] = rule.lineno
    return dead


# ----------------------------------------------------------- 格式检查 --

def check_formats(rules, tag):
    """CIDR/ASN/IDN 格式检查，返回 [(rule, 级别, 说明)]。"""
    issues = []
    for rule in rules:
        t, v = rule.rtype, rule.value
        if t not in KNOWN_TYPES:
            issues.append((rule, "WARN", "未知规则类型 {}".format(t)))
            continue
        if t in ("host", "host-suffix", "host-keyword", "host-wildcard"):
            if any(ord(c) > 127 for c in v):
                issues.append((rule, "FAIL", "域名含非 ASCII 字符（IDN 应转 punycode）"))
            elif t in ("host", "host-suffix") and v and not re.match(
                    r"^[a-z0-9*?.-]+$", v.lower()):
                issues.append((rule, "WARN", "域名含异常字符: {}".format(v)))
        elif t in ("ip-cidr", "ip6-cidr"):
            try:
                net = ipaddress.ip_network(v, strict=True)
                want = 4 if t == "ip-cidr" else 6
                if net.version != want:
                    issues.append((rule, "FAIL",
                                   "IPv{} 地址出现在 {} 规则".format(net.version, t)))
            except ValueError as exc:
                try:
                    ipaddress.ip_network(v, strict=False)
                    issues.append((rule, "WARN", "CIDR 主机位未清零: {}".format(v)))
                except ValueError:
                    issues.append((rule, "FAIL", "无法解析 CIDR: {} ({})".format(v, exc)))
        elif t == "ip-asn":
            if not v.isdigit():
                issues.append((rule, "FAIL", "IP-ASN 值不是纯数字: {}".format(v)))
        elif t == "geoip":
            if not re.match(r"^[a-z]{2}$", v.lower()):
                issues.append((rule, "FAIL", "geoip 值不是两位国家码: {}".format(v)))
    return issues


# ------------------------------------------------------------- 探针表 --

# (探针, 期望命中, 说明)。期望值独立于脚本推导（研究结论），非脚本自证。
# 带注记的探针记录"现状即预期"的已知遮蔽行为；其余期望为本次维护后的目标态。
PROBES = [
    # 国内大站
    ("www.baidu.com", "Mainland", ""),
    ("www.taobao.com", "Mainland", ""),
    ("www.weibo.com", "Mainland", ""),
    ("www.bilibili.com", "Mainland", ""),
    ("www.jd.com", "Mainland", ""),
    ("mail.163.com", "Mainland", ""),
    ("www.qq.com", "Mainland", ""),
    # AI
    ("chatgpt.com", "AI", ""),
    ("claude.ai", "AI", ""),
    ("gemini.google.com", "AI", ""),
    ("grok.com", "AI", ""),
    ("mistral.ai", "AI", ""),
    ("www.midjourney.com", "AI", "2026-11-11 合并上游 A 组新增"),
    ("api.cloudflare.com", "AI", "2026-11-11 合并上游 B 组新增（exact-host）"),
    ("storage.googleapis.com", "AI", "2026-11-11 合并上游 B 组新增（exact-host）"),
    ("copilot.microsoft.com", "Outside",
     "真机证实：Global.list 精确 HOST,copilot.microsoft.com（host 层级最高），维持现状"),
    # 流媒体
    ("www.netflix.com", "Netflix", ""),
    ("www.youtube.com", "YouTube", ""),
    ("open.spotify.com", "Spotify", ""),
    ("www.disneyplus.com", "GlobalMedia", ""),
    ("www.hulu.com", "GlobalMedia", ""),
    ("web.telegram.org", "Telegram", ""),
    ("x.com", "Twitter", ""),
    # 广告
    ("1rtb.com", "Ads", ""),
    ("a.market.xiaomi.com", "Ads",
     "真机语义（最长 SUFFIX 优先）：AWAvenue 的 a.market.xiaomi.com 赢过 China.list 的 xiaomi.com"),
    ("proxima.midjourney.com", "Advertising",
     "真机证实：Advertising.list 更长 SUFFIX 接管 midjourney 统计子域"),
    ("doubleclick.net", "Google", ""),
    # 个人直连例外
    ("mp.weixin.qq.com", "WeChatAdSettlement", ""),
    ("weheatmap.woa.com", "WeChatAdSettlement", "HOST 精确层级赢过 Mainland/WeChat 的 SUFFIX（真机语义）"),
    ("xiaoyuzhoufm.com", "Xiaoyuzhou", ""),
    ("media.xyzcdn.net", "Xiaoyuzhou", "2026-11-11 删除死规则后由 xyzcdn.net 覆盖"),
    ("docs.qianjiapp.com", "Qianji", ""),
    ("longbridge.com", "Longbridge", ""),
    # 苹果/微软（收窄后）
    ("www.apple.com", "Apple", "2026-11-11 AppleIntelligence 收窄后回落 Apple.list"),
    ("www.icloud.com", "Apple", "同上"),
    ("api.smoot.apple.com", "AppleIntelligence", "收窄后保留（Apple 官方 101555 Siri/搜索）"),
    ("guzzoni.apple.com", "AppleIntelligence", "收窄后保留（Siri 请求域）"),
    ("office.com", "Mainland",
     "已知遮蔽：China.list 含 host-suffix,office.com（21Vianet/Office CN CDN），先于 Microsoft.list，维持现状"),
    # 代理名单与兜底
    ("www.pixiv.net", "Outside", ""),
    ("cdn.jsdelivr.net", "Outside", ""),
    ("www.wikipedia.org", "Outside", ""),
    ("example.com", "final", "host 未命中 + 非 CN IP → 本地 final"),
    ("114.114.114.114", "geoip", "纯 IP：China.list 无 17 段含此址 → 本地 geoip,cn"),
]


def expected_matches(actual, expected):
    """期望值匹配：expected 为 tag 名 / 'final' / 'geoip'。"""
    if expected in ("final", "geoip"):
        return actual.startswith("local({}".format(expected if expected == "final" else "geoip"))
    return actual.startswith(expected + "(")


# ------------------------------------------------------------- 主流程 --

SELF_TAGS = {"Qianji", "WeChatAdSettlement", "Xiaoyuzhou", "Longbridge",
             "AI", "AppleIntelligence"}


def load_remote_lists(remotes, args):
    """下载/读取全部远程清单，返回 [(tag, rules)] 与错误列表。"""
    import concurrent.futures
    lists = [None] * len(remotes)
    errors = []

    def _load(idx_url):
        idx, (url, params) = idx_url
        tag = params.get("tag", "list-{}".format(idx))
        # 自维护清单优先读本地文件（推送前审计）
        if SELF_HOSTED_MARKER in url:
            name = url.rsplit("/", 1)[-1]
            local = os.path.join(RULES_DIR, name)
            if os.path.exists(local):
                text = open(local, encoding="utf-8").read()
                return idx, tag, parse_list_text(text, tag), "本地文件 rules/{}".format(name), None
        text, src, err = cached_fetch(url, CACHE_TTL, args.timeout,
                                      fresh=args.fresh, offline=args.offline)
        if err:
            return idx, tag, None, None, err
        return idx, tag, parse_list_text(text, tag), src, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for idx, tag, rules, src, err in pool.map(_load, enumerate(remotes)):
            if err:
                errors.append("{} ({}): {}".format(tag, remotes[idx][0], err))
                lists[idx] = (tag, [])
            else:
                lists[idx] = (tag, rules)
    return lists, errors


def sync_check(remotes):
    """三处 [filter_remote] + rule_urls.txt 一致性检查，返回 [(级别, 说明)]。"""
    issues = []
    canonical = [(url, params.get("tag"), params.get("force-policy"),
                  params.get("update-interval")) for url, params in remotes]

    profile = parse_remote_lines(extract_remote_section(PROFILE_CONF), PROFILE_CONF)
    template = parse_remote_lines(extract_remote_section(TEMPLATE_CONF), TEMPLATE_CONF)
    for name, parsed in (("profile/QX_Config.conf", profile),
                         ("config/quantumultx.conf.template", template)):
        sig = [(url, p.get("tag"), p.get("force-policy"), p.get("update-interval"))
               for url, p in parsed]
        if sig != canonical:
            issues.append(("FAIL", "{} 与 config/filter_remote.conf 不一致（{} 条 vs {} 条）"
                           .format(name, len(sig), len(canonical))))
            for a, b in zip(canonical, sig):
                if a != b:
                    issues.append(("FAIL", "  维护源: {} / {} 处: {}".format(a, name, b)))
                    break

    # rule_urls.txt 分区解析
    section = None
    url_sections = {}
    for raw in open(RULE_URLS_TXT, encoding="utf-8"):
        line = raw.strip()
        m = re.match(r"^#\s*----\s*(.+?)\s*----", line)
        if m:
            section = m.group(1)
            continue
        if line.startswith("http"):
            url_sections.setdefault(section, []).append(line)
    filter_urls = url_sections.get("远程分流规则 [filter_remote]", [])
    expected_urls = {url for url, _ in remotes}
    got = set(filter_urls)
    if got != expected_urls:
        for missing in sorted(expected_urls - got):
            issues.append(("FAIL", "rule_urls.txt filter 区段缺少: {}".format(missing)))
        for extra in sorted(got - expected_urls):
            issues.append(("FAIL", "rule_urls.txt filter 区段多余: {}".format(extra)))
    for sec, urls in url_sections.items():
        for u in urls:
            if u.endswith(".list") and "filter" not in sec:
                issues.append(("FAIL", "rule_urls.txt 的 .list 文件落在非 filter 区段: {} ({})"
                               .format(u, sec)))
    return issues


def main(argv=None):
    parser = argparse.ArgumentParser(description="Quantumult X 远程分流规则语义审计")
    parser.add_argument("--fresh", action="store_true", help="忽略缓存重新下载")
    parser.add_argument("--offline", action="store_true", help="仅使用缓存")
    parser.add_argument("--timeout", type=int, default=60, help="下载超时秒数")
    parser.add_argument("--workers", type=int, default=6, help="下载并发数")
    parser.add_argument("--device-checklist", action="store_true",
                        help="输出真机导入核对单（探针 + 导入检查项）")
    parser.add_argument("--probe", action="append", default=[],
                        metavar="host=期望tag", help="追加自定义探针")
    args = parser.parse_args(argv)

    if args.device_checklist:
        return device_checklist(args)

    try:
        remotes = parse_remote_conf(REMOTE_CONF)
        local_rules = parse_local_conf(LOCAL_CONF)
        policies = parse_policy_conf(POLICY_CONF)
    except (OSError, ValueError) as exc:
        print("配置错误: {}".format(exc), file=sys.stderr)
        return 2
    if not remotes:
        print("错误: [filter_remote] 为空", file=sys.stderr)
        return 2

    failures = []   # FAIL 级
    warnings = []   # WARN 级
    infos = []      # INFO 级

    # ---- 检查 1：force-policy 与策略组引用 ----
    force_policies = {}
    for url, params in remotes:
        tag = params.get("tag")
        fp = params.get("force-policy")
        if fp:
            force_policies[tag] = fp
            if fp not in policies and fp not in BUILTIN_POLICIES:
                failures.append("force-policy 引用不存在的策略组: {} -> {}".format(tag, fp))
    for name, candidates in policies.items():
        for cand in candidates:
            if cand not in policies and cand not in BUILTIN_POLICIES:
                failures.append("策略组 {} 引用了不存在的子策略: {}".format(name, cand))

    # ---- 同步检查 ----
    for level, msg in sync_check(remotes):
        (failures if level == "FAIL" else warnings).append("同步: " + msg)

    # ---- 下载远程清单 ----
    remote_lists, errors = load_remote_lists(remotes, args)
    if errors:
        for e in errors:
            print("下载失败: {}".format(e), file=sys.stderr)
        return 2

    # ---- 检查 2：格式（全部清单）----
    for tag, rules in remote_lists:
        for rule, level, msg in check_formats(rules, tag):
            entry = "格式[{}]: line {} {}: {}".format(tag, rule.lineno, rule.raw, msg)
            (failures if level == "FAIL" else warnings).append(entry)
    for rule, level, msg in check_formats(local_rules, "filter_local"):
        entry = "格式[filter_local]: line {}: {}".format(rule.lineno, msg)
        (failures if level == "FAIL" else warnings).append(entry)

    # ---- 检查 3：同清单死规则 ----
    for tag, rules in remote_lists:
        dead = find_intra_list_dead(rules, tag)
        if not dead:
            continue
        level = "FAIL" if tag in SELF_TAGS else "INFO"
        for rule, why in dead:
            entry = "死规则[{}] line {}: {} ({})".format(tag, rule.lineno, rule.raw, why)
            if level == "FAIL":
                failures.append(entry)
            else:
                infos.append(entry)

    # ---- 检查 4：跨清单接管（真机语义：最具体优先）----
    shadowed = find_cross_list_shadow(remote_lists, force_policies)
    agg = {}
    for wtag, ltag, rule, same, kind in shadowed:
        agg.setdefault((wtag, ltag, same, kind), []).append(rule)
    for (wtag, ltag, same, kind), rules in sorted(agg.items()):
        n = len(rules)
        samples = ", ".join(r.raw for r in rules[:3])
        label = "同值重复" if kind == "exact-dup" else "子域接管"
        if kind == "exact-dup" and ltag in SELF_TAGS:
            failures.append("跨清单同值重复[{}→{}] line {}: {} —— 更早清单同值 HOST 优先，本条永不可达"
                            .format(wtag, ltag, rules[0].lineno, rules[0].raw))
        elif ltag in SELF_TAGS and not same:
            warnings.append("{}[{}→{} 策略不同]: {} 条（如 {}）—— 自维护清单子域被接管"
                            .format(label, wtag, ltag, n, samples))
        elif same:
            infos.append("{}[{}→{} 同策略]: {} 条（如 {}）".format(label, wtag, ltag, n, samples))
        else:
            infos.append("{}[{}→{} 策略不同]: {} 条（如 {}）".format(label, wtag, ltag, n, samples))

    # ---- 探针表 ----
    cn_networks = load_cn_networks(args.timeout, fresh=args.fresh, offline=args.offline)
    if cn_networks is None:
        warnings.append("geoip: APNIC 数据不可用，geoip 相关探针将记 SKIP")
    engine = Engine(local_rules, remote_lists, cn_networks,
                    lambda host: resolve_host(host, args.timeout))

    probes = list(PROBES) + [tuple(p.split("=", 1)) + ("",) for p in args.probe]
    print("=" * 72)
    print("探针表（{} 条；期望值独立推导，见任务 research/）".format(len(probes)))
    print("=" * 72)
    passed = failed = skipped = 0
    for probe, expected, note in probes:
        actual, rule, unresolved = engine.match(probe)
        if unresolved:
            status, mark = "SKIP", "跳"
            skipped += 1
        elif expected_matches(actual, expected):
            status, mark = "PASS", "√"
            passed += 1
        else:
            status, mark = "FAIL", "×"
            failed += 1
            failures.append("探针 {} 期望 {} 实际 {}".format(probe, expected, actual))
        note_str = "  # " + note if note else ""
        print("[{}] {:28s} 期望 {:18s} 实际 {}{}"
              .format(mark, probe, expected, actual, note_str))

    # ---- 汇总 ----
    print("=" * 72)
    print("探针: {} 通过 / {} 失败 / {} 跳过".format(passed, failed, skipped))
    if warnings:
        print("\nWARN ({}):".format(len(warnings)))
        for w in warnings:
            print("  - " + w)
    if infos:
        print("\nINFO ({}，不影响退出码):".format(len(infos)))
        for i in infos[:40]:
            print("  - " + i)
        if len(infos) > 40:
            print("  ... 其余 {} 条省略".format(len(infos) - 40))
    if failures:
        print("\nFAIL ({}):".format(len(failures)))
        for f in failures:
            print("  - " + f)
        return 1
    print("\n审计通过：无 FAIL")
    return 0


def device_checklist(args):
    """输出真机导入核对单。"""
    try:
        remotes = parse_remote_conf(REMOTE_CONF)
    except (OSError, ValueError) as exc:
        print("配置错误: {}".format(exc), file=sys.stderr)
        return 2
    print("=" * 72)
    print("Quantumult X 真机导入核对单（供人工执行，结果回填维护记录）")
    print("=" * 72)
    print("""
一、导入检查（profile/QX_Config.conf）
  1. 设置 → 配置导入后无任何格式报错弹窗
  2. 分流页每个 tag 的策略图标正常显示（Qianji/WeChatAdSettlement/
     Xiaoyuzhou/Mainland/WeChat/Longbridge/AI/AppleIntelligence/Apple/Google/
     Microsoft/PayPal/Netflix/YouTube/Spotify/GlobalMedia/Telegram/Twitter/
     Steam/Epic/Sony/Nintendo/Outside/Ads/Advertising 共 {} 个）
  3. 远程资源"最近更新"时间均为近期（无下载失败感叹号）
  4. 主页下拉刷新触发资源更新，全部成功

二、探针实测（任选 5-10 条，看请求日志命中的 tag 与策略）：
""".format(len(remotes)))
    for probe, expected, note in PROBES:
        print("  {:28s} → 预期 tag: {:18s} {}".format(probe, expected, ("(" + note + ")") if note else ""))
    print("""
三、段序语义确认（本地先于远程）
  1. 访问 linux.do（[filter_local] host-suffix→proxy）：日志应显示命中
     本地规则而非远程清单
  2. 观察 copilot.microsoft.com：预期命中 Mainland（HOST-KEYWORD,microsoft）
     —— 若真机显示 AI/Microsoft 先命中，说明存在 host 类内子分层，
     请回报（影响审计脚本模型）
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
