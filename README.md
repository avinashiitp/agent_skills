# 🧠 Level 7 — Agent + Skills + MCP

An extension of the [Agent-to-Agent-to-MCP](https://github.com/avinashiitp/agent_to_agent) project (Levels 5–6) that adds **Skills** — structured SOPs that tell each agent not just *what* to do but *how* to do it.

> **This repo covers Level 7 only.**
> For Levels 5–6 (Agent-to-Agent + MCP): 👉 [avinashiitp/agent_to_agent](https://github.com/avinashiitp/agent_to_agent)
> For Levels 1–4 (single agent → MCP foundations): 👉 [avinashiitp/MultiTool_agents](https://github.com/avinashiitp/MultiTool_agents)

---

## 🧩 What is a Skill?

| | Without Skill | With Skill |
|---|---|---|
| Agent's system prompt | `"You are a Research Agent. Be concise."` | A full structured SOP: step-by-step procedure, tool selection logic, output format rules, quality checks |
| Agent behaviour | Varies — depends on Claude's defaults | Consistent — follows the SOP every time |
| Bad output | Hard to debug — is it the tools or the agent? | Easy to debug — is it the SOP or the tools? |
| Reusability | Prompt lives inside one agent | Skill is a class, importable anywhere |

A Skill is a **reusable knowledge package** — a structured prompt template / SOP that instructs an agent on how to perform a specific action, ensuring consistency and accuracy across every run.

---

## 📁 Project Structure

```
level7/
├── .env                     ← API key
├── .env.example
├── requirements.txt
├── README.md
│
├── main.py                  ← Orchestrator + all agents (entry point)
├── mcp_server.py            ← 8 MCP tools (same as Level 6)
│
└── skills/
    ├── __init__.py          ← clean exports
    ├── base_skill.py        ← abstract BaseSkill class
    ├── skill_loader.py      ← combines multiple skills into one prompt
    ├── orchestrator_skill.py← OrchestratorSkill SOP
    ├── research_skill.py    ← ResearchSkill + WeatherResearchSkill
    ├── math_skill.py        ← MathSkill + EstimationSkill
    └── writing_skill.py     ← WritingSkill + SummarizationSkill
```

---

## 🚀 Architecture

```
User
 └── Orchestrator Agent  [OrchestratorSkill SOP]
       │   tool: delegate_to_agent
       │
       ├── Research Agent [ResearchSkill + WeatherResearchSkill]
       │     └── MCP tools: get_country_info, get_weather, define_word,
       │                    get_github_user, get_random_fact
       │
       ├── Math Agent     [MathSkill]
       │     └── MCP tools: calculate, convert_units
       │
       └── Writing Agent  [WritingSkill]
             └── MCP tools: analyze_text
                   └── All via mcp_server.py → live APIs
```

Each agent has two power sources:
- **Skill** → tells it HOW to think and act (the SOP)
- **MCP tools** → gives it the ability to act (the capability)

---

## 🔑 Key Concepts

### BaseSkill

Every skill inherits from `BaseSkill`:

```python
class BaseSkill(ABC):
    @property
    def name(self) -> str: ...          # unique identifier

    @property
    def description(self) -> str: ...  # one-line summary

    def build_prompt(self) -> str: ... # returns the full SOP string
```

### SkillLoader

Combines one or more skills into a single system prompt:

```python
# Single skill
prompt = SkillLoader.build(ResearchSkill())

# Multiple skills combined — useful for agents with broad scope
prompt = SkillLoader.build(ResearchSkill(), WeatherResearchSkill())
```

### Skill → System Prompt Flow

```python
# Level 6 (no skill):
system = "You are a specialist Research Agent. Be concise and accurate."

# Level 7 (with skill):
system = SkillLoader.build(ResearchSkill())
# → injects a full SOP covering:
#   STEP 1: Understand the question
#   STEP 2: Select the right tool
#   STEP 3: Execute and validate
#   STEP 4: Format your response
#   Quality checks, output format rules...
```

---

## 📚 Skills Reference

### OrchestratorSkill
SOP for task decomposition, agent assignment, and result synthesis.
Defines exactly how the Orchestrator should break a question, which agent handles what, and how to write a cohesive final answer.

### ResearchSkill
SOP for factual research tasks.
Covers: question understanding → tool selection logic → validation → output format.

### WeatherResearchSkill
Sub-skill focused on weather queries.
Covers: location extraction → tool execution → output with practical advice.
Can be combined with ResearchSkill via `SkillLoader.build(ResearchSkill(), WeatherResearchSkill())`.

### MathSkill
SOP for calculations and unit conversions.
Covers: task classification (calculate vs convert) → expression preparation → Python-safe syntax rules → result formatting.

### EstimationSkill
Sub-skill for Fermi estimation and order-of-magnitude reasoning.
Can be combined with MathSkill for agents handling estimation tasks.

### WritingSkill
SOP for drafting, editing, summarizing, and text analysis.
Covers: task classification → planning before writing → tone calibration by audience → quality checks.

### SummarizationSkill
Sub-skill focused on condensing long content into structured summaries.
Can be combined with WritingSkill.

---

## 🛠 Adding a New Skill

Create a new file in `skills/`:

```python
# skills/code_skill.py
from skills.base_skill import BaseSkill

class CodeSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "code_skill"

    @property
    def description(self) -> str:
        return "SOP for code review, debugging, and explanation tasks"

    def build_prompt(self) -> str:
        return """
You are a specialist Code Agent.

── CODE REVIEW SOP ──

STEP 1 — UNDERSTAND THE CODE
  → Identify the language and purpose
  → Read for intent before reading for bugs

STEP 2 — ANALYSE
  → Check logic correctness first
  → Check edge cases second
  → Check style last

STEP 3 — RESPOND
  → Lead with the most critical issue
  → Suggest fixes, not just problems
""".strip()
```

Then export it in `skills/__init__.py` and load it in any agent:

```python
from skills import CodeSkill
skill_prompt = SkillLoader.build(CodeSkill())
```

---

## 🛠 Adding a New Agent

1. Add the agent function in `main.py`:
```python
async def code_agent(session, task):
    skill_prompt = SkillLoader.build(CodeSkill())
    return await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        allowed_tools=["analyze_text"],   # add code tools to mcp_server.py
        label="Code",
    )
```

2. Register in the Orchestrator's routing table:
```python
agents = {
    "research": research_agent,
    "math":     math_agent,
    "writing":  writing_agent,
    "code":     code_agent,        # ← add here
}
```

3. Add `"code"` to the `delegate_to_agent` enum in the delegation tool.

---

## ⚙️ Setup

```bash
git clone https://github.com/avinashiitp/level7_skills.git
cd level7_skills
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

Try:
```
You: What is the population of France, convert 500km to miles, and write a travel tip
You: Look up torvalds on GitHub and write a 2-sentence professional bio
You: Define 'serendipity', calculate 2**16, and write a sentence using the word
```

---

## 🔧 Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: skills` | Run from the `level7/` directory |
| `AuthenticationError` | Check `.env` has your Anthropic API key |
| `ModuleNotFoundError: mcp` | `pip install mcp` |
| `ModuleNotFoundError: dotenv` | `pip install python-dotenv` |
| Agent gives generic answer | Check the skill's SOP — improve the relevant step |

---

## 📚 Series

| Level | Repo | What it covers |
|-------|------|----------------|
| 1–4 | [MultiTool_agents](https://github.com/avinashiitp/MultiTool_agents) | Single agent → multi-tool → live APIs → MCP |
| 5–6 | [agent_to_agent](https://github.com/avinashiitp/agent_to_agent) | Agent-to-agent → Agent-to-agent-to-MCP |
| 7 | this repo | Skills — structured SOPs for every agent |

---

## License

MIT License — free to use, modify, and distribute.

Built with Claude by Anthropic.
