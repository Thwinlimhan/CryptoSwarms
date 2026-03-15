from __future__ import annotations

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json

from cryptoswarms.adapters.llm import LLMClient

@dataclass
class SkillMetadata:
    name: str
    description: str

class SkillAgent:
    """An agent that performs tasks based on a Skill.md definition."""

    def __init__(self, skill_name: str, skills_dir: str = "skills", llm: Optional[LLMClient] = None):
        self.skill_name = skill_name
        self.skill_path = Path(skills_dir) / skill_name / "SKILL.md"
        self.llm = llm or LLMClient()
        self.metadata: Optional[SkillMetadata] = None
        self.instructions: str = ""
        
        self._load_skill()

    def _load_skill(self):
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {self.skill_path}")

        content = self.skill_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            _, frontmatter, body = content.split("---", 2)
            meta = yaml.safe_load(frontmatter)
            self.metadata = SkillMetadata(name=meta["name"], description=meta["description"])
            self.instructions = body.strip()
        else:
            self.instructions = content.strip()

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the skill with the given payload."""
        prompt = f"""
{self.instructions}

### CURRENT DATA CONTEXT
{json.dumps(payload, indent=2)}

### EXECUTION
Analyze the data context according to the PROCEDURES and return the final JSON result.
"""
        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            json_response=True
        )
        return json.loads(response)
