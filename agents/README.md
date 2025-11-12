# Sub-Agent Examples

This directory contains example sub-agent definitions for the Mini-Agent system.

## Quick Start

1. **Enable sub-agents** in your `config.yaml`:
```yaml
tools:
  enable_agents: true
  agents:
    directory: "agents"
    auto_discover: true
    max_depth: 1
```

2. **Run mini-agent**:
```bash
mini-agent
```

3. **Invoke a sub-agent** from the main agent:
```
You: Please review the code in mini_agent/config.py for potential issues

Agent: I'll use the code_reviewer sub-agent to analyze that file.
[Calls: call_agent(agent_name="code_reviewer", task="Review mini_agent/config.py...")]
```

## Available Sub-Agents

### code-reviewer
**Purpose**: Reviews code for bugs, security issues, and best practices  
**Tools**: `read_file`, `grep`  
**Max Steps**: 5

**Example usage**:
```
call_agent(
    agent_name="code_reviewer",
    task="Review the authentication module in auth.py for security vulnerabilities"
)
```

### test-generator
**Purpose**: Generates comprehensive unit tests for Python code  
**Tools**: `read_file`, `write_file`  
**Max Steps**: 10

**Example usage**:
```
call_agent(
    agent_name="test_generator",
    task="Generate pytest tests for the LLMClient class in mini_agent/llm.py"
)
```

## Creating Custom Sub-Agents

Create a new `.md` file in this directory:

```markdown
---
name: my_agent
description: Brief description of what this agent does
tools: [read_file, write_file]  # Optional: restrict tools
skills: [my-skill]               # Optional: restrict skills
max_steps: 10                    # Optional: execution limit
---

You are a specialized agent for [purpose].

## Your Capabilities
- Capability 1
- Capability 2

## Process
1. Step 1
2. Step 2

Your task: {{task}}
```

### Field Descriptions

- **name** (required): Unique identifier for the agent
- **description** (required): Brief description shown in main agent's context
- **tools** (optional): Whitelist of allowed tools. If omitted, all global tools are available (except `call_agent`)
- **skills** (optional): Whitelist of allowed skills. If omitted, all skills are available
- **max_steps** (optional): Maximum execution steps. If omitted, uses default (10)
- **{{task}}** placeholder: Will be replaced with the task passed via `call_agent`

## Architecture Notes

### Context Isolation
Each sub-agent has:
- **Independent message history**: Starts fresh for each invocation
- **Isolated session notes**: Stored in `.agent_memory_<agent_name>.json`
- **Shared workspace**: Can access the same files as main agent

### Recursion Prevention
- Sub-agents cannot call other sub-agents
- The `call_agent` tool is automatically excluded from sub-agents
- Maximum call depth is enforced via `max_depth` configuration

### Logging
- Sub-agent execution is logged separately
- Log format: `agent_run_<agent_name>_<timestamp>.log`
- Stored in `~/.mini-agent/log/`

## Best Practices

1. **Keep agents focused**: Each sub-agent should handle one specific domain
2. **Limit tools**: Only grant necessary tools to reduce complexity
3. **Set appropriate max_steps**: Balance between capability and token usage
4. **Clear task descriptions**: The `{{task}}` should guide the agent effectively
5. **Document capabilities**: Help the main agent understand when to use each sub-agent

## Troubleshooting

### Agent not discovered
- Check that the file is in the `agents/` directory
- Verify the file has `.md` extension
- Ensure YAML frontmatter is properly formatted with `---` delimiters
- Check that required fields (`name`, `description`) are present

### Agent execution fails
- Verify the tools specified in frontmatter are available globally
- Check log files in `~/.mini-agent/log/` for detailed error messages
- Ensure `max_steps` is sufficient for the task complexity

### Tools not available
- Check main agent's tool configuration in `config.yaml`
- Remember that `call_agent` is never available to sub-agents
- Verify tool names match exactly (case-sensitive)
