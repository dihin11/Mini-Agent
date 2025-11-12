"""Tests for AgentLoader"""

import tempfile
from pathlib import Path

import pytest

from mini_agent.tools.agent_loader import AgentDefinition, AgentLoader


@pytest.fixture
def temp_agents_dir():
    """Create temporary agents directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_agent_file(temp_agents_dir):
    """Create a sample agent file"""
    agent_content = """---
name: test_agent
description: A test agent for unit testing
tools: [read_file, write_file]
skills: [test-skill]
max_steps: 5
---

You are a test agent.

Your task: {{task}}
"""
    agent_file = temp_agents_dir / "test-agent.md"
    agent_file.write_text(agent_content, encoding="utf-8")
    return agent_file


@pytest.fixture
def minimal_agent_file(temp_agents_dir):
    """Create a minimal agent file (only required fields)"""
    agent_content = """---
name: minimal_agent
description: Minimal agent with no optional fields
---

You are a minimal agent.
"""
    agent_file = temp_agents_dir / "minimal.md"
    agent_file.write_text(agent_content, encoding="utf-8")
    return agent_file


def test_load_agent_success(sample_agent_file, temp_agents_dir):
    """Test loading a valid agent file"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agent = loader.load_agent(sample_agent_file)

    assert agent is not None
    assert agent.name == "test_agent"
    assert agent.description == "A test agent for unit testing"
    assert agent.tools == ["read_file", "write_file"]
    assert agent.skills == ["test-skill"]
    assert agent.max_steps == 5
    assert "You are a test agent" in agent.prompt
    assert "{{task}}" in agent.prompt


def test_load_minimal_agent(minimal_agent_file, temp_agents_dir):
    """Test loading agent with only required fields"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agent = loader.load_agent(minimal_agent_file)

    assert agent is not None
    assert agent.name == "minimal_agent"
    assert agent.description == "Minimal agent with no optional fields"
    assert agent.tools is None
    assert agent.skills is None
    assert agent.max_steps is None


def test_load_agent_missing_frontmatter(temp_agents_dir):
    """Test loading agent without frontmatter"""
    bad_file = temp_agents_dir / "bad.md"
    bad_file.write_text("No frontmatter here!", encoding="utf-8")

    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agent = loader.load_agent(bad_file)

    assert agent is None


def test_load_agent_missing_required_fields(temp_agents_dir):
    """Test loading agent with missing required fields"""
    bad_file = temp_agents_dir / "incomplete.md"
    bad_file.write_text(
        """---
description: Missing name field
---
Prompt here
""",
        encoding="utf-8",
    )

    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agent = loader.load_agent(bad_file)

    assert agent is None


def test_discover_agents(sample_agent_file, minimal_agent_file, temp_agents_dir):
    """Test discovering multiple agents"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agents = loader.discover_agents()

    assert len(agents) == 2
    agent_names = {agent.name for agent in agents}
    assert "test_agent" in agent_names
    assert "minimal_agent" in agent_names


def test_discover_agents_empty_dir(temp_agents_dir):
    """Test discovering agents in empty directory"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agents = loader.discover_agents()

    assert len(agents) == 0


def test_discover_agents_nonexistent_dir():
    """Test discovering agents in non-existent directory"""
    loader = AgentLoader(agents_dir="/nonexistent/path")
    agents = loader.discover_agents()

    assert len(agents) == 0


def test_get_agent(sample_agent_file, temp_agents_dir):
    """Test retrieving agent by name"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    loader.discover_agents()

    agent = loader.get_agent("test_agent")
    assert agent is not None
    assert agent.name == "test_agent"

    # Non-existent agent
    assert loader.get_agent("nonexistent") is None


def test_list_agents(sample_agent_file, minimal_agent_file, temp_agents_dir):
    """Test listing all agent names"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    loader.discover_agents()

    agent_names = loader.list_agents()
    assert len(agent_names) == 2
    assert "test_agent" in agent_names
    assert "minimal_agent" in agent_names


def test_agent_metadata_prompt(sample_agent_file, temp_agents_dir):
    """Test generating metadata prompt"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    loader.discover_agents()

    metadata = loader.get_agents_metadata_prompt()

    assert "Available Sub-Agents" in metadata
    assert "test_agent" in metadata
    assert "A test agent for unit testing" in metadata
    assert "call_agent" in metadata


def test_agent_to_metadata(sample_agent_file, temp_agents_dir):
    """Test AgentDefinition.to_metadata()"""
    loader = AgentLoader(agents_dir=str(temp_agents_dir))
    agent = loader.load_agent(sample_agent_file)

    metadata = agent.to_metadata()

    assert "test_agent" in metadata
    assert "A test agent for unit testing" in metadata
    assert "tools:" in metadata
    assert "read_file" in metadata
    assert "skills:" in metadata
    assert "test-skill" in metadata
    assert "max_steps: 5" in metadata
