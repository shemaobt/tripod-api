import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import BibleBook

BIBLE_BOOKS_DATA = [
    ("Genesis", "Gen", "OT", 1, 50),
    ("Exodus", "Exod", "OT", 2, 40),
    ("Leviticus", "Lev", "OT", 3, 27),
    ("Numbers", "Num", "OT", 4, 36),
    ("Deuteronomy", "Deut", "OT", 5, 34),
    ("Joshua", "Josh", "OT", 6, 24),
    ("Judges", "Judg", "OT", 7, 21),
    ("Ruth", "Ruth", "OT", 8, 4),
    ("1 Samuel", "1Sam", "OT", 9, 31),
    ("2 Samuel", "2Sam", "OT", 10, 24),
    ("1 Kings", "1Kgs", "OT", 11, 22),
    ("2 Kings", "2Kgs", "OT", 12, 25),
    ("1 Chronicles", "1Chr", "OT", 13, 29),
    ("2 Chronicles", "2Chr", "OT", 14, 36),
    ("Ezra", "Ezra", "OT", 15, 10),
    ("Nehemiah", "Neh", "OT", 16, 13),
    ("Esther", "Esth", "OT", 17, 10),
    ("Job", "Job", "OT", 18, 42),
    ("Psalms", "Ps", "OT", 19, 150),
    ("Proverbs", "Prov", "OT", 20, 31),
    ("Ecclesiastes", "Eccl", "OT", 21, 12),
    ("Song of Solomon", "Song", "OT", 22, 8),
    ("Isaiah", "Isa", "OT", 23, 66),
    ("Jeremiah", "Jer", "OT", 24, 52),
    ("Lamentations", "Lam", "OT", 25, 5),
    ("Ezekiel", "Ezek", "OT", 26, 48),
    ("Daniel", "Dan", "OT", 27, 12),
    ("Hosea", "Hos", "OT", 28, 14),
    ("Joel", "Joel", "OT", 29, 3),
    ("Amos", "Amos", "OT", 30, 9),
    ("Obadiah", "Obad", "OT", 31, 1),
    ("Jonah", "Jonah", "OT", 32, 4),
    ("Micah", "Mic", "OT", 33, 7),
    ("Nahum", "Nah", "OT", 34, 3),
    ("Habakkuk", "Hab", "OT", 35, 3),
    ("Zephaniah", "Zeph", "OT", 36, 3),
    ("Haggai", "Hag", "OT", 37, 2),
    ("Zechariah", "Zech", "OT", 38, 14),
    ("Malachi", "Mal", "OT", 39, 4),
    ("Matthew", "Matt", "NT", 40, 28),
    ("Mark", "Mark", "NT", 41, 16),
    ("Luke", "Luke", "NT", 42, 24),
    ("John", "John", "NT", 43, 21),
    ("Acts", "Acts", "NT", 44, 28),
    ("Romans", "Rom", "NT", 45, 16),
    ("1 Corinthians", "1Cor", "NT", 46, 16),
    ("2 Corinthians", "2Cor", "NT", 47, 13),
    ("Galatians", "Gal", "NT", 48, 6),
    ("Ephesians", "Eph", "NT", 49, 6),
    ("Philippians", "Phil", "NT", 50, 4),
    ("Colossians", "Col", "NT", 51, 4),
    ("1 Thessalonians", "1Thess", "NT", 52, 5),
    ("2 Thessalonians", "2Thess", "NT", 53, 3),
    ("1 Timothy", "1Tim", "NT", 54, 6),
    ("2 Timothy", "2Tim", "NT", 55, 4),
    ("Titus", "Titus", "NT", 56, 3),
    ("Philemon", "Phlm", "NT", 57, 1),
    ("Hebrews", "Heb", "NT", 58, 13),
    ("James", "Jas", "NT", 59, 5),
    ("1 Peter", "1Pet", "NT", 60, 5),
    ("2 Peter", "2Pet", "NT", 61, 3),
    ("1 John", "1John", "NT", 62, 5),
    ("2 John", "2John", "NT", 63, 1),
    ("3 John", "3John", "NT", 64, 1),
    ("Jude", "Jude", "NT", 65, 1),
    ("Revelation", "Rev", "NT", 66, 22),
]


async def seed_books(db: AsyncSession) -> int:
    existing = await db.execute(select(BibleBook.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return 0

    count = 0
    for name, abbr, testament, order, chapters in BIBLE_BOOKS_DATA:
        book = BibleBook(
            id=str(uuid.uuid4()),
            name=name,
            abbreviation=abbr,
            testament=testament,
            order=order,
            chapter_count=chapters,
            is_enabled=(testament == "OT"),
        )
        db.add(book)
        count += 1

    await db.commit()
    return count
