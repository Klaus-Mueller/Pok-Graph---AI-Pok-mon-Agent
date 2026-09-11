from __future__ import annotations

from datetime import date, datetime
from typing import Any


def jsonable(value: Any) -> Any:
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def records_to_dicts(records: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        data = record.data() if hasattr(record, "data") else dict(record)
        rows.append({key: jsonable(value) for key, value in data.items()})
    return rows
