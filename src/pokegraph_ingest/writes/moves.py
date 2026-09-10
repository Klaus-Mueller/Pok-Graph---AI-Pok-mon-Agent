from __future__ import annotations

from typing import Any

from neo4j import AsyncSession
from pokelance import PokeLance

from ..cache import EnrichmentCache
from ..resources import resource_id, resource_name


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
    m.contest_effect_id = $contest_effect_id
"""


def _english_effect(move: Any) -> tuple[str, str]:
    for entry in getattr(move, "effect_entries", None) or []:
        language = getattr(entry, "language", None)
        if resource_name(language) == "en":
            return (
                getattr(entry, "effect", None) or "",
                getattr(entry, "short_effect", None) or "",
            )
    return "", ""


def move_props(move: Any) -> dict[str, Any]:
    """Extract Move node properties from a PokéAPI move resource."""
    move_type = getattr(move, "type", None)
    damage_class = getattr(move, "damage_class", None)
    target = getattr(move, "target", None)
    contest_type = getattr(move, "contest_type", None)
    contest_effect = getattr(move, "contest_effect", None)
    meta = getattr(move, "meta", None)
    effect, short_effect = _english_effect(move)

    ailment = getattr(meta, "ailment", None) if meta is not None else None
    return {
        "id": int(move.id),
        "name": getattr(move, "name", "") or "",
        "power": getattr(move, "power", None),
        "accuracy": getattr(move, "accuracy", None),
        "pp": getattr(move, "pp", None),
        "priority": getattr(move, "priority", None),
        "type": resource_name(move_type) if move_type is not None else "",
        "type_id": resource_id(move_type) if move_type is not None else None,
        "damage_class": resource_name(damage_class) if damage_class is not None else "",
        "effect_chance": getattr(move, "effect_chance", None),
        "effect": effect,
        "short_effect": short_effect,
        "target": resource_name(target) if target is not None else "",
        "ailment": resource_name(ailment) if ailment is not None else "",
        "ailment_chance": getattr(meta, "ailment_chance", None) if meta is not None else None,
        "flinch_chance": getattr(meta, "flinch_chance", None) if meta is not None else None,
        "stat_chance": getattr(meta, "stat_chance", None) if meta is not None else None,
        "drain": getattr(meta, "drain", None) if meta is not None else None,
        "healing": getattr(meta, "healing", None) if meta is not None else None,
        "min_hits": getattr(meta, "min_hits", None) if meta is not None else None,
        "max_hits": getattr(meta, "max_hits", None) if meta is not None else None,
        "min_turns": getattr(meta, "min_turns", None) if meta is not None else None,
        "max_turns": getattr(meta, "max_turns", None) if meta is not None else None,
        "contest_type": resource_name(contest_type) if contest_type is not None else "",
        "contest_effect_id": resource_id(contest_effect) if contest_effect is not None else None,
    }


def _set_params(props: dict[str, Any]) -> dict[str, Any]:
    return {key: props[key] for key in _MOVE_SET_KEYS}


async def enrich_moves(
    session: AsyncSession,
    pokeapi: PokeLance,
    cache: EnrichmentCache,
    move_ids: list[int],
) -> None:
    for move_id in move_ids:
        if move_id in cache.moves:
            continue
        move_model = await pokeapi.move.fetch_move(move_id)
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
