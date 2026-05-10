"""
Skill Loader
=============
Utility that combines multiple skills into one system prompt for an agent.

An agent can have ONE primary skill or MULTIPLE skills combined.

Example:
    # Single skill
    prompt = SkillLoader.build(ResearchSkill())

    # Multiple skills combined
    prompt = SkillLoader.build(ResearchSkill(), WeatherResearchSkill())

The loader joins skills with clear section separators so Claude
can distinguish between different SOPs in one system prompt.
"""

from skills.base_skill import BaseSkill


class SkillLoader:

    @staticmethod
    def build(*skills: BaseSkill) -> str:
        """
        Combine one or more skills into a single system prompt string.

        Args:
            *skills: One or more BaseSkill instances

        Returns:
            A combined system prompt string with all SOPs clearly separated

        Example:
            prompt = SkillLoader.build(ResearchSkill(), WeatherResearchSkill())
        """
        if not skills:
            raise ValueError("At least one skill must be provided")

        if len(skills) == 1:
            # Single skill — return its prompt directly
            return skills[0].build_prompt()

        # Multiple skills — combine with clear separators
        sections = []
        for skill in skills:
            section = f"{'═' * 50}\n SKILL: {skill.name.upper()}\n{'═' * 50}\n{skill.build_prompt()}"
            sections.append(section)

        combined = "\n\n".join(sections)

        # Add a closing instruction for multi-skill agents
        combined += "\n\n── SKILL PRIORITY ──\nWhen tasks overlap multiple skills, apply the most specific skill for each part."

        return combined

    @staticmethod
    def describe(*skills: BaseSkill) -> str:
        """
        Returns a summary of all skills loaded — useful for logging.
        """
        return " + ".join(s.name for s in skills)
