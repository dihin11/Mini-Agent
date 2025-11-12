# CODEBUDDY.md
This file provides guidance to CodeBuddy Code when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

---

# Mini Agent Project Guide

## Project Overview

Mini Agent is a minimal yet professional demo showcasing best practices for building agents with the MiniMax M2 model. It features:

- Full agent execution loop with file system and shell operations
- Persistent memory via Session Note Tool
- Intelligent context management with automatic summarization (configurable token limit)
- Claude Skills integration (15+ professional skills)
- MCP (Model Context Protocol) tool integration
- Comprehensive logging for debugging

## Tech Stack

- **Language**: Python 3.10+
- **Package Manager**: `uv` (development) / `pipx` (installation)
- **Key Dependencies**: 
  - `pydantic` (data validation)
  - `httpx` (async HTTP)
  - `mcp` (Model Context Protocol)
  - `tiktoken` (token counting)
  - `prompt-toolkit` (interactive CLI)
  - `pytest` (testing)

## Development Commands

### Environment Setup

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Initialize Claude Skills submodule (optional)
git submodule update --init --recursive
```

### Configuration

```bash
# Copy example config
cp mini_agent/config/config-example.yaml mini_agent/config/config.yaml

# Edit config with your API key
vim mini_agent/config/config.yaml
```

### Running the Agent

```bash
# Method 1: Run as module (development/debugging)
uv run python -m mini_agent.cli

# Method 2: Install in editable mode (recommended for development)
pipx install -e .
mini-agent                                    # Use current directory
mini-agent --workspace /path/to/project       # Specify workspace

# Production installation (from GitHub)
pipx install git+https://github.com/MiniMax-AI/Mini-Agent.git
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_agent.py tests/test_note_tool.py -v

# Run single test
pytest tests/test_agent.py::test_agent_initialization -v

# Run with coverage
pytest tests/ --cov=mini_agent --cov-report=html
```

### Linting and Formatting

This project uses:
- `pytest` for testing
- Standard Python tooling (can be extended with `black`, `ruff`, etc.)

## Architecture Overview

### Core Components

1. **Agent Loop** (`mini_agent/agent.py`)
   - Main execution loop with step limit (`max_steps`)
   - Token-based context management with automatic summarization
   - Message history management (system, user, assistant, tool)
   - Colored terminal output for different message types

2. **LLM Client** (`mini_agent/llm.py`)
   - Anthropic-compatible API wrapper for MiniMax M2
   - Automatic retry logic with exponential backoff
   - Support for thinking tokens and tool calls
   - Error handling for API failures and billing issues

3. **Configuration** (`mini_agent/config.py`)
   - Priority-based config loading:
     1. `mini_agent/config/` (development mode)
     2. `~/.mini-agent/config/` (user config)
     3. Package installation directory (installed mode)
   - YAML-based configuration with Pydantic validation
   - Separate configs for LLM, Agent, and Tools

4. **Tools System** (`mini_agent/tools/`)
   - **Base Tool** (`base.py`): Abstract base class with `to_schema()` method
   - **File Tools** (`file_tools.py`): Read, Write, Edit with workspace-aware path resolution
   - **Bash Tool** (`bash_tool.py`): Execute shell commands, monitor background jobs
   - **Session Note** (`note_tool.py`): Persistent memory with JSON storage
   - **Skills** (`skill_tool.py`, `skill_loader.py`): Progressive disclosure (metadata → full content)
   - **MCP Loader** (`mcp_loader.py`): Load external MCP tools from config

### Key Architectural Patterns

#### 1. Context Management & Summarization

The agent automatically triggers message summarization when token count exceeds `token_limit` (default: 80,000):

- **Strategy**: Keep all user messages (intents), summarize agent execution between user messages
- **Implementation**: `_summarize_messages()` and `_create_summary()` in `agent.py`
- **Token Counting**: Uses `tiktoken` with `cl100k_base` encoder for accurate estimation

#### 2. Progressive Disclosure for Skills

**Level 1**: Skill metadata injected into system prompt (name, description, capabilities)
**Level 2**: Full skill content loaded on-demand via `get_skill` tool

This reduces initial context size while maintaining access to full skill details when needed.

#### 3. Workspace-Aware Tools

File tools resolve paths relative to the workspace directory:
- Configured via `--workspace` CLI argument or defaults to current directory
- Workspace info is injected into system prompt
- Prevents file operations outside workspace (security)

#### 4. Retry Mechanism

LLM calls automatically retry on failure with:
- Configurable max retries (default: 3)
- Exponential backoff with jitter
- Custom retry callback for terminal feedback
- Special handling for billing/quota errors

#### 5. Session State Management

- **Message History**: Maintained in `agent.messages` list
- **Tool Results**: Added as `role="tool"` messages with `tool_call_id` linkage
- **Thinking**: Stored separately in message objects (not in content)
- **Persistence**: Session notes stored in `.agent_memory.json` in workspace

### Directory Structure

```
mini_agent/
├── agent.py              # Core agent execution loop
├── cli.py                # Interactive CLI with prompt_toolkit
├── llm.py                # LLM client with retry logic
├── config.py             # Configuration management
├── schema/
│   └── schema.py         # Pydantic models (Message, ToolCall, LLMResponse)
├── tools/
│   ├── base.py           # Tool base class
│   ├── file_tools.py     # Read/Write/Edit tools
│   ├── bash_tool.py      # Bash execution
│   ├── note_tool.py      # Session memory
│   ├── skill_tool.py     # Skill tool wrapper
│   ├── skill_loader.py   # Skill discovery and loading
│   ├── agent_loader.py   # Sub-agent discovery and loading
│   ├── call_agent_tool.py # Sub-agent invocation tool
│   └── mcp_loader.py     # MCP tool loading
├── config/
│   ├── config-example.yaml    # Configuration template
│   ├── system_prompt.md       # Default system prompt
│   └── mcp.json               # MCP server configurations
└── skills/               # Claude Skills (git submodule)
    ├── document-skills/
    ├── webapp-testing/
    └── ...

tests/
├── test_agent.py         # Agent loop tests
├── test_llm.py           # LLM client tests
├── test_tools.py         # File tool tests
├── test_note_tool.py     # Session note tests
├── test_skill_tool.py    # Skill system tests
├── test_agent_loader.py  # Sub-agent loader tests
├── test_call_agent.py    # Sub-agent invocation tests
├── test_mcp.py           # MCP integration tests
└── test_integration.py   # End-to-end tests
```

## Important Patterns

### Adding New Tools

1. Inherit from `Tool` base class in `mini_agent/tools/base.py`
2. Implement required properties: `name`, `description`, `parameters`
3. Implement `async def execute(**kwargs) -> ToolResult`
4. Add tool to appropriate initialization section in `cli.py`:
   - `initialize_base_tools()` for workspace-independent tools
   - `add_workspace_tools()` for workspace-dependent tools

Example:
```python
from .base import Tool, ToolResult

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param"]
        }
    
    async def execute(self, param: str) -> ToolResult:
        try:
            result = f"Processed: {param}"
            return ToolResult(success=True, content=result)
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))
```

### Configuration Priority

The config system searches in this order:
1. Development: `./mini_agent/config/{filename}`
2. User: `~/.mini-agent/config/{filename}`
3. Package: `{site-packages}/mini_agent/config/{filename}`

Use `Config.find_config_file(filename)` for consistent resolution.

### Logging

Agent execution logs are automatically created in workspace directory:
- Format: `agent_run_YYYYMMDD_HHMMSS.log`
- Contains: All LLM requests, responses, tool calls, and results
- Access via: `self.logger` in agent code

## MCP Integration

MCP servers are configured in `mini_agent/config/mcp.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {"KEY": "value"}
    }
  }
}
```

MCP tools are loaded asynchronously at startup and cleaned up on exit.

## Skills System

Skills are Claude-compatible prompts stored in the `skills/` directory (git submodule).

**Discovery**: `SkillLoader.discover_skills()` scans for `skill.md` files
**Loading**: Skills loaded on-demand via `get_skill` tool to minimize context
**Metadata**: Name, description, capabilities injected into system prompt

## Sub-Agent System

Sub-agents are specialized agents that can be invoked by the main agent to handle specific tasks.

### Configuration

Enable sub-agents in `config.yaml`:
```yaml
tools:
  enable_agents: true
  agents:
    directory: "agents"    # Directory containing agent definitions
    auto_discover: true    # Auto-discover *.md files
    max_depth: 1           # Prevent recursive calls
```

### Agent Definition Format

Create agent files in `agents/` directory using markdown with YAML frontmatter:

```markdown
---
name: code_reviewer
description: Reviews code for bugs and best practices
tools: [read_file, grep]      # Optional: restrict available tools
skills: [code-review]          # Optional: restrict available skills
max_steps: 5                   # Optional: custom execution limit
---

You are a code review specialist.

## Your Capabilities
- Identify bugs and security issues
- Check best practices

Your task: {{task}}
```

### Key Features

**Independent Context**: Each sub-agent has:
- Isolated message history
- Isolated session notes (`.agent_memory_<agent_name>.json`)
- Shared workspace directory

**Tool Filtering**:
- If `tools` specified: only those tools available
- If `tools` omitted: all global tools available (except `call_agent`)
- `call_agent` is always excluded from sub-agents (prevents recursion)

**Invocation**:
```python
# Main agent calls sub-agent via call_agent tool
result = call_agent(
    agent_name="code_reviewer",
    task="Review the authentication module for security issues"
)
```

**Logging**: Sub-agent logs are stored separately as `agent_run_<agent_name>_<timestamp>.log`

### Architecture

- **AgentLoader** (`agent_loader.py`): Discovers and loads agent definitions
- **CallAgentTool** (`call_agent_tool.py`): Enables main agent to invoke sub-agents
- **Recursion Prevention**: `call_depth` and `max_depth` prevent nested sub-agent calls
- **Progressive Disclosure**: Agent metadata injected into main agent's system prompt

## Testing Strategy

- **Unit Tests**: Individual tool classes, LLM client, config loading
- **Functional Tests**: Session notes, skill loading, MCP integration
- **Integration Tests**: Full agent execution loops with mocked LLM
- **Coverage**: Core functionality (agent loop, tools, retry logic)

Run integration tests carefully as they may create files in workspace.
