# 更新日志

本文件记录两类内容：

1. **配置变更**（结构性修改：策略组、规则增删、DNS 调整等）记入日期条目。
   每次结构性变更提交时打一个 git tag（如 `config-2026-10-25`），出现故障可回滚。
2. **维护记录**（每周例行维护：同步 Fork、确认上游无破坏性变更、客户端验证）
   在文末「维护记录」表格追加一行，无需打 tag。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

### Changed

- 将“钱迹记账”和“微信广告结算”从 `[filter_local]` 迁移为
  `rules/Qianji.list`、`rules/WeChatAdSettlement.list`，并接入 `[filter_remote]`；
  微信广告结算仍保留 10 条经本机 DevTools 验证的具体域名，核心补充 `wxa.wxs.qq.com`
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
