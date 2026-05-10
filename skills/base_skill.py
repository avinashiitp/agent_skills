"""
Base Skill Class
=================
A Skill is a reusable knowledge package — a structured SOP (Standard Operating Procedure)
that tells an agent HOW to perform a specific task.

Think of it as the difference between:
  Without Skill: "You are a Research Agent. Be concise."
  With Skill:    A detailed step-by-step SOP injected into the agent's system prompt
                 that defines exactly how to research, in what order, with what checks.

Every skill in this project inherits from BaseSkill.
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    A skill has three responsibilities:
    1. build_prompt()   — returns the SOP as a string injected into the agent's system prompt
    2. name             — identifier for logging and debugging
    3. description      — one-line summary of what this skill does
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this skill. e.g. 'research_skill'"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line summary. e.g. 'Structured SOP for factual research tasks'"""
        pass

    @abstractmethod
    def build_prompt(self) -> str:
        """
        Returns the full SOP as a string.
        This gets injected into the agent's system prompt.
        Should define: role, step-by-step process, output format, quality checks.
        """
        pass

    def __repr__(self):
        return f"<Skill: {self.name}>"
