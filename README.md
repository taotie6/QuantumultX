# Quantumult X 配置库

Quantumult X 配置文件集合。自维护脚本发布在 [taotie6/scripts](https://github.com/taotie6/scripts)，本仓库通过 `.conf` 文件远程引用；尚未迁移的历史脚本保留原上游地址。

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
│   └── banana-travelsim.conf          # Banana Travel SIM 流量查询
├── rules/                             # 本地规则文件
│   ├── AI.list                        # AI 服务规则
│   ├── AppleIntelligence.list         # 苹果智能服务规则
│   ├── dandan.list                    # 蛋蛋不语规则
│   └── Longbridge.list                # 长桥证券代理规则
└── icons/                             # 策略图标
```

> taotie6 自维护脚本统一发布在 [taotie6/scripts](https://github.com/taotie6/scripts)。未迁移到该仓库的历史脚本仍保留原上游 raw 地址，避免配置指向不存在的脚本文件。

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
| `banana-travelsim.js` | Banana Travel SIM 多卡流量查询 | 先导入 BoxJS 配置 `https://raw.githubusercontent.com/taotie6/scripts/main/boxjs/banana-travelsim.boxjs.json`，再导入 `scripts/banana-travelsim.conf`；脚本地址为 `https://raw.githubusercontent.com/taotie6/scripts/main/scripts/banana-travelsim.js` |

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
