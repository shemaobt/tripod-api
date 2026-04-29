from __future__ import annotations

from typing import Any

_MAINLINE_TYPES = frozenset({"Way0", "WayX"})
_CONTENT_FUNCTIONS = frozenset({"Subj", "Objc", "Cmpl", "PreC"})
_PRONOMINAL_PDP = frozenset({"prde", "prps", "prin", "intj"})


def is_mainline(clause_type: str) -> bool:
    return clause_type in _MAINLINE_TYPES


def get_chain_position(clause_type: str, prev_type: str | None) -> str:
    if clause_type in _MAINLINE_TYPES:
        return "initial" if prev_type not in _MAINLINE_TYPES else "continuation"
    if prev_type in _MAINLINE_TYPES:
        return "break"
    return "continuation"


def _extract_lemmas(words: list[Any], F: Any) -> list[str]:
    lemmas = []
    for w in words:
        if F.sp.v(w) in ("art", "prep", "conj"):
            continue
        lemma = None
        for attr in ("lex_utf8", "g_lex_utf8", "lex"):
            if hasattr(F, attr):
                lemma = getattr(F, attr).v(w)
                break
        if lemma:
            lemmas.append(lemma.rstrip("/=[]"))
    return lemmas


def _content_word_entry(w: Any, F: Any, sp: str, function: str | None) -> dict[str, Any] | None:
    lex_utf8 = None
    for attr in ("lex_utf8", "g_lex_utf8"):
        if hasattr(F, attr):
            lex_utf8 = getattr(F, attr).v(w)
            if lex_utf8:
                break
    lex_ascii = F.lex.v(w) if hasattr(F, "lex") else None
    cleaned_utf8 = (lex_utf8 or "").rstrip("/=[]") or None
    cleaned_ascii = (lex_ascii or "").rstrip("/=[]") or None
    if not cleaned_utf8 and not cleaned_ascii:
        return None
    entry: dict[str, Any] = {
        "lex_utf8": cleaned_utf8,
        "lex": cleaned_ascii,
        "sp": sp,
        "gloss": (F.gloss.v(w) if hasattr(F, "gloss") else "") or "",
        "pdp": F.pdp.v(w) if hasattr(F, "pdp") else None,
        "function": function,
    }
    if sp == "verb":
        entry["binyan"] = F.vs.v(w) if hasattr(F, "vs") else None
        entry["tense"] = F.vt.v(w) if hasattr(F, "vt") else None
    return entry


def extract_clause(
    clause_node: Any,
    verse: int,
    clause_id: int,
    prev_type: str | None,
    F: Any,
    L: Any,
    T: Any,
) -> dict[str, Any]:
    text = T.text(clause_node).strip()
    clause_type = F.typ.v(clause_node) or "Unknown"
    words = L.d(clause_node, otype="word")

    glosses = []
    for w in words:
        g = F.gloss.v(w) if hasattr(F, "gloss") and F.gloss.v(w) else ""
        if g:
            glosses.append(g)

    verb_lemma = verb_lemma_ascii = verb_stem = verb_tense = None
    for w in words:
        if F.sp.v(w) == "verb":
            for attr in ("lex_utf8", "g_lex_utf8", "lex"):
                if hasattr(F, attr):
                    verb_lemma = getattr(F, attr).v(w)
                    break
            verb_lemma_ascii = F.lex.v(w)
            verb_stem = F.vs.v(w)
            verb_tense = F.vt.v(w)
            break

    subjects: list[str] = []
    objects: list[str] = []
    names: list[str] = []
    name_glosses: dict[str, str] = {}
    name_types: dict[str, str] = {}
    content_words: list[dict[str, Any]] = []

    for phrase_node in L.d(clause_node, otype="phrase"):
        func = F.function.v(phrase_node)
        phrase_words = L.d(phrase_node, otype="word")
        lemmas = _extract_lemmas(phrase_words, F)
        clean = " ".join(lemmas) if lemmas else None

        if func == "Subj" and clean:
            subjects.append(clean)
        elif func == "Objc" and clean:
            objects.append(clean)

        for w in phrase_words:
            sp = F.sp.v(w)
            if sp == "nmpr":
                for attr in ("lex_utf8", "lex"):
                    if hasattr(F, attr):
                        name = getattr(F, attr).v(w)
                        if name:
                            clean_name = name.rstrip("/=[]")
                            names.append(clean_name)
                            if clean_name not in name_glosses:
                                gloss_val = F.gloss.v(w) if hasattr(F, "gloss") else ""
                                if gloss_val:
                                    name_glosses[clean_name] = gloss_val
                            if clean_name not in name_types and hasattr(F, "nametype"):
                                nt = F.nametype.v(w) or ""
                                if nt:
                                    name_types[clean_name] = nt
                        break
                continue

            if sp == "verb" or (sp in ("subs", "adjv") and func in _CONTENT_FUNCTIONS):
                pdp = F.pdp.v(w) if hasattr(F, "pdp") else None
                if pdp in _PRONOMINAL_PDP:
                    continue
                entry = _content_word_entry(w, F, sp, func)
                if entry:
                    content_words.append(entry)

    return {
        "clause_id": clause_id,
        "verse": verse,
        "text": text,
        "gloss": " ".join(glosses),
        "clause_type": clause_type,
        "is_mainline": is_mainline(clause_type),
        "chain_position": get_chain_position(clause_type, prev_type),
        "lemma": verb_lemma.rstrip("/=[]") if verb_lemma else None,
        "lemma_ascii": (verb_lemma_ascii.rstrip("/=[]") if verb_lemma_ascii else None),
        "binyan": verb_stem,
        "tense": verb_tense,
        "subjects": subjects,
        "objects": objects,
        "has_ki": any(F.lex.v(w) == "KJ/" for w in words),
        "names": list(set(names)),
        "name_glosses": name_glosses,
        "name_types": name_types,
        "content_words": content_words,
    }
