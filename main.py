"""
Level 7 — Agent + Skills + MCP
================================
Every agent is now powered by TWO things:
  1. A SKILL  — a structured SOP injected as the system prompt (the HOW)
  2. MCP tools — discovered at runtime from the server (the WHAT)

Architecture:
  User
   └── Orchestrator Agent  [OrchestratorSkill]
         ├── Research Agent [ResearchSkill + WeatherResearchSkill] + MCP tools
         ├── Math Agent     [MathSkill]                            + MCP tools
         └── Writing Agent  [WritingSkill]                        + MCP tools
                                   └── all tools via mcp_server.py

Key difference from Level 6:
  Level 6: system prompt = a simple one-liner describing the agent's role
  Level 7: system prompt = a full structured SOP from a Skill class
            → agents know not just WHAT to do but HOW to do it step by step
"""

import os
import sys
import json
import asyncio
import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import skills
from skills import (
    ResearchSkill,
    WeatherResearchSkill,
    MathSkill,
    WritingSkill,
    OrchestratorSkill,
)
from skills.skill_loader import SkillLoader

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-5"


# ---------------------------------------------------------------------------
# Core: Universal Agent Loop with Skills + MCP
# ---------------------------------------------------------------------------

async def run_agent(
    session: ClientSession,
    skill_prompt: str,
    user_task: str,
    allowed_tools: list[str] | None = None,
    label: str = "Agent",
) -> str:
    """
    Run a Claude agent powered by a Skill (SOP) and MCP tools.

    Args:
        session:       Active MCP session to the tool server
        skill_prompt:  The SOP built by SkillLoader — becomes the system prompt
        user_task:     The specific task this agent must complete
        allowed_tools: Which MCP tools this agent can see (agent scoping)
        label:         Display name for logging

    The key change from Level 6:
        Level 6: system=system_prompt  (a simple one-liner)
        Level 7: system=skill_prompt   (a full structured SOP from a Skill class)
    """
    # Discover and filter MCP tools
    mcp_tools = await session.list_tools()
    all_tools = mcp_tools.tools
    if allowed_tools:
        all_tools = [t for t in all_tools if t.name in allowed_tools]

    # Convert MCP format → Anthropic format
    anthropic_tools = [
        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
        for t in all_tools
    ]

    print(f"  [{label}] Skill loaded. Tools: {[t['name'] for t in anthropic_tools]}")

    messages = [{"role": "user", "content": user_task}]

    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=skill_prompt,          # ← Skill SOP as system prompt
            tools=anthropic_tools if anthropic_tools else anthropic.NOT_GIVEN,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"    [{label}] 🔧 {block.name}({json.dumps(block.input)[:60]})")
                result = await session.call_tool(block.name, block.input)
                result_text = result.content[0].text if result.content else "{}"
                print(f"    [{label}] ← {result_text[:100]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Specialist Agents — each powered by a Skill
# ---------------------------------------------------------------------------

async def research_agent(session: ClientSession, task: str) -> str:
    """
    Research Agent powered by ResearchSkill + WeatherResearchSkill combined.
    The SkillLoader merges both SOPs into one system prompt.
    """
    print(f"\n  🔬 RESEARCH AGENT ← {task}")

    # Combine two skills for this agent
    skill_prompt = SkillLoader.build(ResearchSkill(), WeatherResearchSkill())
    skill_desc = SkillLoader.describe(ResearchSkill(), WeatherResearchSkill())
    print(f"  🔬 Skills loaded: {skill_desc}")

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        allowed_tools=["get_country_info", "get_weather", "define_word",
                       "get_github_user", "get_random_fact"],
        label="Research",
    )
    print(f"  🔬 RESEARCH AGENT done.")
    return result


async def math_agent(session: ClientSession, task: str) -> str:
    """
    Math Agent powered by MathSkill.
    The SOP enforces tool-only computation and correct expression syntax.
    """
    print(f"\n  📐 MATH AGENT ← {task}")

    skill_prompt = SkillLoader.build(MathSkill())
    print(f"  📐 Skills loaded: {SkillLoader.describe(MathSkill())}")

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        allowed_tools=["calculate", "convert_units"],
        label="Math",
    )
    print(f"  📐 MATH AGENT done.")
    return result


async def writing_agent(session: ClientSession, task: str) -> str:
    """
    Writing Agent powered by WritingSkill.
    The SOP enforces audience analysis, structure, and tone calibration.
    """
    print(f"\n  ✍️  WRITING AGENT ← {task}")

    skill_prompt = SkillLoader.build(WritingSkill())
    print(f"  ✍️  Skills loaded: {SkillLoader.describe(WritingSkill())}")

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        allowed_tools=["analyze_text"],
        label="Writing",
    )
    print(f"  ✍️  WRITING AGENT done.")
    return result


# ---------------------------------------------------------------------------
# Orchestrator — powered by OrchestratorSkill
# ---------------------------------------------------------------------------

async def orchestrator(session: ClientSession, user_question: str) -> str:
    """
    Orchestrator Agent powered by OrchestratorSkill.

    The OrchestratorSkill SOP defines:
      - how to decompose questions into subtasks
      - which agent to assign each subtask to
      - how to synthesize results into a cohesive final answer

    The Orchestrator has ONE tool: delegate_to_agent.
    It does not use MCP tools directly — it delegates to specialists who do.
    """
    print(f"\n🎯 ORCHESTRATOR ← {user_question}")

    # Load the Orchestrator's skill
    skill_prompt = SkillLoader.build(OrchestratorSkill())
    print(f"🎯 Orchestrator skill loaded: {SkillLoader.describe(OrchestratorSkill())}")

    # Orchestrator's only tool — delegate to specialists
    delegation_tool = {
        "name": "delegate_to_agent",
        "description": (
            "Delegate a subtask to a specialist agent. "
            "Use 'research' for facts, countries, weather, GitHub, definitions. "
            "Use 'math' for calculations and unit conversions. "
            "Use 'writing' for drafting, editing, summarizing, word counts. "
            "Each specialist is powered by a Skill SOP — they know how to do their job."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["research", "math", "writing"],
                    "description": "Which specialist agent to delegate to",
                },
                "task": {
                    "type": "string",
                    "description": "The full subtask description for the specialist",
                },
            },
            "required": ["agent", "task"],
        },
    }

    agents = {
        "research": research_agent,
        "math":     math_agent,
        "writing":  writing_agent,
    }

    messages = [{"role": "user", "content": user_question}]

    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=skill_prompt,         # ← OrchestratorSkill SOP
            tools=[delegation_tool],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            return next((b.text for b in resp.content if hasattr(b, "text")), "")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                agent_name = block.input["agent"]
                task = block.input["task"]
                print(f"\n📤 ORCHESTRATOR → [{agent_name.upper()} AGENT] {task}")
                specialist = agents[agent_name]
                result = await specialist(session, task)
                print(f"📥 ORCHESTRATOR ← [{agent_name.upper()} AGENT] done")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py mcp_server.py")
        sys.exit(1)

    server_script = sys.argv[1]
    server_params = StdioServerParameters(
        command="python",
        args=[server_script],
        env=None,
    )

    print("=" * 65)
    print("  Level 7 — Agent + Skills + MCP")
    print("  Every agent is powered by a structured Skill SOP")
    print("=" * 65)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"\n✅ MCP Server connected. {len(tools.tools)} tools available.")
            print(f"📚 Skills loaded: ResearchSkill, WeatherResearchSkill, MathSkill, WritingSkill, OrchestratorSkill\n")

            print("Type 'quit' to exit.")
            print("Try: 'What is the population of France, convert 500km to miles, and write a one-sentence travel tip'")
            print("Try: 'Look up torvalds on GitHub and write a 2-sentence professional bio'\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break
                if not user_input:
                    continue

                answer = await orchestrator(session, user_input)
                print(f"\n✅ Final Answer:\n{answer}\n")
                print("-" * 65)


if __name__ == "__main__":
    asyncio.run(main())
