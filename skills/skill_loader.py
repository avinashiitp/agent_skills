"""
Skill Loader — Level 8
=======================
Combines one or more skills into a single system prompt.
Memory context is injected BEFORE the skill SOP by main.py.
"""

from skills.base_skill import BaseSkill


class SkillLoader:

    @staticmethod
    def build(*skills: BaseSkill) -> str:
        if not skills:
            raise ValueError("At least one skill must be provided")

        if len(skills) == 1:
            return skills[0].build_prompt()

        sections = []
        for skill in skills:
            section = f"{'═' * 50}\n SKILL: {skill.name.upper()}\n{'═' * 50}\n{skill.build_prompt()}"
            sections.append(section)

        combined = "\n\n".join(sections)
        combined += "\n\n── SKILL PRIORITY ──\nWhen tasks overlap multiple skills, apply the most specific skill for each part."
        return combined

    @staticmethod
    def build_with_memory(memory_context: str, *skills: BaseSkill) -> str:
        """
        Build system prompt with memory context injected BEFORE the skill SOP.

        Args:
            memory_context: formatted string from MemoryStore.format_for_prompt()
            *skills:        one or more skill instances

        Returns:
            combined string: memory context + skill SOP(s)

        This is the key Level 8 addition:
            Level 7: system = skill_prompt
            Level 8: system = memory_context + skill_prompt
        """
        skill_prompt = SkillLoader.build(*skills)

        if not memory_context:
            return skill_prompt

        return f"{memory_context}\n\n{skill_prompt}"

    @staticmethod
    def describe(*skills: BaseSkill) -> str:
        return " + ".join(s.name for s in skills)
