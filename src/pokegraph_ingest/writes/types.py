from __future__ import annotations

from typing import Any

from neo4j import AsyncSession
from pokelance import PokeLance

from ..cache import EnrichmentCache
from ..resources import resource_id, resource_name
from ..schema import RELATIONSHIP_BATCH_SIZE


def _damage_rows(type_id: int, type_name: str, relations: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mapping = (
        (getattr(relations, "double_damage_to", []), 2.0),
        (getattr(relations, "half_damage_to", []), 0.5),
        (getattr(relations, "no_damage_to", []), 0.0),
    )
    for targets, factor in mapping:
        for target in targets:
            target_id = resource_id(target)
            if target_id is None:
                continue
            rows.append(
                {
                    "from_id": type_id,
                    "from_name": type_name,
                    "to_id": target_id,
                    "to_name": resource_name(target),
                    "factor": factor,
                }
            )
    return rows


async def enrich_types(
    session: AsyncSession,
    pokeapi: PokeLance,
    cache: EnrichmentCache,
    type_ids: list[int],
) -> None:
    batch = RELATIONSHIP_BATCH_SIZE
    for type_id in type_ids:
        if type_id in cache.types:
            continue
        type_model = await pokeapi.pokemon.fetch_type(type_id)
        rows = _damage_rows(type_model.id, type_model.name, type_model.damage_relations)
        result = await session.run(
            """
            MERGE (t:Type {id: $type_id})
            SET t.name = $type_name
            """,
            type_id=type_model.id,
            type_name=type_model.name,
        )
        await result.consume()
        if rows:
            result = await session.run(
                f"""
                UNWIND $rows AS item
                CALL (item) {{
                  MERGE (from:Type {{id: item.from_id}})
                  SET from.name = item.from_name
                  MERGE (to:Type {{id: item.to_id}})
                  SET to.name = coalesce(to.name, item.to_name)
                  MERGE (from)-[r:DAMAGE_TO]->(to)
                  SET r.factor = item.factor
                }} IN TRANSACTIONS OF {batch} ROWS
                """,
                rows=rows,
            )
            await result.consume()
        cache.types.add(type_id)
