"""
Agent Loader - Load Sub-Agents

Supports loading agent definitions from *.md files with YAML frontmatter
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class AgentDefinition:
    """Agent definition data structure"""

    name: str
    description: str
    prompt: str
    tools: Optional[List[str]] = None  # Optional: restrict to specific tools
    skills: Optional[List[str]] = None  # Optional: restrict to specific skills
    max_steps: Optional[int] = None  # Optional: custom step limit
    agent_path: Optional[Path] = None

    def to_metadata(self) -> str:
        """Convert agent to metadata format for system prompt"""
        metadata = f"- `{self.name}`: {self.description}"
        if self.tools:
            metadata += f" (tools: {', '.join(self.tools)})"
        if self.skills:
            metadata += f" (skills: {', '.join(self.skills)})"
        if self.max_steps:
            metadata += f" (max_steps: {self.max_steps})"
        return metadata


class AgentLoader:
    """Agent loader for discovering and loading sub-agents"""

    def __init__(self, agents_dir: str = "agents"):
        """
        Initialize Agent Loader

        Args:
            agents_dir: Agents directory path
        """
        self.agents_dir = Path(agents_dir)
        self.loaded_agents: Dict[str, AgentDefinition] = {}

    def load_agent(self, agent_path: Path) -> Optional[AgentDefinition]:
        """
        Load single agent from *.md file with YAML frontmatter

        Args:
            agent_path: Agent markdown file path

        Returns:
            AgentDefinition object, or None if loading fails
        """
        try:
            content = agent_path.read_text(encoding="utf-8")

            # Parse YAML frontmatter
            frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)

            if not frontmatter_match:
                print(f"⚠️  {agent_path} missing YAML frontmatter")
                return None

            frontmatter_text = frontmatter_match.group(1)
            agent_prompt = frontmatter_match.group(2).strip()

            # Parse YAML
            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                print(f"❌ Failed to parse YAML frontmatter in {agent_path}: {e}")
                return None

            # Required fields
            if "name" not in frontmatter or "description" not in frontmatter:
                print(f"⚠️  {agent_path} missing required fields (name or description)")
                return None

            # Create AgentDefinition object
            agent = AgentDefinition(
                name=frontmatter["name"],
                description=frontmatter["description"],
                prompt=agent_prompt,
                tools=frontmatter.get("tools"),
                skills=frontmatter.get("skills"),
                max_steps=frontmatter.get("max_steps"),
                agent_path=agent_path,
            )

            return agent

        except Exception as e:
            print(f"❌ Failed to load agent ({agent_path}): {e}")
            return None

    def discover_agents(self) -> List[AgentDefinition]:
        """
        Discover and load all agents in the agents directory

        Returns:
            List of AgentDefinitions
        """
        agents = []

        if not self.agents_dir.exists():
            print(f"⚠️  Agents directory does not exist: {self.agents_dir}")
            return agents

        # Find all *.md files in agents directory (non-recursive)
        for agent_file in self.agents_dir.glob("*.md"):
            agent = self.load_agent(agent_file)
            if agent:
                agents.append(agent)
                self.loaded_agents[agent.name] = agent

        return agents

    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """
        Get loaded agent by name

        Args:
            name: Agent name

        Returns:
            AgentDefinition object, or None if not found
        """
        return self.loaded_agents.get(name)

    def list_agents(self) -> List[str]:
        """
        List all loaded agent names

        Returns:
            List of agent names
        """
        return list(self.loaded_agents.keys())

    def get_agents_metadata_prompt(self) -> str:
        """
        Generate prompt containing metadata for all available sub-agents.
        This is injected into the main agent's system prompt.

        Returns:
            Metadata prompt string
        """
        if not self.loaded_agents:
            return ""

        prompt_parts = ["## Available Sub-Agents\n"]
        prompt_parts.append(
            "You have access to specialized sub-agents. Each sub-agent is an independent agent "
            "with its own context and capabilities, designed for specific tasks.\n"
        )
        prompt_parts.append("Call a sub-agent using the `call_agent` tool when you need specialized assistance.\n")

        # List all agents with their metadata
        for agent in self.loaded_agents.values():
            prompt_parts.append(agent.to_metadata())

        return "\n".join(prompt_parts)
