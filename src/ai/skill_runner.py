"""Local Skill Runner for Semblance Canvas.

Loads local skill definitions and JSON schemas, executes them via the configured AI backend,
and validates adherence to Non-Invention rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from src.ai.client import BaseAIClient, get_ai_client
from src.audio.realtime_stt import SourceSegment


class SkillExecutionError(Exception):
    pass


class NonInventionViolationError(SkillExecutionError):
    pass


class SkillRunner:
    """Orchestrates local skills execution and schema validation."""

    def __init__(self, ai_client: Optional[BaseAIClient] = None, skills_dir: Optional[Path] = None):
        self.ai_client = ai_client or get_ai_client()
        self.skills_dir = skills_dir or Path(__file__).resolve().parent.parent.parent / "skills"

    def _load_skill_assets(self, skill_name: str) -> tuple[str, Dict[str, Any]]:
        target_dir = self.skills_dir / skill_name
        skill_md_path = target_dir / "SKILL.md"
        schema_path = target_dir / "schema.json"

        if not skill_md_path.is_file():
            raise FileNotFoundError(f"Skill instruction file not found: {skill_md_path}")
        if not schema_path.is_file():
            raise FileNotFoundError(f"Skill schema file not found: {schema_path}")

        instructions = skill_md_path.read_text(encoding="utf-8")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        return instructions, schema

    def run_text_to_semantic(self, segments: List[SourceSegment]) -> Dict[str, Any]:
        """Skill 1: Translates raw transcript segments into logical adaptive semantic JSON."""
        instructions, schema = self._load_skill_assets("text_to_semantic_json")

        segments_payload = json.dumps([s.to_dict() for s in segments], indent=2)
        prompt = (
            f"Analyze the following transcribed speech segments and convert them into the requested "
            f"logical adaptive semantic JSON structure.\n\n"
            f"INPUT TRANSCRIPT SEGMENTS:\n{segments_payload}\n\n"
            f"Adhere strictly to the Non-Invention Rule. Respond ONLY with valid JSON."
        )

        raw_result = self.ai_client.generate_json(prompt=prompt, system_instruction=instructions)

        # 1. JSON Schema validation
        try:
            jsonschema.validate(instance=raw_result, schema=schema)
        except jsonschema.ValidationError as e:
            raise SkillExecutionError(f"Skill 1 output failed schema validation: {e.message}")

        # 2. Strict Non-Invention Verification
        valid_source_ids = {s.id for s in segments}

        # Check concepts
        for c in raw_result.get("concepts", []):
            c_type = c.get("type")
            sources = c.get("source_ids", [])
            if c_type not in ("template_scaffolding", "placeholder"):
                if not sources:
                    raise NonInventionViolationError(
                        f"Non-Invention Rule Violation: Concept '{c.get('label')}' (ID: {c.get('id')}) has no source_ids!"
                    )
                for sid in sources:
                    if sid not in valid_source_ids:
                        raise NonInventionViolationError(
                            f"Non-Invention Rule Violation: Concept '{c.get('label')}' cites non-existent source '{sid}'"
                        )

        # Check relationships (MANDATORY PROVENANCE)
        for r in raw_result.get("relationships", []):
            sources = r.get("source_ids", [])
            if not sources:
                raise NonInventionViolationError(
                    f"Non-Invention Rule Violation: Relationship between '{r.get('source')}' and '{r.get('target')}' has no source_ids!"
                )
            for sid in sources:
                if sid not in valid_source_ids:
                    raise NonInventionViolationError(
                        f"Non-Invention Rule Violation: Relationship cites non-existent source '{sid}'"
                    )

        return raw_result

    def run_semantic_to_canvas(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Skill 2: Translates logical adaptive semantic JSON into visual canvas JSON."""
        instructions, schema = self._load_skill_assets("semantic_json_to_canvas_json")

        semantic_payload = json.dumps(semantic_data, indent=2)
        prompt = (
            f"Translate the following logical semantic data into a clean, well-spaced visual canvas JSON layout.\n\n"
            f"SEMANTIC DATA:\n{semantic_payload}\n\n"
            f"Ensure nodes belonging to the same cluster are placed in visual proximity without drawing unrequested edges.\n"
            f"Respond ONLY with valid JSON conforming to the schema."
        )

        raw_result = self.ai_client.generate_json(prompt=prompt, system_instruction=instructions)

        # JSON Schema validation
        try:
            jsonschema.validate(instance=raw_result, schema=schema)
        except jsonschema.ValidationError as e:
            raise SkillExecutionError(f"Skill 2 output failed schema validation: {e.message}")

        return raw_result
