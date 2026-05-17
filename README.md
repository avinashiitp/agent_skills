# 🧠 Level 8 — Agent + Skills + MCP + Memory

An extension of [Level 7 (Skills)](https://github.com/avinashiitp/agent_skills) that adds **persistent Memory** — every agent now remembers past interactions across sessions using ChromaDB vector storage.

> **This repo covers Level 8 only.**
> For Level 7 (Skills/SOPs): 👉 [avinashiitp/agent_skills](https://github.com/avinashiitp/agent_skills)
> For Levels 5–6 (Agent-to-Agent + MCP): 👉 [avinashiitp/agent_to_agent](https://github.com/avinashiitp/agent_to_agent)
> For Levels 1–4 (single agent → MCP foundations): 👉 [avinashiitp/MultiTool_agents](https://github.com/avinashiitp/MultiTool_agents)

---

## 🧩 What is Memory?

| | Without Memory (Level 7) | With Memory (Level 8) |
|---|---|---|
| Between sessions | Agent forgets everything | Agent recalls relevant past interactions |
| System prompt | Skill SOP only | Memory context + Skill SOP |
| Same question asked twice | Full tool call every time | May reference past result directly |
| Debugging | "What did it do before?" → no answer | Full interaction history in ChromaDB |
| Personalisation | None | Agent builds context over time |

Memory is **semantic** — not keyword search. "France population" retrieves memories about "How many people live in France?" because they mean the same thing.

---

## 📁 Project Structure

```
level8/
├── .env                        ← API key
├── .env.example
├── requirements.txt
├── README.md
│
├── main.py                     ← Entry point — Orchestrator + all agents
├── mcp_server.py               ← 8 MCP tools (same as Level 7)
│
├── memory/
│   ├── __init__.py
│   └── memory_store.py         ← ChromaDB wrapper — save, retrieve, format
│
└── skills/
    ├── __init__.py
    ├── base_skill.py
    ├── skill_loader.py          ← Updated: accepts memory_context parameter
    ├── orchestrator_skill.py
    ├── research_skill.py
    ├── math_skill.py
    └── writing_skill.py
```

Memory is stored on disk at `./memory_db/` — persists across process restarts.

---

## 🚀 Architecture

```
User
 └── Orchestrator Agent  [OrchestratorSkill + Memory]
       │   tool: delegate_to_agent
       │
       ├── Research Agent [ResearchSkill + WeatherSkill + Memory]
       │     └── MCP tools: get_country_info, get_weather, define_word,
       │                    get_github_user, get_random_fact
       │
       ├── Math Agent     [MathSkill + Memory]
       │     └── MCP tools: calculate, convert_units
       │
       └── Writing Agent  [WritingSkill + Memory]
             └── MCP tools: analyze_text
```

Each agent has THREE power sources:
- **Skill** → tells it HOW to think (the SOP)
- **MCP tools** → gives it the ability to act (the capability)
- **Memory** → gives it context from the past (the experience)

---

## 🔑 Key Concepts

### MemoryStore

Each agent gets its own `MemoryStore` — a named ChromaDB collection:

```python
store = MemoryStore(agent_name="research", persist_dir="./memory_db")

# Save an interaction
store.save(user_input="What is France's population?", response="67.75 million")

# Retrieve top-3 semantically similar past interactions
memories = store.retrieve(query="France population stats", n_results=3)

# Format for injection into system prompt
context = store.format_for_prompt(query="France population stats")
```

### Memory → System Prompt Flow

```python
# Level 7 (no memory):
system = SkillLoader.build(ResearchSkill())
# → just the SOP

# Level 8 (with memory):
memory_context = store.format_for_prompt(query=task)
system = f"{memory_context}\n\n{skill_prompt}"
# → past relevant interactions + SOP
```

### Memory saved after every interaction

```python
# After agent completes:
store.save(user_input=task, response=final_response)
# Stored as: "User: {task} | Agent: {response}"
# ChromaDB embeds this text for future semantic retrieval
```

### Separate memory per agent

```python
memory_stores = {
    "research":     MemoryStore("research"),
    "math":         MemoryStore("math"),
    "writing":      MemoryStore("writing"),
    "orchestrator": MemoryStore("orchestrator"),
}
```

Research memories never bleed into Math memories. Each agent builds its own experience independently.

---

## 📚 Memory Reference

### `MemoryStore(agent_name, persist_dir)`
Creates or loads a ChromaDB collection for this agent. Data persists to disk.

### `store.save(user_input, response, session_id)`
Saves one interaction. Stored text: `"User: {input} | Agent: {response}"`.

### `store.retrieve(query, n_results=3)`
Semantic search — returns top-n most similar past interactions as list of dicts.

### `store.format_for_prompt(query, n_results=3)`
Returns a formatted string block ready to prepend to the skill prompt.
Returns empty string if no memories exist — prompt is not polluted.

### `store.count()`
Returns total number of stored memories.

### `store.clear()`
Deletes all memories for this agent. Also available via `clear memory` in the CLI.

---

## 🛠 Adding Memory to a New Agent

```python
# 1. Create a store
memory_stores["code"] = MemoryStore(agent_name="code")

# 2. Pass it into run_agent()
result = await run_agent(
    session=session,
    skill_prompt=SkillLoader.build(CodeSkill()),
    user_task=task,
    memory_store=memory_stores["code"],   # ← add this
    allowed_tools=["analyze_text"],
    label="Code",
)
# Memory retrieval + saving is handled automatically inside run_agent()
```

---

## ⚙️ Setup

```bash
git clone https://github.com/avinashiitp/agent_memory.git
cd agent_memory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your Anthropic API key
```

---

## ▶️ Run

```bash
python main.py mcp_server.py
```

**Special CLI commands:**
```
memory        → show memory stats for all agents
clear memory  → wipe all stored memories
```

**Try this to see memory in action:**
```
# First run:
You: What is the population of France?
# Agent calls get_country_info tool, saves result to memory

# Second run (same session or new session):
You: Tell me more about France
# Agent retrieves the France population memory, uses it as context
```

---

## 🔧 Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: chromadb` | `pip install chromadb` |
| `ModuleNotFoundError: skills` | Run from the `level8/` directory |
| `AuthenticationError` | Check `.env` has your Anthropic API key |
| `ModuleNotFoundError: mcp` | `pip install mcp` |
| Memory not persisting | Check `./memory_db/` directory exists and has write permission |

---

## 📚 Series

| Level | Repo | What it covers |
|-------|------|----------------|
| 1–4 | [MultiTool_agents](https://github.com/avinashiitp/MultiTool_agents) | Single agent → multi-tool → live APIs → MCP |
| 5–6 | [agent_to_agent](https://github.com/avinashiitp/agent_to_agent) | Agent-to-agent → Agent-to-agent-to-MCP |
| 7 | [agent_skills](https://github.com/avinashiitp/agent_skills) | Skills — structured SOPs for every agent |
| 8 | this repo | Memory — persistent vector memory via ChromaDB |

---

## License

MIT License — free to use, modify, and distribute.

Built with Claude by Anthropic.
