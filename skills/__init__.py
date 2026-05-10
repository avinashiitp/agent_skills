"""
Skills Package
===============
All skills are imported here for clean access across the project.

Usage:
    from skills import ResearchSkill, MathSkill, WritingSkill, OrchestratorSkill
    from skills import WeatherResearchSkill, EstimationSkill, SummarizationSkill
"""

from skills.base_skill import BaseSkill
from skills.research_skill import ResearchSkill, WeatherResearchSkill
from skills.math_skill import MathSkill, EstimationSkill
from skills.writing_skill import WritingSkill, SummarizationSkill
from skills.orchestrator_skill import OrchestratorSkill

__all__ = [
    "BaseSkill",
    "ResearchSkill",
    "WeatherResearchSkill",
    "MathSkill",
    "EstimationSkill",
    "WritingSkill",
    "SummarizationSkill",
    "OrchestratorSkill",
]
