from __future__ import annotations

from typing import Any

from neo4j import AsyncSession

from pokegraph.sources.base import DataSource
from pokegraph.sources.models import Type

from ..cache import EnrichmentCache
from ..schema import RELATIONSHIP_BATCH_SIZE


def _damage_rows(type_model: Type) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mapping = (
        (type_model.damage_relations.double_damage_to, 2.0),
        (type_model.damage_relations.half_damage_to, 0.5),
        (type_model.damage_relations.no_damage_to, 0.0),
    )
    provenance = type_model.provenance
    for targets, factor in mapping:
        for target in targets:
            if target.id is None:
                continue
            rows.append(
                {
                    "from_id": type_model.id,
                    "from_name": type_model.name,
                    "to_id": target.id,
                    "to_name": target.name,
                    "factor": factor,
                    "source_url": provenance.source_url,
                    "source_version": provenance.source_version,
                    "retrieved_at": provenance.retrieved_at.isoformat(),
                }
            )
    return rows


async def enrich_types(
    session: AsyncSession,
    source: DataSource,
    cache: EnrichmentCache,
    type_ids: list[int],
) -> None:
    batch = RELATIONSHIP_BATCH_SIZE
    for type_id in type_ids:
        if type_id in cache.types:
            continue
        type_model = await source.get_type(type_id)
        rows = _damage_rows(type_model)
        provenance = type_model.provenance
        result = await session.run(
            """
            MERGE (t:Type {id: $type_id})
            SET t.name = $type_name,
                t.source_url = $source_url,
                t.source_version = $source_version,
                t.retrieved_at = $retrieved_at
            """,
            type_id=type_model.id,
            type_name=type_model.name,
            source_url=provenance.source_url,
            source_version=provenance.source_version,
            retrieved_at=provenance.retrieved_at.isoformat(),
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
                  SET r.factor = item.factor,
                      r.source_url = item.source_url,
                      r.source_version = item.source_version,
                      r.retrieved_at = item.retrieved_at
                }} IN TRANSACTIONS OF {batch} ROWS
                """,
                rows=rows,
            )
            await result.consume()
        cache.types.add(type_id)
