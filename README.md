# Quantumult X 配置库

一个精心维护的 Quantumult X 配置文件和自动化脚本集合。

## 📁 仓库结构

```
QuantumultX/
├── README.md                          # 本文件
├── LICENSE                            # MIT 许可证
├── profile/
│   └── QX_Config.conf                 # 主配置文件
├── scripts/                           # 自动化脚本
│   ├── new-api.js                     # NewAPI 中转站通用签到
│   ├── v2ex.js                        # V2EX 每日签到
│   ├── cd-rail.js                     # 成都地铁签到
│   ├── cmcc.js                        # 中国移动签到
│   ├── nodeseek.js                    # NodeSeek 论坛签到
│   ├── buding.js                      # 布丁锁屏解锁
│   ├── caiyun.js                      # 彩云天气解锁
│   ├── nicegram.js                    # Nicegram 解锁
│   ├── dreamface.js                   # DreamFace 解锁
│   └── notability.js                  # Notability 解锁
├── rules/                             # 本地规则文件
│   ├── AI.list                        # AI 服务规则
│   └── AppleIntelligence.list         # 苹果智能服务规则
└── icons/                             # 策略图标
    ├── Curtin.jpg                     # 仓库头像
    ├── set.png
    └── lightning-full.png
```

## ✨ 主要特性

### 🔧 完整配置
- **智能分流**：国内直连、国外代理、流媒体、社交等智能分类
- **地区策略**：香港、台湾、日本、新加坡、美国、韩国等节点智能分配
- **策略优选**：支持手动选择、自动延迟测试、目标地址哈希
- **DNS 优化**：预配置多个高效 DNS 解析服务

### 📋 规则集成
- **国内规则**：国内 CDN、金融、社交直连
- **国际规则**：Google、Apple、Microsoft、GitHub、PayPal
- **流媒体**：Netflix、YouTube、Spotify、BiliBili
- **广告拦截**：多个高质量广告过滤规则
- **AI 服务**：OpenAI、Claude、Gemini、Copilot 等全覆盖

### 📜 自动化脚本
- **签到类**：NewAPI 通用签到、V2EX、成都地铁、中国移动、NodeSeek
- **解锁类**：布丁锁屏、彩云天气、Nicegram、DreamFace、Notability

## 🚀 快速开始

### 1. 导入配置

在 Quantumult X 中：
1. 点击「配置」
2. 选择「下载」或「从文件导入」
3. 复制以下地址：
   ```
   https://raw.githubusercontent.com/curtinp118/QuantumultX/refs/heads/main/profile/QX_Config.conf
   ```

### 2. 配置订阅

编辑 `[server_remote]` 部分添加你的机场订阅链接。

### 3. MITM 证书

部分脚本需要 MITM 证书才能工作：
1. 在 Quantumult X 中开启 MITM
2. 安装并信任证书
3. 配置对应的 hostname

### 4. 启用脚本

编辑 `[task_local]` 部分启用需要的自动签到脚本。

## 📜 脚本使用说明

### 签到类脚本

| 脚本 | 功能 | 使用方法 |
|------|------|----------|
| `new-api.js` | NewAPI 中转站通用签到 | 先抓包保存 `/api/user/self` 的 Cookie，支持多站点多账户 |
| `v2ex.js` | V2EX 每日签到 | 访问 V2EX 个人主页保存 Cookie |
| `cd-rail.js` | 成都地铁签到 | 打开成都地铁 App 签到页面保存请求头 |
| `cmcc.js` | 中国移动签到 | 打开移动 App 签到页面保存 Cookie |
| `nodeseek.js` | NodeSeek 论坛签到 | 访问 NodeSeek 个人页面保存请求头 |

### 解锁类脚本

| 脚本 | 功能 | 说明 |
|------|------|------|
| `buding.js` | 布丁锁屏解锁 | 需要 MITM |
| `caiyun.js` | 彩云天气解锁 | 需要 MITM |
| `nicegram.js` | Nicegram 解锁 | 需要 MITM |
| `dreamface.js` | DreamFace 解锁 | 需要 MITM |
| `notability.js` | Notability 解锁 | 需要 MITM |

## 🔐 隐私与安全

本仓库中的 `QX_Config.conf` 为公开配置：
- ✅ 所有规则和脚本链接都是公开的
- ✅ MITM 证书信息已使用占位符替换
- ✅ 个人订阅 Token 需自行添加
- ✅ Cookie 等敏感信息仅保存在本地

## 🤝 相关资源

- [Quantumult X 官方网站](https://quantumultx.com)
- [iOS 规则脚本库 - blackmatrix7](https://github.com/blackmatrix7/ios_rule_script)
- [资源解析与脚本 - KOP-XIAO](https://github.com/KOP-XIAO/QuantumultX)

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT License 开源许可证。详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本仓库提供的配置和脚本仅供学习参考使用，用户需自行承担使用本配置的一切后果。

---

**最后更新**: 2026-05-27
