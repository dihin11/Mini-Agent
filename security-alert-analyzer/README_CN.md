# 安全告警分析器

基于 MiniMax M2 模型和 Mini-Agent 子代理框架的智能安全告警分析系统。

## 📋 功能概述

本系统通过协调两个专业子代理来全面分析安全告警：

1. **威胁情报分析代理** - 查询攻击者 IP 信誉和受害资产画像
2. **TTP 分析代理** - 分析攻击战术、技术和程序

最终生成综合风险评估报告，将威胁等级判定为：**高危 / 中危 / 低危**

## 🏗️ 系统架构

```
用户输入安全告警
    ↓
主协调代理 (MiniMax M2)
    ├─→ 威胁情报子代理
    │   ├─ query_ip_reputation (MCP)
    │   └─ get_asset_profile (MCP)
    │
    └─→ TTP 分析子代理
        └─ 攻击技术识别与映射
    ↓
综合风险评估报告
    - 风险等级: 高/中/低
    - 详细分析与建议
```

## 🚀 快速开始

### 前置要求

1. **已安装 Mini-Agent**
   ```bash
   cd /path/to/Mini-Agent
   uv sync
   ```

2. **已配置 MiniMax API Key**
   - 编辑 `~/.mini-agent/config/config.yaml`
   - 填入有效的 API Key

3. **已配置 MCP 服务** ⚠️ **重要**
   
   需要配置两个 MCP 工具：
   - `query_ip_reputation` - IP 信誉查询服务
   - `get_asset_profile` - 资产画像查询服务
   
   **配置方式一：本地配置（推荐）**
   
   在项目目录下创建 `mcp.json`：
   ```bash
   cd security-alert-analyzer
   cp .mcp.json.template mcp.json
   # 然后编辑 mcp.json 填入实际配置
   ```
   
   **配置方式二：全局配置**
   
   编辑 `~/.mini-agent/config/mcp.json`
   
   系统会优先使用本地 `mcp.json`，如不存在则使用全局配置。
   
   > 💡 **提示**: 参考 `MCP_CONFIG_GUIDE.md` 获取详细配置说明。

### 使用方法

```bash
cd security-alert-analyzer

# 分析高危告警 (SQL 注入)
python analyzer.py sample_alerts/high_severity_sqli.json

# 分析中危告警 (端口扫描)
python analyzer.py sample_alerts/medium_severity_portscan.json

# 分析低危告警 (失败登录)
python analyzer.py sample_alerts/low_severity_failedauth.json
```

## 📂 项目结构

```
security-alert-analyzer/
├── analyzer.py                        # 主分析脚本
├── mcp.json                          # MCP 配置文件（本地）
├── .mcp.json.template                # MCP 配置模板
├── agents/                           # 代理定义
│   ├── main-coordinator-agent.md     # 主协调代理定义
│   ├── threat-intel-agent.md         # 威胁情报分析代理
│   └── ttp-analyzer-agent.md         # TTP 分析代理
├── sample_alerts/                    # 示例告警数据
│   ├── high_severity_sqli.json       # 高危: SQL 注入
│   ├── medium_severity_portscan.json # 中危: 端口扫描
│   └── low_severity_failedauth.json  # 低危: 失败登录
├── workspace/                        # 工作空间 (自动创建)
│   └── .agent_memory*.json          # 代理会话记录
├── README_CN.md                      # 中文文档
├── README.md                         # 英文文档
└── MCP_CONFIG_GUIDE.md              # MCP 配置指南
```

## 📊 示例输出

### 高危告警分析

```
🛡️  安全告警分析系统
================================================================================
安全告警详情
================================================================================
告警 ID: ALR-2025-001234
时间: 2025-11-25T10:30:00Z
攻击者 IP: 192.0.2.123
受害者 IP: 10.0.1.50
攻击类型: sql_injection
载荷: ' OR '1'='1' --
================================================================================

🔍 开始分析...

Step 1: 调用威胁情报子代理
Step 2: 调用 TTP 分析子代理
Step 3: 综合评估

📊 分析完成
================================================================================

**风险等级**: 高

**威胁情报摘要**
- 攻击者 IP 信誉评分: 95/100 (已知恶意)
- 威胁类别: 僵尸网络 C2
- 受害资产: 关键数据库服务器 (财务部门)

**TTP 分析摘要**
- 攻击技术: SQL 注入
- MITRE ATT&CK: T1190
- 严重性: 高 (可导致数据库完全泄露)

**综合评估理由**
已知恶意 IP (95/100) 攻击关键资产，使用高危 SQL 注入技术。
符合高危判定标准：恶意来源 + 关键资产 + 危险技术。

**建议措施**
1. 立即在防火墙阻断 IP 192.0.2.123
2. 隔离数据库服务器并检查访问日志
3. 部署 WAF 并实施参数化查询
```

## 🔧 自定义告警

创建自定义告警 JSON 文件：

```json
{
  "alert_id": "YOUR-ALERT-ID",
  "timestamp": "2025-11-25T10:30:00Z",
  "attacker_ip": "攻击者IP",
  "victim_ip": "受害者IP",
  "attack_type": "攻击类型",
  "payload": "攻击载荷",
  "protocol": "HTTP/HTTPS/TCP",
  "destination_port": 443,
  "additional_context": {
    "key": "value"
  },
  "description": "告警描述"
}
```

**必需字段**:
- `attacker_ip`: 攻击者 IP 地址
- `victim_ip`: 受害者 IP 地址
- `attack_type`: 攻击类型

**可选字段**: 其他所有字段均可选

## 🎯 支持的攻击类型

TTP 分析代理内置以下攻击类型的识别：

- `sql_injection` - SQL 注入
- `xss` - 跨站脚本攻击
- `port_scan` - 端口扫描
- `brute_force` - 暴力破解
- `command_injection` - 命令注入
- `path_traversal` - 路径遍历

其他未列出的攻击类型也会被分析，但可能需要更详细的载荷信息。

## ⚙️ 风险评级规则

系统根据以下规则判定风险等级：

### 高危 (High)
- (恶意 IP 或 关键资产) **且** (危险攻击技术)
- IP 信誉评分 ≥ 70 或 资产关键性 = critical
- 攻击严重性 = 高

### 中危 (Medium)
- (可疑 IP 或 重要资产) **且** (常见攻击技术)
- 或 (恶意 IP) **且** (低风险技术)

### 低危 (Low)
- (正常 IP) **且** (良性模式)
- IP 信誉评分 < 30 且 资产关键性 = low/unknown
- 攻击严重性 = 低

## 🔍 工作流程详解

1. **告警加载**: 读取 JSON 文件并验证必需字段

2. **系统初始化**:
   - 加载 MiniMax M2 模型配置
   - 连接 MCP 服务 (威胁情报 + 资产管理)
   - 发现并加载子代理定义

3. **威胁情报分析**:
   - 主代理调用 `threat_intel_analyzer` 子代理
   - 子代理通过 MCP 查询攻击者 IP 信誉
   - 子代理通过 MCP 查询受害资产画像
   - 返回结构化威胁情报报告

4. **TTP 分析**:
   - 主代理调用 `ttp_analyzer` 子代理
   - 子代理分析攻击类型和载荷
   - 识别攻击技术并映射到 MITRE ATT&CK
   - 评估利用风险和潜在影响
   - 返回结构化 TTP 分析报告

5. **综合评估**:
   - 主代理收集两份子代理报告
   - 应用风险评级规则
   - 生成最终风险等级判定
   - 提供可执行的应对建议

## 🛠️ 故障排查

### MCP 工具加载失败

```
⚠️  警告: MCP 配置文件不存在
```

**解决方案**:
1. 确认 `~/.mini-agent/config/mcp.json` 文件存在
2. 检查文件格式是否为有效 JSON
3. 确认配置了 `query_ip_reputation` 和 `get_asset_profile` 工具

### 子代理未找到

```
❌ 错误: 未找到子代理定义文件
```

**解决方案**:
1. 确认 `agents/` 目录存在
2. 确认包含两个代理定义文件:
   - `threat-intel-agent.md`
   - `ttp-analyzer-agent.md`

### API Key 错误

```
❌ 配置加载失败
```

**解决方案**:
1. 检查 `~/.mini-agent/config/config.yaml` 是否存在
2. 确认配置了有效的 MiniMax API Key
3. 检查 API Base URL 是否正确

### 告警文件格式错误

```
❌ 错误: 告警数据缺少必需字段: attacker_ip
```

**解决方案**:
确保告警 JSON 文件包含所有必需字段：
- `attacker_ip`
- `victim_ip`
- `attack_type`

## 📖 技术说明

### 子代理隔离

- 每个子代理有独立的会话记录文件
- 子代理之间无法相互调用 (防止递归)
- 子代理只能访问配置中指定的工具

### MCP 集成

- 使用标准 MCP (Model Context Protocol) 协议
- 通过 stdio 与 MCP 服务器通信
- 支持异步工具调用

### 提示词工程

- 主代理: 协调流程，综合评估
- 威胁情报代理: 专注 IP 和资产分析
- TTP 代理: 专注攻击技术识别

每个代理都有明确的职责边界和输出格式要求。

## 🎓 学习价值

本示例展示了：

1. **子代理模式**: 如何将复杂任务分解给专业子代理
2. **MCP 集成**: 如何通过 MCP 获取外部数据
3. **结构化工作流**: 多阶段分析流程的实现
4. **领域知识注入**: 在提示词中嵌入专业知识 (MITRE ATT&CK)
5. **错误处理**: 优雅降级和用户友好的错误信息

## 📝 许可证

本示例代码遵循 Mini-Agent 项目的许可证。

## 🤝 贡献

欢迎提交问题和改进建议！

---

**提示**: 这是一个演示示例，MCP 服务需要您根据实际环境配置。在生产环境中，建议连接真实的威胁情报 API (如 VirusTotal, AbuseIPDB) 和资产管理系统。

---

## 🆕 最新更新 (v2.0.0)

### MCP URL 连接支持

现在支持远程 MCP 服务器连接！除了本地 stdio 进程，还可以通过 URL 连接远程服务：

**支持的传输协议：**
- ✅ `stdio` - 本地进程通信（原有功能）
- ✅ `sse` - Server-Sent Events 远程连接（新增）
- ✅ `websocket` - WebSocket 远程连接（新增）

**配置示例：**
```json
{
  "mcpServers": {
    "local-server": {
      "transport": "stdio",
      "command": "python",
      "args": ["server.py"]
    },
    "remote-threat-intel": {
      "transport": "sse",
      "url": "https://threat-intel.example.com/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    },
    "remote-asset-db": {
      "transport": "websocket",
      "url": "wss://asset-db.example.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

**详细文档：**
- 📖 [MCP URL 配置指南](./MCP_URL_CONFIGURATION.md)
- 📖 [完整更新说明](./FINAL_UPDATE_SUMMARY.md)

### 异步资源清理优化

修复了程序退出时的 RuntimeError，现在会正确清理所有 MCP 连接：
- ✅ 自动清理所有异步资源
- ✅ 优雅处理清理错误
- ✅ 详细的清理日志

程序退出时会看到：
```
🔌 清理 MCP 连接...
✅ 清理完成
```

---
