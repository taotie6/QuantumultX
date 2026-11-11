# 更新日志

本文件记录两类内容：

1. **配置变更**（结构性修改：策略组、规则增删、DNS 调整等）记入日期条目。
   每次结构性变更提交时打一个 git tag（如 `config-2026-10-25`），出现故障可回滚。
2. **维护记录**（每周例行维护：同步 Fork、确认上游无破坏性变更、客户端验证）
   在文末「维护记录」表格追加一行，无需打 tag。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

（空：结构性变更条目已归档至对应日期段落）

## 2026-11-12

### Changed

- `[policy]` 为 AI / YouTube / Telegram / Netflix 四个策略组补充内置 `proxy`
  候选（三处同步：`config/policy.conf`、`profile/QX_Config.conf`、
  `config/quantumultx-template`）。原因：四组候选仅有地区组与 dest-hash，
  当所选节点失效或 IP 被目标服务风控时整组无可切换的兜底策略
  （实测场景：新加坡节点出口被 OpenAI 拉黑，chatgpt.com/api.openai.com
  全部超时，而 claude.ai 正常）。`proxy` 指向默认代理，可在组内直接切换。

## 2026-10-28

### Changed

- 将“钱迹记账”和“微信广告结算”从 `[filter_local]` 迁移为
  `rules/Qianji.list`、`rules/WeChatAdSettlement.list`，并接入 `[filter_remote]`；
  微信广告结算仍保留 10 条经本机 DevTools 验证的具体域名，核心补充 `wxa.wxs.qq.com`
- 新增 `rules/Xiaoyuzhou.list` 小宇宙直连分流
- 同步维护源、主配置、模板与规则健康检查清单

## 2026-10-26

### 新增

- `[filter_local]` 新增钱迹记账直连分组：`qianjiapp.com`、`xxoojoke.com`、
  `litangkj.com`、`qianjibillimage.kodo-accelerate.cn-south-1.qiniucs.com`
  （维护源 `config/filter_local.conf` 与 `profile/QX_Config.conf` 已同步）

## 2026-10-25

### 新增

- `config/` 配置拆分目录：`quantumultx.conf.template`（无凭据完整模板）、
  `policy.conf`、`filter_remote.conf`、`filter_local.conf`、`dns.conf`
  分别作为主配置对应段的维护源
- `checks/rule_urls.txt`：远程资源健康检查清单（分流 / 重写 / 任务脚本共 35 项）
- `scripts/check_rules.py`：规则 URL 健康检查脚本
  （HTTP 200、内容非空、非 HTML 劫持页、按扩展名的简单格式校验）
- `.github/workflows/check-rules.yml`：每周一 09:00（北京时间）自动健康检查，
  失败时自动创建/追加 Issue 通知，仅使用最小权限 `GITHUB_TOKEN`
- `CHANGELOG.md`：即本文件

### 架构约定

- 确立三层维护架构：上游 `blackmatrix7/ios_rule_script` 只读依赖、
  个人 Fork 跟踪上游、本仓库只保存个人配置与差异，不镜像上游规则
- 上游规则 URL 直接引用 `master` 分支，上游更新自动生效
- 量子配置不支持 include：`config/*.conf` 为维护源，
  变更后需手工同步到 `profile/QX_Config.conf` 对应段

### 依赖

- 无：远程资源清单与 `profile/QX_Config.conf` 当前引用完全一致

---

## 维护记录

> 每周维护后在表格追加一行。结果栏填写「正常」或具体问题与处理方式。

| 日期 | 操作 | 结果 |
| ---- | ---- | ---- |
| 2026-10-25 | 建立维护流水线，生成规则清单并本地全量验证 | 35 项中除 ddgksf2013.top 的 3 项外全部通过；该站点对非浏览器客户端返回 302/异常（XiaoHongShuAds、StartUpAds、server-info-pure），疑似站点限制，待人工确认替代源；其余偶发失败为本机到 raw.githubusercontent.com 的网络抖动，CI 环境不受影响 |
| 2026-11-11 | 深度维护：证据核对、AI.list 上游合并、AppleIntelligence 收窄、死规则清理、update-interval 对齐、语义审计脚本落地（`scripts/audit_rules.py`）。**证据来源**：钱迹 4 域=官方 VPN 帮助页（docs.qianjiapp.com/other/vpn_timeout.html）书面确认；小宇宙=软件许可协议明文域名 + 官网 og:audio 第一方引用 xyzcdn.net；长桥 8/9=各官网 + 官方帮助中心 longbridge/docs，lbtech.hk 经 HKIRC WHOIS/DNS/CT 三重确认未注册已删除；AppleIntelligence=Apple 官方 101555（smoot/guzzoni/apple-relay×3/cp4）+ curtinp118/Loon + bm7 issue #1598，app-measurement.com 确证为 Google Firebase 域名（归属错误）已移除。**上游 diff 结论**：VPSDance/ai-proxy-rules 为 MIT（署名合规），本地为上游严格子集，新增 20 条中合并 A 组 7 条 AI 专属 + B 组 2 条精确主机（api.cloudflare.com、storage.googleapis.com），11 条宽泛第三方规则不合并（含 IP-ASN,14061=DigitalOcean 全网段）；bm7 18 条路径全部存在（最近提交 2025-06~2026-10）、无失效 issue。**结构变更**：AppleIntelligence 26 条收窄为 9 条（苹果主域回落 Apple.list→Apple 策略组直连优先，Siri/PCC 端点保留走 AI）；Xiaoyuzhou 删 5 条死规则；AI.list 删 events.statsigapi.net 死规则；删除孤儿 rules/dandan.list；11 条 bm7 清单 update-interval 86400→604800（上游 ≥6 个月未更新）；rule_urls.txt 的 AppleIntelligence 从 [task_local] 区段移入 filter 区段。**探针表**：43/43 通过（含 apple.com→Apple、smoot→AppleIntelligence、midjourney/api.cloudflare.com/storage.googleapis.com→AI、copilot.microsoft.com→Outside、proxima.midjourney.com→Advertising 等新预期）。**真机验证**（Mac 端 QuantumultX TUN，2026-11-11）：收窄生效（www.apple.com→HOST,WWW.APPLE.COM,APPLE→DIRECT）、合并生效（www.midjourney.com→AI）、本地优先确认（linux.do→本地 PROXY）；实测推翻审计 v1 的"纯声明顺序"假设——**QX host 类实为"最具体优先"**（精确 HOST > 更长 SUFFIX > KEYWORD，跨清单生效：Global.list 精确 HOST,copilot.microsoft.com 赢 China.list KEYWORD 与 AI.list SUFFIX；Advertising.list 更长 SUFFIX,proxima.midjourney.com 赢 AI.list 短 SUFFIX）。审计引擎按真机语义重写（v2）：死规则判定收窄为"完全重复"，跨清单报告改为"子域接管"（WARN 4 组：Advertising→AI 13 条、GlobalMedia→AI 3 条、Ads→AI 1 条、Apple→AppleIntelligence 1 条，均为上游清单间子域级策略分歧，记录不改）；可达性三视角（CI 全球/本机直连/本机走 QX）均 36/39，3 项失败均为 ddgksf2013.top 存量问题（全球性失效，另案），无新增全球/大陆失败。**遗留问题**：① ddgksf2013.top 3 项全球失效待人工确认替代源；② AWAvenue issue #219（api.ad.xiaomi.com 误拦截）为上游内容问题；③ AI 策略组真机实测出口为 DIRECT（组候选无 direct，疑似手动选择或地区组链路指向，待确认组选择——分流命中本身正确） |
