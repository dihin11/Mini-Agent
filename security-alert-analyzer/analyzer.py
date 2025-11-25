#!/usr/bin/env python3
"""
安全告警分析器

使用 MiniMax M2 模型和子代理框架分析安全告警，评估威胁等级。
包含两个专业子代理：
1. 威胁情报分析代理 - 查询 IP 信誉和资产画像
2. TTP 分析代理 - 分析攻击技战术手法
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from mini_agent.agent import Agent
from mini_agent.config import Config
from mini_agent.llm import LLMClient
from mini_agent.tools.agent_loader import AgentLoader
from mini_agent.tools.call_agent_tool import CallAgentTool
from mini_agent.tools.note_tool import SessionNoteTool
from mini_agent.tools.mcp_loader import load_mcp_tools_async, cleanup_mcp_connections


def load_alert(alert_file: Path) -> dict:
    """加载安全告警数据"""
    try:
        with open(alert_file, 'r', encoding='utf-8') as f:
            alert = json.load(f)
        
        # 验证必需字段
        required_fields = ["attacker_ip", "victim_ip", "attack_type"]
        for field in required_fields:
            if field not in alert:
                raise ValueError(f"告警数据缺少必需字段: {field}")
        
        return alert
    except json.JSONDecodeError as e:
        raise ValueError(f"告警文件 JSON 格式错误: {e}")
    except FileNotFoundError:
        raise ValueError(f"告警文件不存在: {alert_file}")


def format_alert_info(alert: dict) -> str:
    """格式化告警信息用于显示"""
    lines = [
        "=" * 80,
        "安全告警详情",
        "=" * 80,
        f"告警 ID: {alert.get('alert_id', 'N/A')}",
        f"时间: {alert.get('timestamp', 'N/A')}",
        f"攻击者 IP: {alert['attacker_ip']}",
        f"受害者 IP: {alert['victim_ip']}",
        f"攻击类型: {alert['attack_type']}",
        f"载荷: {alert.get('payload', 'N/A')}",
        f"协议: {alert.get('protocol', 'N/A')}",
        f"目标端口: {alert.get('destination_port', 'N/A')}",
    ]
    
    if 'description' in alert:
        lines.append(f"描述: {alert['description']}")
    
    lines.append("=" * 80)
    return "\n".join(lines)


async def main():
    """主函数"""
    print("\n" + "🛡️  " * 20)
    print("        安全告警分析系统 (基于 MiniMax M2 模型)")
    print("🛡️  " * 20 + "\n")
    
    # 确保在退出时清理 MCP 连接
    try:
        await _run_analysis()
    finally:
        print("\n🔌 清理 MCP 连接...")
        await cleanup_mcp_connections()
        print("✅ 清理完成")


async def _run_analysis():
    """实际的分析逻辑"""
    
    # 解析命令行参数
    if len(sys.argv) < 2:
        print("用法: python analyzer.py <告警文件路径>")
        print("\n示例:")
        print("  python analyzer.py sample_alerts/high_severity_sqli.json")
        print("  python analyzer.py sample_alerts/medium_severity_portscan.json")
        print("  python analyzer.py sample_alerts/low_severity_failedauth.json")
        # sys.exit(1)
        alert_file = Path("sample_alerts/high_severity_sqli.json")
    else:
        alert_file = Path(sys.argv[1])
    
    # 如果是相对路径，相对于当前脚本目录
    if not alert_file.is_absolute():
        alert_file = current_dir / alert_file
    
    # 加载告警数据
    print("📥 加载告警数据...")
    try:
        alert = load_alert(alert_file)
        print(format_alert_info(alert))
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    
    # 工作空间设置
    workspace_dir = current_dir / "workspace"
    workspace_dir.mkdir(exist_ok=True)
    
    agents_dir = current_dir / "agents"
    
    # 加载配置
    print("\n⚙️  初始化系统...")
    
    # 优先使用本地配置，否则使用全局配置
    local_config = current_dir / "config.yaml"
    global_config = Path.home() / ".mini-agent" / "config" / "config.yaml"
    
    config_path = local_config if local_config.exists() else global_config
    
    try:
        if local_config.exists():
            print(f"✅ 使用本地配置: {local_config}")
            config = Config.from_yaml(str(local_config))
        else:
            print(f"⚠️  本地配置不存在，使用全局配置: {global_config}")
            config = Config.from_yaml(str(global_config))
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        print(f"\n已检查位置:")
        print(f"  - 本地: {local_config}")
        print(f"  - 全局: {global_config}")
        print("\n请确保:")
        print("  1. 复制 config.yaml.example 为 config.yaml")
        print("  2. 填写有效的 MiniMax API Key")
        sys.exit(1)
    
    # 初始化 LLM 客户端
    llm_client = LLMClient(
        api_key=config.llm.api_key,
        api_base=config.llm.api_base,
        model=config.llm.model
    )
    
    # 基础工具
    tools = [
        SessionNoteTool(memory_file=str(workspace_dir / ".agent_memory.json"))
    ]
    
    # 加载 MCP 工具
    print("🔌 加载 MCP 工具...")
    # 优先使用当前目录的 mcp.json，否则使用全局配置
    local_mcp_config = current_dir / "mcp.json"
    global_mcp_config = Path.home() / ".mini-agent" / "config" / "mcp.json"
    
    mcp_config_path = local_mcp_config if local_mcp_config.exists() else global_mcp_config
    
    if not mcp_config_path.exists():
        print(f"⚠️  警告: 未找到 MCP 配置文件")
        print(f"   已检查位置:")
        print(f"   - 本地: {local_mcp_config}")
        print(f"   - 全局: {global_mcp_config}")
        print("\n请配置 MCP 服务以使用威胁情报和资产画像功能")
        print("需要配置的 MCP 工具:")
        print("  - query_ip_reputation: IP 信誉查询")
        print("  - get_asset_profile: 资产画像查询")
        print("\n参考 MCP_CONFIG_GUIDE.md 或使用 .mcp.json.template 模板")
        sys.exit(1)
    
    print(f"✅ 使用配置文件: {mcp_config_path}")
    
    try:
        mcp_tools = await load_mcp_tools_async(config_path=str(mcp_config_path))
        if mcp_tools:
            tools.extend(mcp_tools)
            print(f"✅ 已加载 {len(mcp_tools)} 个 MCP 工具")
            for tool in mcp_tools:
                print(f"   • {tool.name}")
        else:
            print("⚠️  警告: 未加载任何 MCP 工具")
            print("请检查 mcp.json 配置")
            sys.exit(1)
    except Exception as e:
        print(f"❌ MCP 工具加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 加载子代理
    print("\n🤖 加载子代理...")
    agent_loader = AgentLoader(agents_dir=str(agents_dir))
    discovered = agent_loader.discover_agents()
    
    if not discovered:
        print(f"❌ 错误: 未找到子代理定义文件 (目录: {agents_dir})")
        sys.exit(1)
    
    print(f"✅ 发现 {len(discovered)} 个子代理:")
    for agent_def in discovered:
        print(f"   • {agent_def.name}: {agent_def.description}")
    
    # 添加 CallAgentTool
    call_agent_tool = CallAgentTool(
        agent_loader=agent_loader,
        llm_client=llm_client,
        all_tools=tools,
        workspace_dir=str(workspace_dir),
        call_depth=0,
        max_depth=1
    )
    tools.append(call_agent_tool)
    
    # 初始化主协调代理
    print("\n🎯 初始化主协调代理...")
    
    # 加载主代理的定义文件（必需）
    main_agent_path = current_dir / "main.md"
    if not main_agent_path.exists():
        print(f"❌ 错误: 未找到主代理定义文件: {main_agent_path}")
        print("\n主协调代理必须有明确的 MD 描述文件来指导如何整合子代理输出")
        print("请确保 agents/main-coordinator-agent.md 文件存在")
        sys.exit(1)
    
    # 读取并解析主代理定义
    try:
        main_agent_content = main_agent_path.read_text(encoding='utf-8')
        # 如果是 YAML frontmatter 格式，提取正文
        if main_agent_content.startswith('---'):
            parts = main_agent_content.split('---', 2)
            if len(parts) >= 3:
                main_agent_prompt = parts[2].strip()
            else:
                main_agent_prompt = main_agent_content
        else:
            main_agent_prompt = main_agent_content
        print(f"✅ 已加载主代理定义: {main_agent_path.name}")
    except Exception as e:
        print(f"❌ 错误: 读取主代理定义文件失败: {e}")
        sys.exit(1)
    
    # 创建主协调代理的系统提示
    system_prompt = f"""你是安全告警协调分析专家，负责全面评估安全威胁。

## 当前工作空间
{workspace_dir}

## 可用的专业子代理

{agent_loader.get_agents_metadata_prompt()}

{main_agent_prompt}

请分析以下安全告警，调用子代理并生成综合评估报告。
"""
    
    # 创建主代理
    main_agent = Agent(
        llm_client=llm_client,
        system_prompt=system_prompt,
        tools=tools,
        max_steps=15,
        workspace_dir=str(workspace_dir)
    )
    
    # 构建用户消息
    user_message = f"""请分析以下安全告警并给出风险评估:

**告警信息**
- 告警 ID: {alert.get('alert_id', 'N/A')}
- 时间戳: {alert.get('timestamp', 'N/A')}
- 攻击者 IP: {alert['attacker_ip']}
- 受害者 IP: {alert['victim_ip']}
- 攻击类型: {alert['attack_type']}
- 攻击载荷: {alert.get('payload', 'N/A')}
- 协议: {alert.get('protocol', 'N/A')}
- 目标端口: {alert.get('destination_port', 'N/A')}
"""
    
    if 'additional_context' in alert:
        user_message += f"\n**额外上下文**\n{json.dumps(alert['additional_context'], indent=2, ensure_ascii=False)}"
    
    main_agent.add_user_message(user_message)
    
    # 执行分析
    print("\n" + "=" * 80)
    print("🔍 开始分析...")
    print("=" * 80 + "\n")
    
    try:
        result = await main_agent.run()
        
        print("\n" + "=" * 80)
        print("📊 分析完成")
        print("=" * 80)
        print("\n最终评估:\n")
        print(result)
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  分析被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
