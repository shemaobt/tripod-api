from __future__ import annotations

import re

BOOK_NAMES: dict[str, str] = {
    "genesis": "Genesis",
    "gen": "Genesis",
    "exodus": "Exodus",
    "exod": "Exodus",
    "ex": "Exodus",
    "leviticus": "Leviticus",
    "lev": "Leviticus",
    "numbers": "Numbers",
    "num": "Numbers",
    "deuteronomy": "Deuteronomy",
    "deut": "Deuteronomy",
    "joshua": "Joshua",
    "josh": "Joshua",
    "judges": "Judges",
    "judg": "Judges",
    "ruth": "Ruth",
    "1 samuel": "1_Samuel",
    "1samuel": "1_Samuel",
    "1sam": "1_Samuel",
    "2 samuel": "2_Samuel",
    "2samuel": "2_Samuel",
    "2sam": "2_Samuel",
    "1 kings": "1_Kings",
    "1kings": "1_Kings",
    "1kgs": "1_Kings",
    "2 kings": "2_Kings",
    "2kings": "2_Kings",
    "2kgs": "2_Kings",
    "isaiah": "Isaiah",
    "isa": "Isaiah",
    "jeremiah": "Jeremiah",
    "jer": "Jeremiah",
    "ezekiel": "Ezekiel",
    "ezek": "Ezekiel",
    "hosea": "Hosea",
    "hos": "Hosea",
    "joel": "Joel",
    "amos": "Amos",
    "obadiah": "Obadiah",
    "obad": "Obadiah",
    "jonah": "Jonah",
    "micah": "Micah",
    "mic": "Micah",
    "nahum": "Nahum",
    "nah": "Nahum",
    "habakkuk": "Habakkuk",
    "hab": "Habakkuk",
    "zephaniah": "Zephaniah",
    "zeph": "Zephaniah",
    "haggai": "Haggai",
    "hag": "Haggai",
    "zechariah": "Zechariah",
    "zech": "Zechariah",
    "malachi": "Malachi",
    "mal": "Malachi",
    "psalms": "Psalms",
    "psalm": "Psalms",
    "ps": "Psalms",
    "job": "Job",
    "proverbs": "Proverbs",
    "prov": "Proverbs",
    "ecclesiastes": "Ecclesiastes",
    "eccl": "Ecclesiastes",
    "song of songs": "Song_of_songs",
    "song": "Song_of_songs",
    "lamentations": "Lamentations",
    "lam": "Lamentations",
    "esther": "Esther",
    "esth": "Esther",
    "daniel": "Daniel",
    "dan": "Daniel",
    "ezra": "Ezra",
    "nehemiah": "Nehemiah",
    "neh": "Nehemiah",
    "1 chronicles": "1_Chronicles",
    "1chronicles": "1_Chronicles",
    "2 chronicles": "2_Chronicles",
    "2chronicles": "2_Chronicles",
}

_SIMILARITY_THRESHOLD = 0.7


def _lcs_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[len1][len2] / max(len1, len2)


def normalize_book_name(book: str) -> str:
    key = book.lower().strip()
    if key in BOOK_NAMES:
        return BOOK_NAMES[key]

    best_match = None
    best_score = 0.0
    for candidate, bhsa_name in BOOK_NAMES.items():
        score = _lcs_similarity(key, candidate)
        if score > best_score and score >= _SIMILARITY_THRESHOLD:
            best_score = score
            best_match = bhsa_name
    return best_match or book


def parse_reference(ref: str) -> tuple[str, int, int, int]:
    ref = ref.strip().replace("\u2013", "-").replace("\u2014", "-")

    match = re.match(r"^(.+?)\s+(\d+):(\d+)[a-zA-Z]?-(\d+)[a-zA-Z]?$", ref)
    if match:
        book = normalize_book_name(match.group(1))
        return book, int(match.group(2)), int(match.group(3)), int(match.group(4))

    match = re.match(r"^(.+?)\s+(\d+):(\d+)[a-zA-Z]?$", ref)
    if match:
        book = normalize_book_name(match.group(1))
        chapter = int(match.group(2))
        verse = int(match.group(3))
        return book, chapter, verse, verse

    raise ValueError(f"Could not parse reference: {ref}")
