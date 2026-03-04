from app.core.exceptions import AuthorizationError
from app.db.models.meaning_map import BibleBook


def ensure_ot(book: BibleBook) -> None:
    if not book.is_enabled:
        raise AuthorizationError(
            f"Book '{book.name}' is not enabled for meaning map work (New Testament)"
        )
