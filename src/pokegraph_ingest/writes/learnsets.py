from __future__ import annotations

from typing import Any

from neo4j import AsyncSession

from pokegraph.sources.models import Pokemon

from ..schema import RELATIONSHIP_BATCH_SIZE


def _learnset_entry_id(
    pokemon_id: int,
    move_id: int,
    version_group_id: int,
    learn_method_id: int,
    level: int,
    order: int | None,
) -> str:
    order_part = "" if order is None else str(order)
    return f"{pokemon_id}:{move_id}:{version_group_id}:{learn_method_id}:{level}:{order_part}"


def learnset_entry_rows(pokemon: Pokemon) -> list[dict[str, Any]]:
    """Flatten pokemon.moves / version_group_details into LearnsetEntry rows."""
    retrieved = pokemon.provenance.retrieved_at.isoformat()
    source_url = pokemon.provenance.source_url
    source_version = pokemon.provenance.source_version
    pokemon_id = int(pokemon.id)
    rows: list[dict[str, Any]] = []

    for entry in pokemon.moves:
        move_id = entry.move.id
        if move_id is None:
            continue
        for detail in entry.version_group_details:
            version_group_id = detail.version_group.id
            learn_method_id = detail.move_learn_method.id
            if version_group_id is None or learn_method_id is None:
                continue
            level = int(detail.level_learned_at or 0)
            order = detail.order
            rows.append(
                {
                    "id": _learnset_entry_id(
                        pokemon_id,
                        move_id,
                        version_group_id,
                        learn_method_id,
                        level,
                        order,
                    ),
                    "pokemon_id": pokemon_id,
                    "move_id": move_id,
                    "move_name": entry.move.name,
                    "version_group_id": version_group_id,
                    "version_group_name": detail.version_group.name,
                    "learn_method_id": learn_method_id,
                    "learn_method_name": detail.move_learn_method.name,
                    "level_learned_at": level,
                    "order": order,
                    "source_url": source_url,
                    "source_version": source_version,
                    "retrieved_at": retrieved,
                }
            )
    return rows


async def write_learnsets(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    batch = RELATIONSHIP_BATCH_SIZE
    result = await session.run(
        f"""
        UNWIND $rows AS item
        CALL (item) {{
          MERGE (p:Pokemon {{id: item.pokemon_id}})
          MERGE (m:Move {{id: item.move_id}})
          SET m.name = coalesce(m.name, item.move_name)
          MERGE (vg:VersionGroup {{id: item.version_group_id}})
          SET vg.name = coalesce(vg.name, item.version_group_name)
          MERGE (lm:MoveLearnMethod {{id: item.learn_method_id}})
          SET lm.name = item.learn_method_name
          MERGE (e:LearnsetEntry {{id: item.id}})
          SET e.pokemon_id = item.pokemon_id,
              e.move_id = item.move_id,
              e.version_group_id = item.version_group_id,
              e.learn_method_id = item.learn_method_id,
              e.level_learned_at = item.level_learned_at,
              e.order = item.order,
              e.source_url = item.source_url,
              e.source_version = item.source_version,
              e.retrieved_at = item.retrieved_at
          MERGE (p)-[:HAS_LEARNSET_ENTRY]->(e)
          MERGE (e)-[:TEACHES]->(m)
          MERGE (e)-[:IN_VERSION_GROUP]->(vg)
          MERGE (e)-[:BY_LEARN_METHOD]->(lm)
        }} IN TRANSACTIONS OF {batch} ROWS
        """,
        rows=rows,
    )
    await result.consume()
