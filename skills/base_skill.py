"""
Base Skill Class
=================
Abstract base class all skills inherit from.
Every skill must implement: name, description, build_prompt()
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def build_prompt(self) -> str:
        pass

    def __repr__(self):
        return f"<Skill: {self.name}>"
