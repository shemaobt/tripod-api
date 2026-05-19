from __future__ import annotations

import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.project_health import PHAgentPrompt
from app.services.project_health.agents._default_prompts import get_placeholders
from app.services.project_health.prompts.get_prompt import get_prompt_or_404


def _validate_template(template: str, required: tuple[str, ...]) -> None:
    """Ensure every required placeholder is referenced by the template."""
    tpl = string.Template(template)
    try:
        # ``substitute`` raises on missing placeholders; ``safe_substitute`` does not.
        # We want to detect missing-required AND unknown placeholders.
        identifiers = set(tpl.get_identifiers())
    except AttributeError:
        # Python < 3.11 fallback (project requires 3.11+, but keep safe).
        identifiers = set()
        tokens = template.split("$")
        for token in tokens[1:]:
            if not token:
                continue
            head = token[0]
            if head == "{":
                end = token.find("}")
                if end != -1:
                    identifiers.add(token[1:end])
            else:
                acc = ""
                for ch in token:
                    if ch.isalnum() or ch == "_":
                        acc += ch
                    else:
                        break
                if acc:
                    identifiers.add(acc)

    missing = [p for p in required if p not in identifiers]
    if missing:
        raise ValidationError(
            f"Template is missing required placeholders: {', '.join('$' + m for m in missing)}"
        )
    unknown = [p for p in identifiers if p not in required]
    if unknown:
        raise ValidationError(
            f"Template references unknown placeholders: {', '.join('$' + u for u in unknown)}. "
            f"Allowed: {', '.join('$' + r for r in required) or '(none)'}"
        )


async def update_prompt(
    db: AsyncSession,
    prompt_key: str,
    *,
    updated_by: str,
    name: str | None = None,
    description: str | None = None,
    template: str | None = None,
) -> PHAgentPrompt:
    row = await get_prompt_or_404(db, prompt_key)
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if template is not None and template != row.template:
        _validate_template(template, get_placeholders(prompt_key))
        row.template = template
        row.version = (row.version or 1) + 1
    row.updated_by = updated_by
    await db.commit()
    await db.refresh(row)
    return row
