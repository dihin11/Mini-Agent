# Sub-Agent System Demo

This example demonstrates the complete workflow of Mini-Agent's sub-agent system.

## What This Demo Shows

1. **Agent Discovery**: Automatically discovering sub-agents from markdown files
2. **Specialized Sub-Agents**: 
   - `math_calculator`: Performs calculations using bash/Python
   - `code_analyzer`: Analyzes code files and generates reports
3. **Tool Filtering**: Each sub-agent has restricted tool access
4. **Context Isolation**: Sub-agents have independent session notes
5. **Recursion Prevention**: Sub-agents cannot call other agents
6. **Main Agent Delegation**: Main agent intelligently delegates to sub-agents

## Running the Demo

### Prerequisites

Make sure you have Mini-Agent installed:

```bash
# From the repository root
pip install -e .
```

### Run the Demo

```bash
cd examples/sub-agent-demo
python demo.py
```

**Note**: This demo uses a simplified `MockLLMClient` for demonstration purposes. The mock responses are hardcoded and may loop in certain scenarios. For a fully functional example with real LLM, see the "Using Real LLM" section below.

### Expected Output

You should see:

1. **Setup Phase**:
   - Creation of temporary workspace
   - Two sub-agents being created (math_calculator, code_analyzer)
   - Sample Python code file creation
   - Agent system initialization

2. **Test Case 1 - Math Calculation**:
   - Main agent receives: "Please calculate: 15 * 37 + 128"
   - Main agent calls `math_calculator` sub-agent
   - Sub-agent uses `bash` tool to execute Python calculation
   - Result: 683

3. **Test Case 2 - Code Analysis**:
   - Main agent receives: "Please analyze the code in sample.py"
   - Main agent calls `code_analyzer` sub-agent
   - Sub-agent reads file using `read_file` tool
   - Result: Identifies 1 class and 5 functions

4. **Verification**:
   - Shows separate session note files for each agent
   - Demonstrates recursion prevention
   - Confirms context isolation

## Demo Architecture

```
examples/sub-agent-demo/
├── demo.py              # Main demo script
├── README.md            # This file
└── (temporary files created during runtime)
    ├── agents/
    │   ├── math-calculator.md
    │   └── code-analyzer.md
    ├── sample.py
    ├── .agent_memory.json                      # Main agent notes
    ├── .agent_memory_math_calculator.json      # Sub-agent notes (if used)
    └── .agent_memory_code_analyzer.json        # Sub-agent notes (if used)
```

## Key Concepts Demonstrated

### 1. Sub-Agent Definition

Each sub-agent is defined using YAML frontmatter:

```markdown
---
name: math_calculator
description: Performs mathematical calculations
tools: [bash]              # Restricted to bash only
max_steps: 3               # Limited execution steps
---

You are a calculation specialist...
Your task: {{task}}
```

### 2. Tool Filtering

- `math_calculator`: Only has access to `bash` tool
- `code_analyzer`: Only has access to `read_file` and `write_file`
- Main agent: Has access to all tools + `call_agent`

### 3. Context Isolation

Each agent maintains:
- **Independent message history**: Fresh start for each invocation
- **Isolated session notes**: Stored in separate JSON files
- **Shared workspace**: Can access the same files

### 4. Recursion Prevention

The `call_agent` tool is automatically excluded from sub-agents:
- `call_depth=0`: Main agent (can call sub-agents)
- `call_depth=1`: Sub-agent (cannot call other agents)
- Attempts to call agents from sub-agents return an error

## Customization

### Adding More Sub-Agents

Create a new `.md` file in the `agents/` directory:

```markdown
---
name: my_agent
description: My custom agent
tools: [tool1, tool2]
max_steps: 5
---

Your specialized prompt here.
Your task: {{task}}
```

### Using Real LLM

Replace the `MockLLMClient` with an actual `LLMClient`:

```python
from mini_agent.llm import LLMClient

llm_client = LLMClient(
    api_key="your-api-key",
    api_base="https://api.minimax.io/anthropic",
    model="MiniMax-M2"
)
```

### Different Workspace

Change the workspace to a persistent directory:

```python
workspace = Path("/path/to/your/workspace")
workspace.mkdir(parents=True, exist_ok=True)
```

## Troubleshooting

### No sub-agents discovered

**Problem**: Agent loader finds 0 agents  
**Solution**: Check that `.md` files are in the `agents/` directory and have valid YAML frontmatter

### Tool not available error

**Problem**: Sub-agent tries to use a restricted tool  
**Solution**: Add the tool name to the `tools` list in frontmatter

### Recursion error

**Problem**: "Sub-agent cannot call other agents"  
**Solution**: This is expected behavior; redesign to avoid nested calls

## Next Steps

1. **Run with real LLM**: Replace MockLLMClient with actual API calls
2. **Create domain-specific agents**: Build agents for your use cases
3. **Integrate with your workflow**: Add to your existing Mini-Agent setup
4. **Experiment with tool combinations**: Test different tool restrictions

## Related Documentation

- Main documentation: `../../CODEBUDDY.md` (Sub-Agent System section)
- Agent examples: `../../agents/README.md`
- Configuration: `../../mini_agent/config/config-example.yaml`
