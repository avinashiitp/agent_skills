"""
Memory Store
=============
Persistent vector memory for agents using ChromaDB.

Every conversation turn is stored as an embedding.
Before each agent run, relevant past context is retrieved
and injected into the system prompt alongside the Skill SOP.

Think of it as the agent's long-term memory:
  Without Memory: agent starts fresh every session — no context, no history
  With Memory:    agent recalls relevant past interactions before responding

Flow:
  User asks question
    → retrieve similar past interactions from ChromaDB
    → inject retrieved context into system prompt
    → agent responds with full context awareness
    → store this interaction in ChromaDB for future retrieval
"""

import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime


class MemoryStore:
    """
    Persistent vector memory backed by ChromaDB.

    Each memory entry stores:
      - role:      "user" or "agent"
      - content:   the actual text
      - agent:     which agent produced/received this
      - timestamp: when it was stored
      - session:   session ID for grouping
    """

    def __init__(self, persist_path: str = "./memory_db", collection_name: str = "agent_memory"):
        self.client = chromadb.PersistentClient(path=persist_path)

        # Built-in sentence transformer — no OpenAI key needed, runs locally
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"  🧠 MemoryStore initialised. {self.collection.count()} memories loaded.")

    def store(
        self,
        content: str,
        role: str,
        agent: str = "orchestrator",
        session_id: str = "default",
    ) -> None:
        """
        Store a single interaction in memory.

        Args:
            content:    the text to store
            role:       "user" or "agent"
            agent:      which agent this belongs to
            session_id: groups memories by conversation session
        """
        memory_id = f"{session_id}_{datetime.now().isoformat()}_{role}"

        self.collection.add(
            documents=[content],
            metadatas=[{
                "role":       role,
                "agent":      agent,
                "session_id": session_id,
                "timestamp":  datetime.now().isoformat(),
            }],
            ids=[memory_id],
        )

    def retrieve(
        self,
        query: str,
        n_results: int = 3,
        agent_filter: str | None = None,
    ) -> list[dict]:
        """
        Retrieve the most semantically similar past memories.

        Args:
            query:        current user question — used as the search vector
            n_results:    how many memories to return
            agent_filter: optionally filter by agent name

        Returns:
            list of dicts: content, role, agent, timestamp, distance
        """
        total = self.collection.count()
        if total == 0:
            return []

        n_results = min(n_results, total)
        where = {"agent": agent_filter} if agent_filter else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        memories = []
        for i, doc in enumerate(results["documents"][0]):
            memories.append({
                "content":   doc,
                "role":      results["metadatas"][0][i]["role"],
                "agent":     results["metadatas"][0][i]["agent"],
                "timestamp": results["metadatas"][0][i]["timestamp"],
                "distance":  results["distances"][0][i],
            })

        return memories

    def format_for_prompt(self, memories: list[dict]) -> str:
        """
        Format retrieved memories into a string block
        ready to be injected into the system prompt.
        """
        if not memories:
            return ""

        lines = ["── RELEVANT PAST CONTEXT ──"]
        for m in memories:
            role_label = "User asked" if m["role"] == "user" else "Agent answered"
            lines.append(f"  [{m['agent']}] {role_label}: {m['content'][:200]}")
        lines.append("── END PAST CONTEXT ──\n")

        return "\n".join(lines)

    def count(self) -> int:
        return self.collection.count()
