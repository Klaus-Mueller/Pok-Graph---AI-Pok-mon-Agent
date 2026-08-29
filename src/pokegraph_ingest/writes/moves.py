from __future__ import annotations

from typing import Any

from neo4j import AsyncSession
from pokelance import PokeLance

from ..cache import EnrichmentCache
from ..resources import resource_id, resource_name


def move_props(move: Any) -> dict[str, Any]:
    """Extract Move node properties from a PokéAPI move resource."""
    move_type = getattr(move, "type", None)
    damage_class = getattr(move, "damage_class", None)
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
    }


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
        type_id = props["type_id"]
        if type_id is None:
            result = await session.run(
                """
                MERGE (m:Move {id: $id})
                SET m.name = $name,
                    m.power = $power,
                    m.accuracy = $accuracy,
                    m.pp = $pp,
                    m.priority = $priority,
                    m.type = $type,
                    m.damage_class = $damage_class
                """,
                id=props["id"],
                name=props["name"],
                power=props["power"],
                accuracy=props["accuracy"],
                pp=props["pp"],
                priority=props["priority"],
                type=props["type"],
                damage_class=props["damage_class"],
            )
            await result.consume()
        else:
            result = await session.run(
                """
                MERGE (m:Move {id: $id})
                SET m.name = $name,
                    m.power = $power,
                    m.accuracy = $accuracy,
                    m.pp = $pp,
                    m.priority = $priority,
                    m.type = $type,
                    m.damage_class = $damage_class
                WITH m
                MERGE (t:Type {id: $type_id})
                SET t.name = coalesce(t.name, $type)
                MERGE (m)-[:HAS_TYPE]->(t)
                """,
                id=props["id"],
                name=props["name"],
                power=props["power"],
                accuracy=props["accuracy"],
                pp=props["pp"],
                priority=props["priority"],
                type=props["type"],
                damage_class=props["damage_class"],
                type_id=type_id,
            )
            await result.consume()
        cache.moves.add(move_id)
