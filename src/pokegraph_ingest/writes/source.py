from __future__ import annotations

from neo4j import AsyncSession

from ..cache import EnrichmentCache

SOURCE_ID = "pokeapi"
SOURCE_NAME = "PokéAPI"


async def ensure_source(session: AsyncSession, cache: EnrichmentCache) -> None:
    if cache.source_ensured:
        return
    result = await session.run(
        """
        MERGE (src:Source {id: $source_id})
        SET src.name = $source_name
        """,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
    )
    await result.consume()
    cache.source_ensured = True


async def link_has_source(session: AsyncSession, pokemon_id: int, species_id: int) -> None:
    result = await session.run(
        """
        MATCH (src:Source {id: $source_id})
        MERGE (p:Pokemon {id: $pokemon_id})
        MERGE (s:PokemonSpecies {id: $species_id})
        MERGE (p)-[:HAS_SOURCE]->(src)
        MERGE (s)-[:HAS_SOURCE]->(src)
        """,
        source_id=SOURCE_ID,
        pokemon_id=pokemon_id,
        species_id=species_id,
    )
    await result.consume()
