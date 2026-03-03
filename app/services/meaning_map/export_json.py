import json

from app.db.models.meaning_map import MeaningMap


def export_json(mm: MeaningMap) -> str:
    return json.dumps(mm.data, indent=2, ensure_ascii=False)
