#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则 URL 健康检查脚本。

对 checks/rule_urls.txt 中列出的远程资源逐项检查：
1. HTTP 状态码为 200
2. 内容非空
3. 返回的不是 HTML 页面（常见于 404 / 运营商劫持 / 图床占位页）
4. 简单格式校验（按扩展名）：
   - .list    至少一半的非注释行符合分流规则语法
     （host-suffix 系列；兼容上游 Surge 风格的 domain-suffix 系列）
   - .conf / .snippet  存在 Quantumult X 重写语法行（url/hostname/script 等）
   - 其他扩展名仅做 1-3 项基础检查

连接级错误（连接中断、超时等）自动重试 2 次；HTTP 状态码错误不重试。

用法：
    python3 scripts/check_rules.py [--file checks/rule_urls.txt]
                                   [--timeout 20] [--workers 8]

退出码：0 全部通过；1 存在失败项；2 清单文件或参数错误。

在 GitHub Actions 中运行时（GITHUB_ACTIONS=true），失败项会输出
::error:: 注解，方便在运行摘要中直接定位。
"""

import argparse
import concurrent.futures
import http.client
import os
import re
import sys
import time
import urllib.error
import urllib.request

MAX_BODY_BYTES = 2 * 1024 * 1024  # 每个资源最多读取 2MB，防止误填超大文件
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RuleHealthCheck/1.0"
TRANSIENT_RETRIES = 2  # 连接级错误（非 HTTP 状态码错误）的重试次数
RETRY_BACKOFF_SECONDS = 2.0

# Quantumult X 分流规则首字段（大小写不敏感）。
# 部分上游清单（如 AWAvenue）使用 Surge 风格前缀，Quantumult X 同样可解析，
# 因此 domain 系列也算合法。
FILTER_LINE_RE = re.compile(
    r"^(host|host-suffix|host-keyword|host-wildcard|"
    r"domain|domain-suffix|domain-keyword|domain-wildcard|"
    r"ip-cidr|ip-cidr6|geoip|user-agent|final|dest-wildcard|"
    r"logic|and|or|not)\b",
    re.IGNORECASE,
)

# Quantumult X 重写规则特征：url 动作、hostname、script 参数等
REWRITE_LINE_RE = re.compile(
    r"(\burl\s+(302|307|reject|request|response|echo|mirror|script-)|"
    r"^hostname\s*=|\bscript-path\s*=|\bscript-url\s*=|\brequires-body\s*=)",
    re.IGNORECASE,
)

COMMENT_PREFIXES = ("#", ";")


def load_urls(path):
    """读取 URL 清单，忽略空行与注释行，返回 (urls, error)。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return [], "无法读取清单文件 {}: {}".format(path, exc)

    urls = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIXES):
            continue
        if not line.startswith(("http://", "https://")):
            return [], "第 {} 行不是合法 URL: {}".format(lineno, line)
        urls.append(line)
    return urls, None


def fetch(url, timeout):
    """抓取 URL，返回 (body_text, error, transient)。

    error 为 None 表示请求成功；transient 表示错误是否为连接级抖动
    （值得重试），HTTP 状态码错误不算 transient。
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None, "HTTP {}".format(resp.status), False
            body = resp.read(MAX_BODY_BYTES)
    except urllib.error.HTTPError as exc:
        return None, "HTTP {}".format(exc.code), False
    except urllib.error.URLError as exc:
        return None, "连接失败: {}".format(exc.reason), True
    except http.client.HTTPException as exc:
        # 重定向/分块传输中断（IncompleteRead、RemoteDisconnected 等）
        return None, "连接异常中断: {}".format(type(exc).__name__), True
    except TimeoutError:
        return None, "请求超时（>{}s）".format(timeout), True
    except (OSError, ValueError) as exc:
        return None, "请求异常: {}".format(exc), True

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - decode 带 errors 参数不会抛出
        return None, "内容解码失败", False
    return text, None, False


def looks_like_html(text):
    head = text.lstrip()[:512].lower()
    return head.startswith(("<!doctype", "<html")) or "<html" in head


def content_lines(text):
    """返回去除空行与注释行后的内容行。"""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith(COMMENT_PREFIXES):
            out.append(line)
    return out


def validate_filter_list(text):
    """校验 .list 分流规则格式，返回 (ok, 说明)。"""
    lines = content_lines(text)
    if not lines:
        return False, "内容为空（无有效规则行）"
    valid = sum(1 for line in lines if FILTER_LINE_RE.match(line))
    if valid == 0:
        return False, "共 {} 行，无一行符合分流规则语法".format(len(lines))
    if valid * 2 < len(lines):
        return False, "仅 {}/{} 行符合分流规则语法".format(valid, len(lines))
    return True, "{}/{} 行符合分流规则语法".format(valid, len(lines))


def validate_rewrite(text):
    """校验重写配置格式，返回 (ok, 说明)。"""
    lines = content_lines(text)
    if not lines:
        return False, "内容为空（无有效重写行）"
    valid = sum(1 for line in lines if REWRITE_LINE_RE.search(line))
    if valid == 0:
        return False, "共 {} 行，未发现重写语法（url/hostname/script）".format(len(lines))
    return True, "{}/{} 行包含重写语法".format(valid, len(lines))


def check_one(url, timeout):
    """检查单个 URL，返回 dict(url=..., ok=..., detail=...)。"""
    result = {"url": url, "ok": False, "detail": ""}

    text, err, transient = None, None, False
    for attempt in range(TRANSIENT_RETRIES + 1):
        text, err, transient = fetch(url, timeout)
        if err is None and not text.strip():
            # 偶发被中间层截断为空响应，视作可重试；真空的文件重试后仍会失败
            err, transient = "内容为空", True
        if err is None or not transient:
            break
        if attempt < TRANSIENT_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS)

    if err:
        detail = err
        if transient and TRANSIENT_RETRIES > 0:
            detail += "（已重试 {} 次）".format(TRANSIENT_RETRIES)
        result["detail"] = detail
        return result

    if looks_like_html(text):
        result["detail"] = "返回 HTML 页面（疑似 404/劫持页）"
        return result

    lower = url.lower().split("?")[0]
    if lower.endswith(".list"):
        ok, detail = validate_filter_list(text)
        result["ok"], result["detail"] = ok, detail
        return result
    if lower.endswith((".conf", ".snippet")):
        ok, detail = validate_rewrite(text)
        result["ok"], result["detail"] = ok, detail
        return result

    size = len(text.encode("utf-8", errors="replace"))
    result["ok"] = True
    result["detail"] = "可访问，{} 字节".format(size)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Quantumult X 规则 URL 健康检查")
    parser.add_argument(
        "--file",
        default=os.path.join(os.path.dirname(__file__), "..", "checks", "rule_urls.txt"),
        help="URL 清单路径（默认 checks/rule_urls.txt）",
    )
    parser.add_argument("--timeout", type=int, default=20, help="单请求超时秒数（默认 20）")
    parser.add_argument("--workers", type=int, default=8, help="并发数（默认 8）")
    args = parser.parse_args(argv)

    urls, err = load_urls(args.file)
    if err:
        print("错误: {}".format(err), file=sys.stderr)
        return 2
    if not urls:
        print("错误: 清单为空: {}".format(args.file), file=sys.stderr)
        return 2

    print("共 {} 个 URL，超时 {}s，并发 {}（清单: {}）\n".format(
        len(urls), args.timeout, args.workers, args.file))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_one, url, args.timeout): url for url in urls}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # 按清单原始顺序输出，便于对照
    order = {url: idx for idx, url in enumerate(urls)}
    results.sort(key=lambda r: order[r["url"]])

    failed = [r for r in results if not r["ok"]]
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print("[{}] {} ({})".format(mark, r["url"], r["detail"]))

    print("\n结果: {}/{} 通过, {} 失败".format(
        len(results) - len(failed), len(results), len(failed)))

    if failed and os.environ.get("GITHUB_ACTIONS") == "true":
        for r in failed:
            # 截断避免注解过长
            detail = r["detail"][:200]
            print("::error title=规则健康检查失败::{} ({})".format(r["url"], detail))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
