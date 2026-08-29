from __future__ import annotations

from typing import Any

from neo4j import AsyncSession
from pokelance import PokeLance

from ..cache import EnrichmentCache
from ..resources import resource_id, resource_name
from ..schema import RELATIONSHIP_BATCH_SIZE


def _species_id_from_link(link: Any) -> int | None:
    return resource_id(getattr(link, "species", None))


def _evolution_edge_props(detail: Any, from_id: int, to_id: int) -> dict[str, Any]:
    trigger = resource_name(detail.trigger) or ""
    version_group = resource_name(detail.version_group) or ""
    item_name = resource_name(detail.item) if detail.item else ""
    region = resource_name(detail.region) if detail.region else ""
    min_level = detail.min_level if detail.min_level is not None else ""
    edge_id = f"{from_id}:{to_id}:{trigger}:{version_group}:{item_name}:{min_level}:{region}"
    return {
        "edge_id": edge_id,
        "trigger": trigger or None,
        "min_level": detail.min_level,
        "min_happiness": detail.min_happiness,
        "min_beauty": detail.min_beauty,
        "min_affection": detail.min_affection,
        "time_of_day": detail.time_of_day or None,
        "needs_overworld_rain": bool(detail.needs_overworld_rain),
        "turn_upside_down": bool(detail.turn_upside_down),
        "relative_physical_stats": detail.relative_physical_stats,
        "known_move": resource_name(detail.known_move) if detail.known_move else None,
        "known_move_type": resource_name(detail.known_move_type) if detail.known_move_type else None,
        "held_item": resource_name(detail.held_item) if detail.held_item else None,
        "location": resource_name(detail.location) if detail.location else None,
        "party_species": resource_name(detail.party_species) if detail.party_species else None,
        "trade_species": resource_name(detail.trade_species) if detail.trade_species else None,
        "gender": str(detail.gender) if detail.gender is not None else None,
        "version_group": version_group or None,
        "region": region or None,
        "is_default": bool(detail.is_default),
    }


def _walk_chain(chain_id: int, link: Any, from_species_id: int | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (species_rows, evolve_rows, item_rows)."""
    species_rows: list[dict[str, Any]] = []
    evolve_rows: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []

    species_id = _species_id_from_link(link)
    if species_id is None:
        return species_rows, evolve_rows, item_rows

    species_rows.append(
        {
            "id": species_id,
            "name": resource_name(link.species),
            "chain_id": chain_id,
            "is_baby": bool(getattr(link, "is_baby", False)),
        }
    )

    if from_species_id is not None:
        for detail in getattr(link, "evolution_details", []) or []:
            props = _evolution_edge_props(detail, from_species_id, species_id)
            evolve_rows.append(
                {
                    "from_id": from_species_id,
                    "to_id": species_id,
                    **props,
                }
            )
            item = detail.item
            if item is not None:
                item_id = resource_id(item)
                if item_id is not None:
                    item_rows.append(
                        {
                            "species_id": species_id,
                            "item_id": item_id,
                            "item_name": resource_name(item),
                        }
                    )

    for child in getattr(link, "evolves_to", []) or []:
        child_species, child_evolve, child_items = _walk_chain(chain_id, child, from_species_id=species_id)
        species_rows.extend(child_species)
        evolve_rows.extend(child_evolve)
        item_rows.extend(child_items)

    return species_rows, evolve_rows, item_rows


async def write_evolution_chain(
    session: AsyncSession,
    pokeapi: PokeLance,
    cache: EnrichmentCache,
    species: Any,
) -> None:
    chain_ref = getattr(species, "evolution_chain", None)
    chain_id = resource_id(chain_ref)
    if chain_id is None:
        return
    if chain_id in cache.evolution_chains:
        # Still ensure current species links to the chain.
        result = await session.run(
            """
            MERGE (s:PokemonSpecies {id: $species_id})
            MERGE (ec:EvolutionChain {id: $chain_id})
            MERGE (s)-[:IN_EVOLUTION_CHAIN]->(ec)
            """,
            species_id=species.id,
            chain_id=chain_id,
        )
        await result.consume()
        return

    chain = await pokeapi.evolution.fetch_evolution_chain(chain_id)
    species_rows, evolve_rows, item_rows = _walk_chain(chain.id, chain.chain)

    batch = RELATIONSHIP_BATCH_SIZE
    if species_rows:
        result = await session.run(
            f"""
            UNWIND $rows AS item
            CALL (item) {{
              MERGE (ec:EvolutionChain {{id: item.chain_id}})
              MERGE (s:PokemonSpecies {{id: item.id}})
              SET s.name = coalesce(s.name, item.name),
                  s.is_baby = item.is_baby
              MERGE (s)-[:IN_EVOLUTION_CHAIN]->(ec)
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            rows=species_rows,
        )
        await result.consume()

    if evolve_rows:
        result = await session.run(
            f"""
            UNWIND $rows AS item
            CALL (item) {{
              MERGE (from:PokemonSpecies {{id: item.from_id}})
              MERGE (to:PokemonSpecies {{id: item.to_id}})
              MERGE (from)-[r:EVOLVES_TO {{id: item.edge_id}}]->(to)
              SET r.trigger = item.trigger,
                  r.min_level = item.min_level,
                  r.min_happiness = item.min_happiness,
                  r.min_beauty = item.min_beauty,
                  r.min_affection = item.min_affection,
                  r.time_of_day = item.time_of_day,
                  r.needs_overworld_rain = item.needs_overworld_rain,
                  r.turn_upside_down = item.turn_upside_down,
                  r.relative_physical_stats = item.relative_physical_stats,
                  r.known_move = item.known_move,
                  r.known_move_type = item.known_move_type,
                  r.held_item = item.held_item,
                  r.location = item.location,
                  r.party_species = item.party_species,
                  r.trade_species = item.trade_species,
                  r.gender = item.gender,
                  r.version_group = item.version_group,
                  r.region = item.region,
                  r.is_default = item.is_default
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            rows=evolve_rows,
        )
        await result.consume()

    if item_rows:
        result = await session.run(
            f"""
            UNWIND $rows AS item
            CALL (item) {{
              MERGE (s:PokemonSpecies {{id: item.species_id}})
              MERGE (i:Item {{id: item.item_id}})
              SET i.name = item.item_name
              MERGE (s)-[:REQUIRES_ITEM]->(i)
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            rows=item_rows,
        )
        await result.consume()

    cache.evolution_chains.add(chain_id)
