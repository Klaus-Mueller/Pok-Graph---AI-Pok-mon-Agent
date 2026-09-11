from __future__ import annotations

from typing import Any

from neo4j import AsyncSession

from pokegraph.sources.base import DataSource
from pokegraph.sources.models import EncounterSet, LocationAreaEncounter, Provenance

from ..cache import EnrichmentCache
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


def flatten_encounters(
    pokemon_id: int,
    location_encounters: list[LocationAreaEncounter] | EncounterSet,
    provenance: Provenance | None = None,
) -> list[dict[str, Any]]:
    if isinstance(location_encounters, EncounterSet):
        rows_in = location_encounters.rows
        provenance = location_encounters.provenance
    else:
        rows_in = location_encounters
    source_url = provenance.source_url if provenance else None
    source_version = provenance.source_version if provenance else None
    retrieved_at = provenance.retrieved_at.isoformat() if provenance else None
    rows: list[dict[str, Any]] = []
    for entry in rows_in:
        area_id = entry.location_area.id
        if area_id is None:
            continue
        area_name = entry.location_area.name
        for version_detail in entry.version_details:
            version_id = version_detail.version.id
            if version_id is None:
                continue
            version_name = version_detail.version.name
            for detail in version_detail.encounter_details:
                method_id = detail.method.id
                if method_id is None:
                    continue
                condition_names = sorted(ref.name for ref in detail.condition_values if ref.name)
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
                        "method_name": detail.method.name,
                        "source_url": source_url,
                        "source_version": source_version,
                        "retrieved_at": retrieved_at,
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
              e.condition_values = item.condition_values,
              e.source_url = item.source_url,
              e.source_version = item.source_version,
              e.retrieved_at = item.retrieved_at
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


def _prov(model: Any) -> dict[str, Any]:
    provenance = model.provenance
    return {
        "source_url": provenance.source_url,
        "source_version": provenance.source_version,
        "retrieved_at": provenance.retrieved_at.isoformat(),
    }


async def enrich_hierarchy(
    session: AsyncSession,
    source: DataSource,
    cache: EnrichmentCache,
    rows: list[dict[str, Any]],
) -> None:
    """Fetch location-area / location / version / version-group details once and wire hierarchy."""
    area_ids = {row["location_area_id"] for row in rows}
    version_ids = {row["version_id"] for row in rows}

    for area_id in sorted(area_ids):
        if area_id in cache.location_areas:
            continue
        area = await source.get_location_area(area_id)
        location_ref = area.location
        location_id = location_ref.id
        location_name = location_ref.name
        area_prov = _prov(area)
        result = await session.run(
            """
            MERGE (la:LocationArea {id: $area_id})
            SET la.name = $area_name,
                la.source_url = $source_url,
                la.source_version = $source_version,
                la.retrieved_at = $retrieved_at
            """,
            area_id=area.id,
            area_name=area.name,
            **area_prov,
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
                location = await source.get_location(location_id)
                region = location.region
                region_id = region.id if region is not None else None
                loc_prov = _prov(location)
                if region_id is not None:
                    result = await session.run(
                        """
                        MERGE (l:Location {id: $location_id})
                        SET l.name = $location_name,
                            l.source_url = $source_url,
                            l.source_version = $source_version,
                            l.retrieved_at = $retrieved_at
                        MERGE (r:Region {id: $region_id})
                        SET r.name = $region_name
                        MERGE (l)-[:IN_REGION]->(r)
                        """,
                        location_id=location.id,
                        location_name=location.name,
                        region_id=region_id,
                        region_name=region.name if region is not None else "",
                        **loc_prov,
                    )
                    await result.consume()
                else:
                    result = await session.run(
                        """
                        MERGE (l:Location {id: $location_id})
                        SET l.name = $location_name,
                            l.source_url = $source_url,
                            l.source_version = $source_version,
                            l.retrieved_at = $retrieved_at
                        """,
                        location_id=location.id,
                        location_name=location.name,
                        **loc_prov,
                    )
                    await result.consume()
                cache.locations.add(location_id)
        cache.location_areas.add(area_id)

    for version_id in sorted(version_ids):
        if version_id in cache.versions:
            continue
        version = await source.get_version(version_id)
        vg_ref = version.version_group
        vg_id = vg_ref.id if vg_ref is not None else None
        ver_prov = _prov(version)
        result = await session.run(
            """
            MERGE (v:GameVersion {id: $version_id})
            SET v.name = $version_name,
                v.source_url = $source_url,
                v.source_version = $source_version,
                v.retrieved_at = $retrieved_at
            """,
            version_id=version.id,
            version_name=version.name,
            **ver_prov,
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
                vg_name=vg_ref.name if vg_ref is not None else f"version-group-{vg_id}",
            )
            await result.consume()
            if vg_id not in cache.version_groups:
                vg = await source.get_version_group(vg_id)
                vg_prov = _prov(vg)
                result = await session.run(
                    """
                    MERGE (vg:VersionGroup {id: $vg_id})
                    SET vg.name = $vg_name,
                        vg.source_url = $source_url,
                        vg.source_version = $source_version,
                        vg.retrieved_at = $retrieved_at
                    """,
                    vg_id=vg.id,
                    vg_name=vg.name,
                    **vg_prov,
                )
                await result.consume()
                for region in vg.regions:
                    region_id = region.id
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
                        region_name=region.name,
                    )
                    await result.consume()
                cache.version_groups.add(vg_id)
        cache.versions.add(version_id)
