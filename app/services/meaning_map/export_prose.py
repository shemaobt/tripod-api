from app.db.models.meaning_map import MeaningMap


def export_prose(mm: MeaningMap) -> str:
    data = mm.data
    lines: list[str] = []

    lines.append("# Prose Meaning Map\n")
    lines.append("**Method:** Tripod Method\n")
    lines.append("---\n")

    level_1 = data.get("level_1", {})
    lines.append("#### Level 1 — The Arc\n")
    lines.append(level_1.get("arc", "") + "\n")
    lines.append("---\n")

    for scene in data.get("level_2_scenes", []):
        lines.append(
            f"#### Level 2 — Scene {scene.get('scene_number', '?')}: "
            f"Verses {scene.get('verses', '?')}\n"
        )
        if scene.get("title"):
            lines.append(f"**Title:** {scene['title']}\n")

        lines.append("##### 2A — People\n")
        for p in scene.get("people", []):
            parts = [f"**{p.get('name', '?')}**"]
            for k in ("role", "relationship", "wants", "carries"):
                if p.get(k):
                    parts.append(f"{k.replace('_', ' ').title()}: {p[k]}")
            lines.append(" ".join(parts) + "\n")

        lines.append("##### 2B — Places\n")
        for p in scene.get("places", []):
            parts = [f"**{p.get('name', '?')}**"]
            for k in ("role", "type", "meaning", "effect_on_scene"):
                if p.get(k):
                    parts.append(f"{k.replace('_', ' ').title()}: {p[k]}")
            lines.append(" ".join(parts) + "\n")

        lines.append("##### 2C — Objects and Elements\n")
        for o in scene.get("objects", []):
            parts = [f"**{o.get('name', '?')}**"]
            for k in ("what_it_is", "function_in_scene", "signals"):
                if o.get(k):
                    parts.append(f"{k.replace('_', ' ').title()}: {o[k]}")
            lines.append(" ".join(parts) + "\n")
        if scene.get("significant_absence"):
            lines.append(f"**Significant absence:** {scene['significant_absence']}\n")

        lines.append("##### 2D — What Happens\n")
        lines.append(scene.get("what_happens", "") + "\n")

        lines.append("##### 2E — Communicative Purpose\n")
        lines.append(scene.get("communicative_purpose", "") + "\n")
        lines.append("---\n")

    lines.append("#### Level 3 — The Propositions\n")
    for prop in data.get("level_3_propositions", []):
        lines.append(
            f"**Proposition {prop.get('proposition_number', '?')} "
            f"— Verse {prop.get('verse', '?')}**\n"
        )
        for qa in prop.get("content", []):
            lines.append(f"{qa.get('question', '?')} {qa.get('answer', '')}\n")
        lines.append("")

    return "\n".join(lines)
