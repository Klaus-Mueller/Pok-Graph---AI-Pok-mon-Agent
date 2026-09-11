from __future__ import annotations

from typing import Any

from neo4j import AsyncSession

from pokegraph.sources.base import DataSource
from pokegraph.sources.models import Move

from ..cache import EnrichmentCache

_MOVE_SET_KEYS = (
    "id",
    "name",
    "power",
    "accuracy",
    "pp",
    "priority",
    "type",
    "damage_class",
    "effect_chance",
    "effect",
    "short_effect",
    "target",
    "ailment",
    "ailment_chance",
    "flinch_chance",
    "stat_chance",
    "drain",
    "healing",
    "min_hits",
    "max_hits",
    "min_turns",
    "max_turns",
    "contest_type",
    "contest_effect_id",
    "source_url",
    "source_version",
    "retrieved_at",
)

_MOVE_SET_CYPHER = """
MERGE (m:Move {id: $id})
SET m.name = $name,
    m.power = $power,
    m.accuracy = $accuracy,
    m.pp = $pp,
    m.priority = $priority,
    m.type = $type,
    m.damage_class = $damage_class,
    m.effect_chance = $effect_chance,
    m.effect = $effect,
    m.short_effect = $short_effect,
    m.target = $target,
    m.ailment = $ailment,
    m.ailment_chance = $ailment_chance,
    m.flinch_chance = $flinch_chance,
    m.stat_chance = $stat_chance,
    m.drain = $drain,
    m.healing = $healing,
    m.min_hits = $min_hits,
    m.max_hits = $max_hits,
    m.min_turns = $min_turns,
    m.max_turns = $max_turns,
    m.contest_type = $contest_type,
    m.contest_effect_id = $contest_effect_id,
    m.source_url = $source_url,
    m.source_version = $source_version,
    m.retrieved_at = $retrieved_at
"""


def move_props(move: Move) -> dict[str, Any]:
    """Extract Move node properties from a normalized move model."""
    return {
        "id": int(move.id),
        "name": move.name,
        "power": move.power,
        "accuracy": move.accuracy,
        "pp": move.pp,
        "priority": move.priority,
        "type": move.type_name,
        "type_id": move.type_id,
        "damage_class": move.damage_class,
        "effect_chance": move.effect_chance,
        "effect": move.effect,
        "short_effect": move.short_effect,
        "target": move.target,
        "ailment": move.ailment,
        "ailment_chance": move.ailment_chance,
        "flinch_chance": move.flinch_chance,
        "stat_chance": move.stat_chance,
        "drain": move.drain,
        "healing": move.healing,
        "min_hits": move.min_hits,
        "max_hits": move.max_hits,
        "min_turns": move.min_turns,
        "max_turns": move.max_turns,
        "contest_type": move.contest_type,
        "contest_effect_id": move.contest_effect_id,
        "source_url": move.provenance.source_url,
        "source_version": move.provenance.source_version,
        "retrieved_at": move.provenance.retrieved_at.isoformat(),
    }


def _set_params(props: dict[str, Any]) -> dict[str, Any]:
    return {key: props[key] for key in _MOVE_SET_KEYS}


async def enrich_moves(
    session: AsyncSession,
    source: DataSource,
    cache: EnrichmentCache,
    move_ids: list[int],
) -> None:
    for move_id in move_ids:
        if move_id in cache.moves:
            continue
        move_model = await source.get_move(move_id)
        props = move_props(move_model)
        params = _set_params(props)
        type_id = props["type_id"]
        if type_id is None:
            result = await session.run(_MOVE_SET_CYPHER, **params)
            await result.consume()
        else:
            result = await session.run(
                _MOVE_SET_CYPHER
                + """
                WITH m
                MERGE (t:Type {id: $type_id})
                SET t.name = coalesce(t.name, $type)
                MERGE (m)-[:HAS_TYPE]->(t)
                """,
                **params,
                type_id=type_id,
            )
            await result.consume()
        cache.moves.add(move_id)
