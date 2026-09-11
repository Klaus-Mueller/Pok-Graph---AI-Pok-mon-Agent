from __future__ import annotations

from typing import Any

from neo4j import AsyncManagedTransaction, AsyncSession

from pokegraph.sources.models import Pokemon, PokemonSpecies

from ..schema import RELATIONSHIP_BATCH_SIZE


def relationship_rows(pokemon: Pokemon) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return types, abilities, and unique moves for simplified CAN_LEARN edges."""
    types = []
    for entry in pokemon.types:
        if entry.type.id is not None:
            types.append({"id": entry.type.id, "name": entry.type.name, "slot": entry.slot})

    abilities = []
    for entry in pokemon.abilities:
        if entry.ability.id is not None:
            abilities.append(
                {
                    "id": entry.ability.id,
                    "name": entry.ability.name,
                    "slot": entry.slot,
                    "is_hidden": entry.is_hidden,
                }
            )

    seen_moves: dict[int, str] = {}
    for entry in pokemon.moves:
        move_id = entry.move.id
        if move_id is None or move_id in seen_moves:
            continue
        seen_moves[move_id] = entry.move.name
    moves = [{"id": move_id, "name": name} for move_id, name in seen_moves.items()]
    return types, abilities, moves


def _provenance_params(model: Pokemon | PokemonSpecies) -> dict[str, Any]:
    return {
        "source_url": model.provenance.source_url,
        "source_version": model.provenance.source_version,
        "retrieved_at": model.provenance.retrieved_at.isoformat(),
        "adapter_version": model.provenance.adapter_version,
    }


async def _write_pokemon_core(tx: AsyncManagedTransaction, pokemon: Pokemon, species: PokemonSpecies) -> None:
    species_prov = _provenance_params(species)
    pokemon_prov = _provenance_params(pokemon)
    result = await tx.run(
        """
        MERGE (s:PokemonSpecies {id: $species_id})
        SET s.name = $species_name,
            s.is_legendary = $is_legendary,
            s.is_mythical = $is_mythical,
            s.generation = $generation,
            s.source_url = $species_source_url,
            s.source_version = $species_source_version,
            s.retrieved_at = $species_retrieved_at,
            s.adapter_version = $species_adapter_version
        MERGE (p:Pokemon {id: $pokemon_id})
        SET p.name = $pokemon_name,
            p.base_experience = $base_experience,
            p.height = $height,
            p.weight = $weight,
            p.is_default = $is_default,
            p.source_url = $pokemon_source_url,
            p.source_version = $pokemon_source_version,
            p.retrieved_at = $pokemon_retrieved_at,
            p.adapter_version = $pokemon_adapter_version
        MERGE (p)-[:SPECIES]->(s)
        """,
        species_id=species.id,
        species_name=species.name,
        is_legendary=species.is_legendary,
        is_mythical=species.is_mythical,
        generation=species.generation,
        species_source_url=species_prov["source_url"],
        species_source_version=species_prov["source_version"],
        species_retrieved_at=species_prov["retrieved_at"],
        species_adapter_version=species_prov["adapter_version"],
        pokemon_id=pokemon.id,
        pokemon_name=pokemon.name,
        base_experience=pokemon.base_experience,
        height=pokemon.height,
        weight=pokemon.weight,
        is_default=pokemon.is_default,
        pokemon_source_url=pokemon_prov["source_url"],
        pokemon_source_version=pokemon_prov["source_version"],
        pokemon_retrieved_at=pokemon_prov["retrieved_at"],
        pokemon_adapter_version=pokemon_prov["adapter_version"],
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


async def write_pokemon(session: AsyncSession, pokemon: Pokemon, species: PokemonSpecies) -> tuple[list[int], list[int]]:
    """Write core Pokemon graph. Returns (type_ids, move_ids) for enrichment."""
    types, abilities, moves = relationship_rows(pokemon)
    await session.execute_write(_write_pokemon_core, pokemon, species)
    await _write_relationship_batches(session, pokemon.id, types, abilities, moves)
    return [item["id"] for item in types], [item["id"] for item in moves]
