"""
Level 8 — Agent + Skills + MCP + Memory
=========================================
Every agent is now powered by THREE things:
  1. A SKILL   — structured SOP injected as the system prompt (the HOW)
  2. MCP tools — discovered at runtime from the server (the WHAT)
  3. MEMORY    — relevant past context retrieved from ChromaDB (the REMEMBER)

Architecture:
  User
   └── Orchestrator Agent  [OrchestratorSkill + Memory]
         ├── Research Agent [ResearchSkill + WeatherResearchSkill + Memory] + MCP tools
         ├── Math Agent     [MathSkill + Memory]                            + MCP tools
         └── Writing Agent  [WritingSkill + Memory]                        + MCP tools
                                   └── all tools via mcp_server.py
                                   └── all memory via ChromaDB (./memory_db)

Key difference from Level 7:
  Level 7: system = skill_prompt
  Level 8: system = memory_context + skill_prompt
            → agents know not just HOW to do it but WHAT they already know

Memory flow per turn:
  1. User asks question
  2. MemoryStore retrieves semantically similar past interactions
  3. Retrieved context injected into system prompt via SkillLoader.build_with_memory()
  4. Agent responds with full context awareness
  5. User question + agent response stored back into MemoryStore
"""

import os
import sys
import json
import uuid
import asyncio
import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from skills import (
    ResearchSkill,
    WeatherResearchSkill,
    MathSkill,
    WritingSkill,
    OrchestratorSkill,
)
from skills.skill_loader import SkillLoader
from memory.memory_store import MemoryStore

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Core: Universal Agent Loop with Skills + MCP + Memory
# ---------------------------------------------------------------------------

async def run_agent(
    session: ClientSession,
    skill_prompt: str,
    user_task: str,
    memory: MemoryStore,
    allowed_tools: list[str] | None = None,
    label: str = "Agent",
    agent_name: str = "agent",
    session_id: str = "default",
) -> str:
    """
    Run a Claude agent powered by a Skill + MCP tools + Memory.

    Key change from Level 7:
        Level 7: system = skill_prompt
        Level 8: system = SkillLoader.build_with_memory(memory_context, skill)
                 → memory context is retrieved BEFORE calling Claude
                 → agent response is stored AFTER Claude responds
    """
    # 1. Retrieve relevant past context
    past_memories = memory.retrieve(query=user_task, n_results=3)
    memory_context = memory.format_for_prompt(past_memories)

    if past_memories:
        print(f"  [{label}] 🧠 {len(past_memories)} memories retrieved")

    # 2. Build system prompt = memory context + skill SOP
    # This is the core Level 8 change — skill_prompt passed in is the raw SOP,
    # but we inject memory ABOVE it here
    full_system = f"{memory_context}\n\n{skill_prompt}" if memory_context else skill_prompt

    # 3. Discover and filter MCP tools
    mcp_tools = await session.list_tools()
    all_tools = mcp_tools.tools
    if allowed_tools:
        all_tools = [t for t in all_tools if t.name in allowed_tools]

    anthropic_tools = [
        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
        for t in all_tools
    ]

    print(f"  [{label}] Skill + Memory loaded. Tools: {[t['name'] for t in anthropic_tools]}")

    messages = [{"role": "user", "content": user_task}]

    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=full_system,           # ← Memory context + Skill SOP
            tools=anthropic_tools if anthropic_tools else anthropic.NOT_GIVEN,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            final_text = next((b.text for b in resp.content if hasattr(b, "text")), "")

            # 4. Store this interaction in memory
            memory.store(content=user_task,   role="user",  agent=agent_name, session_id=session_id)
            memory.store(content=final_text,  role="agent", agent=agent_name, session_id=session_id)
            print(f"  [{label}] 🧠 Interaction stored to memory")

            return final_text

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
# Specialist Agents
# ---------------------------------------------------------------------------

async def research_agent(session: ClientSession, task: str, memory: MemoryStore, session_id: str) -> str:
    print(f"\n  🔬 RESEARCH AGENT ← {task}")
    skill_prompt = SkillLoader.build(ResearchSkill(), WeatherResearchSkill())

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        memory=memory,
        allowed_tools=["get_country_info", "get_weather", "define_word",
                       "get_github_user", "get_random_fact"],
        label="Research",
        agent_name="research",
        session_id=session_id,
    )
    print(f"  🔬 RESEARCH AGENT done.")
    return result


async def math_agent(session: ClientSession, task: str, memory: MemoryStore, session_id: str) -> str:
    print(f"\n  📐 MATH AGENT ← {task}")
    skill_prompt = SkillLoader.build(MathSkill())

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        memory=memory,
        allowed_tools=["calculate", "convert_units"],
        label="Math",
        agent_name="math",
        session_id=session_id,
    )
    print(f"  📐 MATH AGENT done.")
    return result


async def writing_agent(session: ClientSession, task: str, memory: MemoryStore, session_id: str) -> str:
    print(f"\n  ✍️  WRITING AGENT ← {task}")
    skill_prompt = SkillLoader.build(WritingSkill())

    result = await run_agent(
        session=session,
        skill_prompt=skill_prompt,
        user_task=task,
        memory=memory,
        allowed_tools=["analyze_text"],
        label="Writing",
        agent_name="writing",
        session_id=session_id,
    )
    print(f"  ✍️  WRITING AGENT done.")
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def orchestrator(
    session: ClientSession,
    user_question: str,
    memory: MemoryStore,
    session_id: str,
) -> str:
    """
    Orchestrator with Memory.

    Memory is retrieved BEFORE decomposing the question.
    If the answer (or part of it) exists in past context,
    the OrchestratorSkill SOP instructs Claude to use it
    instead of re-delegating.
    """
    print(f"\n🎯 ORCHESTRATOR ← {user_question}")

    # Retrieve memory for the orchestrator
    past_memories = memory.retrieve(query=user_question, n_results=4)
    memory_context = memory.format_for_prompt(past_memories)

    if past_memories:
        print(f"🧠 Orchestrator: {len(past_memories)} memories retrieved")

    skill_prompt = SkillLoader.build(OrchestratorSkill())
    full_system = f"{memory_context}\n\n{skill_prompt}" if memory_context else skill_prompt

    delegation_tool = {
        "name": "delegate_to_agent",
        "description": (
            "Delegate a subtask to a specialist agent. "
            "Use 'research' for facts, countries, weather, GitHub, definitions. "
            "Use 'math' for calculations and unit conversions. "
            "Use 'writing' for drafting, editing, summarizing, word counts. "
            "Check past context first — if the answer is already known, do not re-delegate."
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
        "research": lambda task: research_agent(session, task, memory, session_id),
        "math":     lambda task: math_agent(session, task, memory, session_id),
        "writing":  lambda task: writing_agent(session, task, memory, session_id),
    }

    messages = [{"role": "user", "content": user_question}]

    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=full_system,          # ← Memory context + OrchestratorSkill SOP
            tools=[delegation_tool],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "end_turn":
            final_text = next((b.text for b in resp.content if hasattr(b, "text")), "")

            # Store orchestrator interaction
            memory.store(content=user_question, role="user",  agent="orchestrator", session_id=session_id)
            memory.store(content=final_text,    role="agent", agent="orchestrator", session_id=session_id)
            print(f"🧠 Orchestrator: interaction stored to memory")

            return final_text

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                agent_name = block.input["agent"]
                task = block.input["task"]
                print(f"\n📤 ORCHESTRATOR → [{agent_name.upper()} AGENT] {task}")
                specialist = agents[agent_name]
                result = await specialist(task)
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
    print("  Level 8 — Agent + Skills + MCP + Memory")
    print("  Every agent remembers past interactions via ChromaDB")
    print("=" * 65)

    # Initialise shared memory store (persists across sessions on disk)
    memory = MemoryStore(persist_path="./memory_db")

    # Unique session ID per run — groups this run's memories together
    session_id = str(uuid.uuid4())[:8]
    print(f"\n🔑 Session ID: {session_id}")
    print(f"🧠 Total memories in store: {memory.count()}\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"✅ MCP Server connected. {len(tools.tools)} tools available.")
            print(f"📚 Skills: ResearchSkill, MathSkill, WritingSkill, OrchestratorSkill")
            print(f"🧠 Memory: ChromaDB at ./memory_db\n")

            print("Type 'quit' to exit. Type 'memory' to see memory stats.")
            print("Try asking the same question twice — the second time uses memory.\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                if user_input.lower() == "memory":
                    print(f"🧠 Total memories stored: {memory.count()}")
                    continue

                if not user_input:
                    continue

                answer = await orchestrator(session, user_input, memory, session_id)
                print(f"\n✅ Final Answer:\n{answer}\n")
                print("-" * 65)


if __name__ == "__main__":
    asyncio.run(main())
