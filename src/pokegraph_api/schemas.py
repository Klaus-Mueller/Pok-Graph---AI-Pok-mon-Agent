from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pokegraph.graph.models import QueryPage


class GameContextModel(BaseModel):
    version_id: int | None = None
    version_name: str | None = None
    version_group_id: int | None = None
    version_group_name: str | None = None


class QueryPageModel(BaseModel):
    query_id: str
    rows: list[dict[str, Any]]
    skip: int
    limit: int
    context: GameContextModel
    limitations: list[str] = Field(default_factory=list)
    data_complete: bool | None = None


class ErrorModel(BaseModel):
    error: str
    category: str
    detail: str
    entity: str | None = None
    entity_id: int | None = None


class HealthModel(BaseModel):
    status: str
    database_ready: bool
    detail: str | None = None


class AgentRequest(BaseModel):
    question: str
    game_version_id: int | None = None
    battle_key: str | None = None
    player_starter: str | None = None
    accessible_location_names: list[str] | None = None


class AgentResponse(BaseModel):
    status: str
    answer: str
    evidence: list[dict[str, Any]]
    assumptions: list[str]
    missing_information: list[str]
    tool_calls: list[str]


def page_to_model(page: QueryPage) -> QueryPageModel:
    return QueryPageModel(
        query_id=page.query_id,
        rows=page.rows,
        skip=page.skip,
        limit=page.limit,
        context=GameContextModel(
            version_id=page.context.version_id,
            version_name=page.context.version_name,
            version_group_id=page.context.version_group_id,
            version_group_name=page.context.version_group_name,
        ),
        limitations=list(page.limitations),
        data_complete=page.data_complete,
    )
