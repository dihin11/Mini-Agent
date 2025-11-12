"""
Call Agent Tool - Invoke sub-agents for specialized tasks
"""

from pathlib import Path
from typing import List, Optional

from ..agent import Agent
from ..llm import LLMClient
from .agent_loader import AgentDefinition, AgentLoader
from .base import Tool, ToolResult


class CallAgentTool(Tool):
    """Tool for invoking sub-agents with independent context"""

    def __init__(
        self,
        agent_loader: AgentLoader,
        llm_client: LLMClient,
        all_tools: List[Tool],
        workspace_dir: str,
        call_depth: int = 0,
        max_depth: int = 1,
    ):
        """
        Initialize Call Agent Tool

        Args:
            agent_loader: AgentLoader instance with discovered agents
            llm_client: LLM client for sub-agent
            all_tools: List of all available tools (for filtering)
            workspace_dir: Workspace directory (shared with main agent)
            call_depth: Current call depth (0 = main agent, 1 = sub-agent)
            max_depth: Maximum allowed call depth
        """
        self.agent_loader = agent_loader
        self.llm_client = llm_client
        self.all_tools = all_tools
        self.workspace_dir = workspace_dir
        self.call_depth = call_depth
        self.max_depth = max_depth

    @property
    def name(self) -> str:
        return "call_agent"

    @property
    def description(self) -> str:
        agents = self.agent_loader.list_agents()
        agent_list = ", ".join(agents) if agents else "none"
        return f"Invoke a specialized sub-agent to handle a specific task. Available agents: {agent_list}"

    @property
    def parameters(self) -> dict:
        agents = self.agent_loader.list_agents()
        return {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": f"Name of the agent to invoke. Available: {', '.join(agents) if agents else 'none'}",
                    "enum": agents if agents else [],
                },
                "task": {
                    "type": "string",
                    "description": "The task description to send to the sub-agent. Be specific and clear.",
                },
            },
            "required": ["agent_name", "task"],
        }

    def _filter_tools(self, agent_def: AgentDefinition, sub_agent_name: str) -> List[Tool]:
        """
        Filter tools based on agent definition and create isolated session note tool

        Args:
            agent_def: Agent definition with optional tool restrictions
            sub_agent_name: Name of the sub-agent (for isolated session notes)

        Returns:
            Filtered list of tools
        """
        # If no restriction specified, use all tools except call_agent and record_note
        if not agent_def.tools:
            base_tools = [
                tool for tool in self.all_tools 
                if tool.name not in ["call_agent", "record_note"]
            ]
        else:
            # Filter to only allowed tools
            allowed_tool_names = set(agent_def.tools)
            base_tools = [tool for tool in self.all_tools if tool.name in allowed_tool_names]
            
            # Ensure call_agent is never available to sub-agents
            base_tools = [tool for tool in base_tools if tool.name != "call_agent"]
            
            # Remove main agent's record_note to replace with isolated version
            base_tools = [tool for tool in base_tools if tool.name != "record_note"]
        
        # Add isolated session note tool for sub-agent if needed
        # Check if record_note was in the allowed tools or unrestricted
        should_have_notes = (not agent_def.tools) or ("record_note" in agent_def.tools)
        if should_have_notes:
            from .note_tool import SessionNoteTool
            isolated_note_tool = SessionNoteTool(
                memory_file=str(Path(self.workspace_dir) / f".agent_memory_{sub_agent_name}.json")
            )
            base_tools.append(isolated_note_tool)
        
        return base_tools

    def _prepare_agent_prompt(self, agent_def: AgentDefinition, task: str) -> str:
        """
        Prepare system prompt for sub-agent by injecting task

        Args:
            agent_def: Agent definition
            task: Task description

        Returns:
            Complete system prompt with task injected
        """
        # Replace {{task}} placeholder with actual task
        prompt = agent_def.prompt.replace("{{task}}", task)
        return prompt

    async def execute(self, agent_name: str, task: str) -> ToolResult:
        """
        Execute sub-agent with given task

        Args:
            agent_name: Name of the agent to invoke
            task: Task description

        Returns:
            ToolResult with agent's final response or error
        """
        # Check recursion depth
        if self.call_depth >= self.max_depth:
            return ToolResult(
                success=False,
                error=f"Sub-agent cannot call other agents (max depth: {self.max_depth})",
            )

        # Get agent definition
        agent_def = self.agent_loader.get_agent(agent_name)
        if not agent_def:
            available = ", ".join(self.agent_loader.list_agents())
            return ToolResult(
                success=False,
                error=f"Agent '{agent_name}' not found. Available agents: {available}",
            )

        try:
            # Filter tools based on agent configuration (with isolated session notes)
            agent_tools = self._filter_tools(agent_def, agent_name)

            # Prepare system prompt with task injection
            system_prompt = self._prepare_agent_prompt(agent_def, task)

            # Determine max_steps for sub-agent
            max_steps = agent_def.max_steps if agent_def.max_steps else 10

            # Create independent Agent instance
            sub_agent = Agent(
                llm_client=self.llm_client,
                system_prompt=system_prompt,
                tools=agent_tools,
                max_steps=max_steps,
                workspace_dir=self.workspace_dir,  # Share workspace
            )

            # Override logger to use sub-agent specific log file
            from ..logger import AgentLogger

            sub_agent.logger = AgentLogger(prefix=f"{agent_name}_")

            # Execute sub-agent
            print(f"\n🤖 Invoking sub-agent: {agent_name}")
            print(f"📝 Task: {task[:100]}..." if len(task) > 100 else f"📝 Task: {task}")

            # Add the task as a user message (the system prompt provides context)
            sub_agent.add_user_message(task)
            
            # Run the sub-agent
            result = await sub_agent.run()

            # Return the sub-agent's final response
            return ToolResult(
                success=True,
                content=f"Sub-agent '{agent_name}' completed task.\n\nResult:\n{result}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute sub-agent '{agent_name}': {str(e)}",
            )
