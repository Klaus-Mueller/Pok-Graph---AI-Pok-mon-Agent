from __future__ import annotations

from neo4j import AsyncSession

from pokegraph.sources.models import Pokemon, PokemonSpecies

from ..cache import EnrichmentCache

SOURCE_ID = "pokeapi"
SOURCE_NAME = "PokéAPI"
SOURCE_URL = "https://pokeapi.co/api/v2/"
SOURCE_VERSION = "unavailable"


async def ensure_source(session: AsyncSession, cache: EnrichmentCache) -> None:
    if cache.source_ensured:
        return
    result = await session.run(
        """
        MERGE (src:Source {id: $source_id})
        SET src.name = $source_name,
            src.source_url = $source_url,
            src.source_version = $source_version
        """,
        source_id=SOURCE_ID,
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        source_version=SOURCE_VERSION,
    )
    await result.consume()
    cache.source_ensured = True


async def link_has_source(
    session: AsyncSession,
    pokemon: Pokemon,
    species: PokemonSpecies,
) -> None:
    result = await session.run(
        """
        MATCH (src:Source {id: $source_id})
        MERGE (p:Pokemon {id: $pokemon_id})
        MERGE (s:PokemonSpecies {id: $species_id})
        MERGE (p)-[ps:HAS_SOURCE]->(src)
        SET ps.source_url = $pokemon_source_url,
            ps.source_version = $pokemon_source_version,
            ps.retrieved_at = $pokemon_retrieved_at
        MERGE (s)-[ss:HAS_SOURCE]->(src)
        SET ss.source_url = $species_source_url,
            ss.source_version = $species_source_version,
            ss.retrieved_at = $species_retrieved_at
        """,
        source_id=SOURCE_ID,
        pokemon_id=pokemon.id,
        species_id=species.id,
        pokemon_source_url=pokemon.provenance.source_url,
        pokemon_source_version=pokemon.provenance.source_version,
        pokemon_retrieved_at=pokemon.provenance.retrieved_at.isoformat(),
        species_source_url=species.provenance.source_url,
        species_source_version=species.provenance.source_version,
        species_retrieved_at=species.provenance.retrieved_at.isoformat(),
    )
    await result.consume()
