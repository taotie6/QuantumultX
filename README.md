# Quantumult X 配置库

Quantumult X 完整配置文件集合，包含智能分流规则、重写规则和自动化脚本模块。

**脚本来源说明**：
- taotie6 自维护脚本发布在 [taotie6/scripts](https://github.com/taotie6/scripts)，本仓库通过 `.conf` 文件远程引用
- 历史脚本暂保留原上游地址（curtinp118/Scripthub），待迁移后统一指向 taotie6 仓库
- 第三方规则和工具（blackmatrix7、KOP-XIAO、ddgksf2013 等）保持原作者地址

## 📱 配置预览

| 首页预览 | 策略列表 | 重写规则 |
| :---: | :---: | :---: |
| <img src="https://cdn.jsdelivr.net/gh/taotie6/QuantumultX@main/icons/home1.jpeg" width="280" /> | <img src="https://cdn.jsdelivr.net/gh/taotie6/QuantumultX@main/icons/home2.jpeg" width="280" /> | <img src="https://cdn.jsdelivr.net/gh/taotie6/QuantumultX@main/icons/rewrite.jpeg" width="280" /> |

## 📁 仓库结构

```
QuantumultX/
├── README.md                          # 本文件
├── LICENSE                            # MIT 许可证
├── profile/
│   └── QX_Config.conf                 # 主配置文件
├── scripts/                           # 脚本配置（引用 taotie6/scripts 或上游脚本源）
│   ├── glados.conf                    # GLaDOS / Railgun 签到
│   ├── v2ex.conf                      # V2EX 每日签到
│   ├── new-api.conf                   # NewAPI 通用签到
│   ├── cd-rail.conf                   # 成都地铁签到
│   ├── cmcc.conf                      # 中国移动签到
│   ├── nodeseek.conf                  # NodeSeek 论坛签到
│   ├── buding.conf                    # 布丁锁屏解锁
│   ├── caiyun.conf                    # 彩云天气解锁
│   ├── nicegram.conf                  # Nicegram 解锁
│   ├── dreamface.conf                 # DreamFace 解锁
│   ├── notability.conf                # Notability 解锁
│   ├── banana-travelsim.conf          # Banana Travel SIM 流量查询任务片段
│   └── banana-travelsim.gallery.json  # Banana Travel SIM Quantumult X 任务库
├── rules/                             # 本地规则文件
│   ├── AI.list                        # AI 服务规则
│   ├── AppleIntelligence.list         # 苹果智能服务规则
│   ├── dandan.list                    # 蛋蛋不语规则
│   └── Longbridge.list                # 长桥证券代理规则
└── icons/                             # 策略图标
```

## ✨ 主要特性

### 🔧 完整配置
- **智能分流**：国内直连、国外代理、流媒体、社交等智能分类
- **地区策略**：香港、台湾、日本、新加坡、美国、韩国等节点智能分配
- **策略优选**：支持手动选择、自动延迟测试、目标地址哈希
- **DNS 优化**：预配置多个高效 DNS 解析服务，支持 DoH3
- **IPv6 禁用**：默认禁用 IPv6 避免泄漏

### 📋 规则集成
- **国内规则**：国内 CDN、金融、社交直连
- **国际规则**：Google、Apple、PayPal
- **流媒体**：Netflix、YouTube、Spotify
- **AI 服务**：OpenAI、Claude、Gemini、Copilot、Perplexity 等全覆盖
- **金融服务**：长桥证券代理分流，国内银行直连
- **广告拦截**：多个高质量广告过滤规则

### 🔄 重写规则
- YouTube 字幕/去广告
- 闲鱼、小红书、高德地图去广告
- Reddit 功能增强
- Spotify 增强

## 📜 脚本列表

taotie6 自维护脚本发布在 [taotie6/scripts](https://github.com/taotie6/scripts)。未迁移脚本继续引用原上游地址。

### taotie6 自维护脚本

| 脚本 | 功能 | 使用方法 |
|------|------|----------|
| `banana-travelsim.js` | Banana Travel SIM 多卡流量查询 | 1. 在 Quantumult X 任务库中添加 `https://raw.githubusercontent.com/taotie6/QuantumultX/main/scripts/banana-travelsim.gallery.json`<br>2. 在 BoxJS 中导入订阅 `https://raw.githubusercontent.com/taotie6/scripts/main/boxjs/banana-travelsim.boxjs.json`<br>3. 配置 SIM 卡信息后运行 |

> `scripts/banana-travelsim.conf` 是 `[task_local]` 任务片段，不能直接作为远程资源或任务库 URL 加入 Quantumult X。如果提示“非法”，请改用上面的 `banana-travelsim.gallery.json`；或者手动复制 `.conf` 中的任务行到主配置的 `[task_local]` 段。

Quantumult X 可直接打开任务库添加链接：

```text
quantumult-x:///ui?module=gallery&type=task&action=add&content=%5B%22https%3A%2F%2Fraw.githubusercontent.com%2Ftaotie6%2FQuantumultX%2Fmain%2Fscripts%2Fbanana-travelsim.gallery.json%22%5D
```

### 签到类

| 脚本 | 功能 | 使用方法 |
|------|------|----------|
| `new-api.js` | NewAPI 中转站通用签到 | 先抓包保存 `/api/user/self` 的 Cookie，支持多站点多账户 |
| `v2ex.js` | V2EX 每日签到 | 访问 V2EX 个人主页保存 Cookie |
| `glados.js` | GLaDOS / Railgun 签到 + 积分兑换 | 访问控制台抓包保存 Cookie，支持多域名多账户 |
| `cd-rail.js` | 成都地铁签到 | 打开成都地铁 App 签到页面保存请求头 |
| `cmcc.js` | 中国移动签到 | 打开移动 App 签到页面保存 Cookie |
| `nodeseek.js` | NodeSeek 论坛签到 | 访问 NodeSeek 个人页面保存请求头 |

### 解锁类

| 脚本 | 功能 | 说明 |
|------|------|------|
| `buding.js` | 布丁锁屏解锁 | 需要 MITM |
| `caiyun.js` | 彩云天气解锁 | 需要 MITM |
| `nicegram.js` | Nicegram 解锁 | 需要 MITM |
| `dreamface.js` | DreamFace 解锁 | 需要 MITM |
| `notability.js` | Notability 解锁 | 需要 MITM |

## 🚀 快速开始

### 1. 导入配置

在 Quantumult X 中：
1. 点击「配置」
2. 选择「下载」或「从文件导入」
3. 复制以下地址：
   ```
   https://raw.githubusercontent.com/taotie6/QuantumultX/main/profile/QX_Config.conf
   ```

### 2. 配置订阅

编辑 `[server_remote]` 部分添加你的机场订阅链接。

### 3. MITM 证书

部分脚本需要 MITM 证书才能工作：
1. 在 Quantumult X 中开启 MITM
2. 安装并信任证书
3. 配置对应的 hostname

### 4. 启用脚本

编辑 `[task_local]` 部分启用需要的自动签到脚本（默认 disabled）。

## 🔄 配置更新

Quantumult X 的「下载配置」主要用于首次导入或重新覆盖整份配置，不提供类似 Clash 的完整配置更新按钮。更新时请区分两种情况：

### 日常更新：刷新远程资源

本配置已将节点订阅、分流规则、重写规则等高频变化内容放在远程资源中：

- `[server_remote]`：代理节点订阅
- `[filter_remote]`：远程分流规则
- `[rewrite_remote]`：远程重写规则

这些资源会按配置中的 `update-interval` 自动更新。需要手动刷新时，在 Quantumult X 主界面长按右下角圆形按钮，然后点击左侧刷新按钮，即可更新远程节点、分流和重写资源。

日常使用优先采用这种方式，不需要重新覆盖 `QX_Config.conf`。

### 基础配置更新：重新下载覆盖

如果本仓库更新了 `profile/QX_Config.conf` 的基础结构，例如策略组、DNS、MITM、远程资源入口等，需要重新下载完整配置：

1. 先在 Quantumult X 中导出或备份当前配置。
2. 打开「配置文件」中的「下载」。
3. 粘贴以下地址：
   ```
   https://raw.githubusercontent.com/taotie6/QuantumultX/main/profile/QX_Config.conf
   ```
4. 确认覆盖导入。
5. 重新填写自己的 `[server_remote]` 机场订阅链接，并恢复个人本地修改。

覆盖导入会替换当前配置，可能导致个人订阅、手动规则、策略组调整等本地修改丢失。除非需要同步基础配置结构，否则不要频繁覆盖整份配置。

## 🌐 策略说明

| 策略 | 用途 | 节点选择 |
|------|------|----------|
| Apple | Apple 服务 | 直连/代理 |
| AI | AI 服务 (ChatGPT/Claude/Gemini) | 美国/日本/新加坡 |
| Google | Google 服务 | 新加坡/美国 |
| YouTube | YouTube | 香港/台湾/日本/韩国/新加坡/美国 |
| X | Twitter/X | 香港/台湾/日本/韩国/新加坡/美国 |
| Telegram | Telegram | 香港/台湾/日本/新加坡/美国 |
| Netflix | Netflix | 手动选择/香港/台湾/日本/韩国/新加坡/美国 |
| Spotify | Spotify | 新加坡/香港/日本/美国 |
| PayPal | PayPal | 美国/代理/直连 |
| GlobalMedia | 全球流媒体 | 代理/直连/手动 |
| Gamer | 游戏平台 | 代理/直连/香港/美国/新加坡 |

## 🔐 隐私与安全

本仓库中的 `QX_Config.conf` 为公开配置：
- ✅ 所有规则和脚本链接都是公开的
- ✅ MITM 证书信息已使用占位符替换
- ✅ 个人订阅 Token 需自行添加
- ✅ Cookie 等敏感信息仅保存在本地

## 🤝 相关资源

- [taotie6/scripts 脚本库](https://github.com/taotie6/scripts) — 自维护脚本发布
- [Loon 配置库](https://github.com/curtinp118/Loon) — Loon 配置
- [Quantumult X 官方网站](https://quantumultx.com)
- [iOS 规则脚本库 - blackmatrix7](https://github.com/blackmatrix7/ios_rule_script)
- [资源解析与脚本 - KOP-XIAO](https://github.com/KOP-XIAO/QuantumultX)
- [广告规则 - AWAvenue](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)
- [重写规则 - ddgksf2013](https://github.com/ddgksf2013/Rewrite)

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT License 开源许可证。详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本仓库提供的配置和脚本仅供学习参考使用，用户需自行承担使用本配置的一切后果。

---

**最后更新**: 2026-06-21
