"""Tests for CallAgentTool"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mini_agent.tools.agent_loader import AgentDefinition, AgentLoader
from mini_agent.tools.base import Tool, ToolResult
from mini_agent.tools.call_agent_tool import CallAgentTool


class MockTool(Tool):
    """Mock tool for testing"""

    def __init__(self, tool_name: str):
        self._name = tool_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Mock {self._name}"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, content=f"Executed {self._name}")


@pytest.fixture
def temp_agents_dir():
    """Create temporary agents directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_agent(temp_agents_dir):
    """Create a sample agent"""
    agent_content = """---
name: test_agent
description: A test agent
tools: [read_file, grep]
max_steps: 3
---

You are a test agent. Execute the following task: {{task}}
"""
    agent_file = temp_agents_dir / "test.md"
    agent_file.write_text(agent_content, encoding="utf-8")

    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    loader.discover_agents()
    return loader


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client"""
    return MagicMock()


@pytest.fixture
def mock_tools():
    """Create mock tools"""
    return [
        MockTool("read_file"),
        MockTool("write_file"),
        MockTool("grep"),
        MockTool("bash"),
        MockTool("record_note"),
    ]


def test_call_agent_tool_init(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test CallAgentTool initialization"""
    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
        call_depth=0,
        max_depth=1,
    )

    assert tool.name == "call_agent"
    assert "test_agent" in tool.description
    assert tool.call_depth == 0
    assert tool.max_depth == 1


def test_filter_tools_unrestricted(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test tool filtering with unrestricted agent"""
    # Create agent without tool restrictions
    unrestricted_agent = AgentDefinition(
        name="unrestricted",
        description="No restrictions",
        prompt="Test",
        tools=None,  # No restrictions
    )

    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
    )

    filtered = tool._filter_tools(unrestricted_agent, "unrestricted")

    # Should include all tools except call_agent, plus isolated record_note
    tool_names = {t.name for t in filtered}
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "bash" in tool_names
    assert "call_agent" not in tool_names  # Excluded to prevent recursion
    assert "record_note" in tool_names  # Isolated version added


def test_filter_tools_restricted(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test tool filtering with restricted agent"""
    restricted_agent = AgentDefinition(
        name="restricted",
        description="Restricted agent",
        prompt="Test",
        tools=["read_file", "grep"],  # Only these tools
    )

    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
    )

    filtered = tool._filter_tools(restricted_agent, "restricted")

    tool_names = {t.name for t in filtered}
    assert "read_file" in tool_names
    assert "grep" in tool_names
    assert "write_file" not in tool_names
    assert "bash" not in tool_names
    assert "call_agent" not in tool_names


def test_prepare_agent_prompt(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test task injection into agent prompt"""
    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
    )

    agent_def = sample_agent.get_agent("test_agent")
    task = "Review the code in main.py"

    prompt = tool._prepare_agent_prompt(agent_def, task)

    assert "Review the code in main.py" in prompt
    assert "{{task}}" not in prompt  # Should be replaced


@pytest.mark.asyncio
async def test_execute_agent_not_found(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test calling non-existent agent"""
    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
    )

    result = await tool.execute(agent_name="nonexistent", task="Do something")

    assert result.success is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_execute_recursion_blocked(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test that sub-agents cannot call other agents"""
    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
        call_depth=1,  # Already at depth 1 (sub-agent level)
        max_depth=1,
    )

    result = await tool.execute(agent_name="test_agent", task="Do something")

    assert result.success is False
    assert "cannot call other agents" in result.error


def test_parameters_schema(sample_agent, mock_llm_client, mock_tools, temp_agents_dir):
    """Test that parameters schema includes available agents"""
    tool = CallAgentTool(
        agent_loader=sample_agent,
        llm_client=mock_llm_client,
        all_tools=mock_tools,
        workspace_dir=str(temp_agents_dir),
    )

    params = tool.parameters

    assert "properties" in params
    assert "agent_name" in params["properties"]
    assert "task" in params["properties"]
    assert params["properties"]["agent_name"]["enum"] == ["test_agent"]
