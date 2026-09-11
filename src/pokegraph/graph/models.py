from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GameContext:
    version_id: int | None = None
    version_name: str | None = None
    version_group_id: int | None = None
    version_group_name: str | None = None


@dataclass(frozen=True)
class QueryPage:
    query_id: str
    rows: list[dict[str, Any]]
    skip: int
    limit: int
    context: GameContext = field(default_factory=GameContext)
    limitations: tuple[str, ...] = ()
    data_complete: bool | None = None
