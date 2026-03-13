from __future__ import annotations

from typing import Any

from app.services.book_context.generation.bhsa_stream import stream_book_clauses

_PERSON_TYPES = frozenset({"pers", "ppde", "pers,gens", "pers,god"})
_PLACE_TYPES = frozenset({"topo", "gens,topo"})
_SKIP_TYPES = frozenset({"mens"})


def _classify_nametype(nametype: str) -> str:

    if nametype in _PERSON_TYPES:
        return "person"
    if nametype in _PLACE_TYPES:
        return "place"
    if nametype in _SKIP_TYPES:
        return "skip"

    if "pers" in nametype:
        return "person"
    if "topo" in nametype:
        return "place"
    return "ambiguous"


def extract_bhsa_entities(tf_api: Any, book_name: str, chapter_count: int) -> dict[str, Any]:

    name_appearances: dict[str, list[dict[str, int]]] = {}
    name_first: dict[str, dict[str, int]] = {}
    name_last: dict[str, dict[str, int]] = {}
    name_glosses: dict[str, str] = {}
    name_types: dict[str, str] = {}

    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        for clause in chapter_data["clauses"]:
            v = clause["verse"]
            ref = {"chapter": ch, "verse": v}

            for name in clause.get("names", []):
                if name not in name_appearances:
                    name_appearances[name] = []
                    name_first[name] = ref

                if not name_appearances[name] or name_appearances[name][-1] != ref:
                    name_appearances[name].append(ref)

                name_last[name] = ref

            for heb_name, gloss in clause.get("name_glosses", {}).items():
                if heb_name not in name_glosses and gloss:
                    name_glosses[heb_name] = gloss

            for heb_name, nt in clause.get("name_types", {}).items():
                if heb_name not in name_types and nt:
                    name_types[heb_name] = nt

    entities = []
    for name in sorted(name_appearances.keys()):
        raw_nametype = name_types.get(name, "")
        entity_type = _classify_nametype(raw_nametype) if raw_nametype else "ambiguous"

        if entity_type == "skip":
            continue

        entities.append(
            {
                "name": name,
                "english_gloss": name_glosses.get(name, ""),
                "entity_type": entity_type,
                "entry_verse": name_first[name],
                "exit_verse": name_last[name],
                "appears_in": name_appearances[name],
                "appearance_count": len(name_appearances[name]),
            }
        )

    return {"bhsa_entities": entities}
