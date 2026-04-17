"""Shared Jinja2 environment for every LLM-facing prompt.

Every `.j2` template lives in ``src/llm/prompts/``. Both the report service and
the chat router render through this module so the same loader config, autoescape
policy, and whitespace settings apply everywhere. Keeping the env cached
avoids re-scanning the templates directory on every request.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

PROMPTS_DIR: Path = Path(__file__).resolve().parent / "prompts"


@cache
def _env() -> Environment:
    """Return the process-wide Jinja environment for LLM prompts."""
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=False,
    )


def render(template_name: str, **context: Any) -> str:
    """Render ``template_name`` (relative to ``prompts/``) with the given context."""
    template = _env().get_template(template_name)
    return template.render(**context)
