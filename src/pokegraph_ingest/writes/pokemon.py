from __future__ import annotations

from typing import Any

from neo4j import AsyncManagedTransaction, AsyncSession

from ..resources import resource_id, resource_name
from ..schema import RELATIONSHIP_BATCH_SIZE


def relationship_rows(pokemon: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return types, abilities, and unique moves for simplified CAN_LEARN edges."""
    types = []
    for entry in getattr(pokemon, "types", []):
        resource = entry.type
        type_id = resource_id(resource)
        if type_id is not None:
            types.append({"id": type_id, "name": resource_name(resource), "slot": entry.slot})

    abilities = []
    for entry in getattr(pokemon, "abilities", []):
        resource = entry.ability
        ability_id = resource_id(resource)
        if ability_id is not None:
            abilities.append(
                {
                    "id": ability_id,
                    "name": resource_name(resource),
                    "slot": entry.slot,
                    "is_hidden": entry.is_hidden,
                }
            )

    # Simplified CAN_LEARN: one edge per move (details live on LearnsetEntry).
    seen_moves: dict[int, str] = {}
    for entry in getattr(pokemon, "moves", []) or []:
        resource = entry.move
        move_id = resource_id(resource)
        if move_id is None or move_id in seen_moves:
            continue
        seen_moves[move_id] = resource_name(resource)
    moves = [{"id": move_id, "name": name} for move_id, name in seen_moves.items()]
    return types, abilities, moves


async def _write_pokemon_core(tx: AsyncManagedTransaction, pokemon: Any, species: Any) -> None:
    species_id = getattr(species, "id", 0)
    result = await tx.run(
        """
        MERGE (s:PokemonSpecies {id: $species_id})
        SET s.name = $species_name,
            s.is_legendary = $is_legendary,
            s.is_mythical = $is_mythical,
            s.generation = $generation
        MERGE (p:Pokemon {id: $pokemon_id})
        SET p.name = $pokemon_name,
            p.base_experience = $base_experience,
            p.height = $height,
            p.weight = $weight,
            p.is_default = $is_default
        MERGE (p)-[:SPECIES]->(s)
        """,
        species_id=species_id,
        species_name=species.name,
        is_legendary=species.is_legendary,
        is_mythical=species.is_mythical,
        generation=resource_name(species.generation),
        pokemon_id=pokemon.id,
        pokemon_name=pokemon.name,
        base_experience=pokemon.base_experience,
        height=pokemon.height,
        weight=pokemon.weight,
        is_default=pokemon.is_default,
    )
    await result.consume()


async def _write_relationship_batches(
    session: AsyncSession,
    pokemon_id: int,
    types: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
    moves: list[dict[str, Any]],
) -> None:
    batch = RELATIONSHIP_BATCH_SIZE
    if types:
        result = await session.run(
            f"""
            UNWIND $types AS item
            CALL (item) {{
              MATCH (p:Pokemon {{id: $pokemon_id}})
              MERGE (t:Type {{id: item.id}}) SET t.name = item.name
              MERGE (p)-[r:HAS_TYPE]->(t) SET r.slot = item.slot
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            pokemon_id=pokemon_id,
            types=types,
        )
        await result.consume()
    if abilities:
        result = await session.run(
            f"""
            UNWIND $abilities AS item
            CALL (item) {{
              MATCH (p:Pokemon {{id: $pokemon_id}})
              MERGE (a:Ability {{id: item.id}}) SET a.name = item.name
              MERGE (p)-[r:HAS_ABILITY]->(a)
              SET r.slot = item.slot, r.is_hidden = item.is_hidden
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            pokemon_id=pokemon_id,
            abilities=abilities,
        )
        await result.consume()
    if moves:
        result = await session.run(
            f"""
            UNWIND $moves AS item
            CALL (item) {{
              MATCH (p:Pokemon {{id: $pokemon_id}})
              MERGE (m:Move {{id: item.id}}) SET m.name = item.name
              MERGE (p)-[:CAN_LEARN]->(m)
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            pokemon_id=pokemon_id,
            moves=moves,
        )
        await result.consume()


async def write_pokemon(session: AsyncSession, pokemon: Any, species: Any) -> tuple[list[int], list[int]]:
    """Write core Pokemon graph. Returns (type_ids, move_ids) for enrichment."""
    types, abilities, moves = relationship_rows(pokemon)
    await session.execute_write(_write_pokemon_core, pokemon, species)
    await _write_relationship_batches(session, pokemon.id, types, abilities, moves)
    return [item["id"] for item in types], [item["id"] for item in moves]
