from __future__ import annotations

from typing import Any

from neo4j import AsyncSession
from pokelance import PokeLance

from ..cache import EnrichmentCache
from ..resources import resource_id, resource_name
from ..schema import RELATIONSHIP_BATCH_SIZE


def _encounter_id(
    pokemon_id: int,
    location_area_id: int,
    version_id: int,
    method_id: int,
    min_level: int,
    max_level: int,
    chance: int,
    conditions: str,
) -> str:
    return (
        f"{pokemon_id}:{location_area_id}:{version_id}:{method_id}:"
        f"{min_level}:{max_level}:{chance}:{conditions}"
    )


def flatten_encounters(pokemon_id: int, location_encounters: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in location_encounters:
        area = entry.location_area
        area_id = resource_id(area)
        if area_id is None:
            continue
        area_name = resource_name(area)
        for version_detail in getattr(entry, "version_details", []):
            version = version_detail.version
            version_id = resource_id(version)
            if version_id is None:
                continue
            version_name = resource_name(version)
            for detail in getattr(version_detail, "encounter_details", []):
                method = detail.method
                method_id = resource_id(method)
                if method_id is None:
                    continue
                condition_names = sorted(
                    name
                    for value in getattr(detail, "condition_values", [])
                    if (name := resource_name(value))
                )
                conditions = "|".join(condition_names)
                min_level = int(detail.min_level)
                max_level = int(detail.max_level)
                chance = int(detail.chance)
                rows.append(
                    {
                        "id": _encounter_id(
                            pokemon_id,
                            area_id,
                            version_id,
                            method_id,
                            min_level,
                            max_level,
                            chance,
                            conditions,
                        ),
                        "min_level": min_level,
                        "max_level": max_level,
                        "chance": chance,
                        "condition_values": condition_names,
                        "location_area_id": area_id,
                        "location_area_name": area_name,
                        "version_id": version_id,
                        "version_name": version_name,
                        "method_id": method_id,
                        "method_name": resource_name(method),
                    }
                )
    return rows


async def write_encounters(session: AsyncSession, pokemon_id: int, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    batch = RELATIONSHIP_BATCH_SIZE
    result = await session.run(
        f"""
        UNWIND $rows AS item
        CALL (item) {{
          MATCH (p:Pokemon {{id: $pokemon_id}})
          MERGE (e:Encounter {{id: item.id}})
          SET e.min_level = item.min_level,
              e.max_level = item.max_level,
              e.chance = item.chance,
              e.condition_values = item.condition_values
          MERGE (la:LocationArea {{id: item.location_area_id}})
          SET la.name = item.location_area_name
          MERGE (v:GameVersion {{id: item.version_id}})
          SET v.name = item.version_name
          MERGE (m:EncounterMethod {{id: item.method_id}})
          SET m.name = item.method_name
          MERGE (p)-[:HAS_ENCOUNTER]->(e)
          MERGE (e)-[:AT_LOCATION_AREA]->(la)
          MERGE (e)-[:IN_VERSION]->(v)
          MERGE (e)-[:USES_METHOD]->(m)
          MERGE (p)-[:AVAILABLE_IN_VERSION]->(v)
          MERGE (p)-[:CAN_BE_FOUND_IN]->(la)
        }} IN TRANSACTIONS OF {batch} ROWS
        """,
        pokemon_id=pokemon_id,
        rows=rows,
    )
    await result.consume()


async def enrich_hierarchy(
    session: AsyncSession,
    pokeapi: PokeLance,
    cache: EnrichmentCache,
    rows: list[dict[str, Any]],
) -> None:
    """Fetch location-area / location / version / version-group details once and wire hierarchy."""
    area_ids = {row["location_area_id"] for row in rows}
    version_ids = {row["version_id"] for row in rows}

    for area_id in sorted(area_ids):
        if area_id in cache.location_areas:
            continue
        area = await pokeapi.location.fetch_location_area(area_id)
        location_ref = area.location
        location_id = resource_id(location_ref)
        location_name = resource_name(location_ref)
        result = await session.run(
            """
            MERGE (la:LocationArea {id: $area_id})
            SET la.name = $area_name
            """,
            area_id=area.id,
            area_name=area.name,
        )
        await result.consume()
        if location_id is not None:
            result = await session.run(
                """
                MERGE (la:LocationArea {id: $area_id})
                MERGE (l:Location {id: $location_id})
                SET l.name = $location_name
                MERGE (la)-[:PART_OF_LOCATION]->(l)
                """,
                area_id=area.id,
                location_id=location_id,
                location_name=location_name or f"location-{location_id}",
            )
            await result.consume()
            if location_id not in cache.locations:
                location = await pokeapi.location.fetch_location(location_id)
                region = location.region
                region_id = resource_id(region) if region is not None else None
                if region_id is not None:
                    result = await session.run(
                        """
                        MERGE (l:Location {id: $location_id})
                        SET l.name = $location_name
                        MERGE (r:Region {id: $region_id})
                        SET r.name = $region_name
                        MERGE (l)-[:IN_REGION]->(r)
                        """,
                        location_id=location.id,
                        location_name=location.name,
                        region_id=region_id,
                        region_name=resource_name(region),
                    )
                    await result.consume()
                else:
                    result = await session.run(
                        """
                        MERGE (l:Location {id: $location_id})
                        SET l.name = $location_name
                        """,
                        location_id=location.id,
                        location_name=location.name,
                    )
                    await result.consume()
                cache.locations.add(location_id)
        cache.location_areas.add(area_id)

    for version_id in sorted(version_ids):
        if version_id in cache.versions:
            continue
        version = await pokeapi.game.fetch_version(version_id)
        vg_ref = version.version_group
        vg_id = resource_id(vg_ref)
        result = await session.run(
            """
            MERGE (v:GameVersion {id: $version_id})
            SET v.name = $version_name
            """,
            version_id=version.id,
            version_name=version.name,
        )
        await result.consume()
        if vg_id is not None:
            result = await session.run(
                """
                MERGE (v:GameVersion {id: $version_id})
                MERGE (vg:VersionGroup {id: $vg_id})
                SET vg.name = $vg_name
                MERGE (v)-[:IN_VERSION_GROUP]->(vg)
                """,
                version_id=version.id,
                vg_id=vg_id,
                vg_name=resource_name(vg_ref) or f"version-group-{vg_id}",
            )
            await result.consume()
            if vg_id not in cache.version_groups:
                vg = await pokeapi.game.fetch_version_group(vg_id)
                result = await session.run(
                    """
                    MERGE (vg:VersionGroup {id: $vg_id})
                    SET vg.name = $vg_name
                    """,
                    vg_id=vg.id,
                    vg_name=vg.name,
                )
                await result.consume()
                for region in getattr(vg, "regions", []):
                    region_id = resource_id(region)
                    if region_id is None:
                        continue
                    result = await session.run(
                        """
                        MERGE (vg:VersionGroup {id: $vg_id})
                        MERGE (r:Region {id: $region_id})
                        SET r.name = $region_name
                        MERGE (vg)-[:IN_REGION]->(r)
                        """,
                        vg_id=vg.id,
                        region_id=region_id,
                        region_name=resource_name(region),
                    )
                    await result.consume()
                cache.version_groups.add(vg_id)
        cache.versions.add(version_id)
