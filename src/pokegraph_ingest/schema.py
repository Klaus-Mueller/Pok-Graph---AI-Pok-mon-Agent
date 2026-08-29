from __future__ import annotations

import asyncio
import sys
import time
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from .config import Settings

SCHEMA_QUERIES = (
    "CREATE CONSTRAINT pokemon_id IF NOT EXISTS FOR (p:Pokemon) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT species_id IF NOT EXISTS FOR (s:PokemonSpecies) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT type_id IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT ability_id IF NOT EXISTS FOR (a:Ability) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT move_id IF NOT EXISTS FOR (m:Move) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT game_version_id IF NOT EXISTS FOR (v:GameVersion) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT version_group_id IF NOT EXISTS FOR (vg:VersionGroup) REQUIRE vg.id IS UNIQUE",
    "CREATE CONSTRAINT region_id IF NOT EXISTS FOR (r:Region) REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT location_area_id IF NOT EXISTS FOR (la:LocationArea) REQUIRE la.id IS UNIQUE",
    "CREATE CONSTRAINT encounter_method_id IF NOT EXISTS FOR (em:EncounterMethod) REQUIRE em.id IS UNIQUE",
    "CREATE CONSTRAINT encounter_id IF NOT EXISTS FOR (e:Encounter) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT evolution_chain_id IF NOT EXISTS FOR (ec:EvolutionChain) REQUIRE ec.id IS UNIQUE",
    "CREATE CONSTRAINT item_id IF NOT EXISTS FOR (i:Item) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT source_id IF NOT EXISTS FOR (src:Source) REQUIRE src.id IS UNIQUE",
    # Relationship identity for MERGE (from)-[r:EVOLVES_TO {id}]->(to)
    "CREATE CONSTRAINT evolves_to_id IF NOT EXISTS FOR ()-[r:EVOLVES_TO]-() REQUIRE r.id IS UNIQUE",
    "CREATE CONSTRAINT learnset_entry_id IF NOT EXISTS FOR (e:LearnsetEntry) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT move_learn_method_id IF NOT EXISTS FOR (m:MoveLearnMethod) REQUIRE m.id IS UNIQUE",
)

EXPECTED_CONSTRAINT_NAMES: frozenset[str] = frozenset(
    (
        "pokemon_id",
        "species_id",
        "type_id",
        "ability_id",
        "move_id",
        "game_version_id",
        "version_group_id",
        "region_id",
        "location_id",
        "location_area_id",
        "encounter_method_id",
        "encounter_id",
        "evolution_chain_id",
        "item_id",
        "source_id",
        "evolves_to_id",
        "learnset_entry_id",
        "move_learn_method_id",
    )
)

# Strip legacy detail properties from CAN_LEARN (moved to LearnsetEntry).
CAN_LEARN_PROPERTY_CLEANUP = """
MATCH ()-[r:CAN_LEARN]->()
REMOVE r.level, r.method, r.version_group
"""

# Commit relationship MERGEs in small batches so large lists do not create huge transactions.
RELATIONSHIP_BATCH_SIZE = 500

_DEFAULT_ONLINE_TIMEOUT_S = 120.0
_ONLINE_POLL_INTERVAL_S = 1.0


async def apply_schema(session: AsyncSession) -> None:
    """Create all uniqueness constraints idempotently and migrate legacy CAN_LEARN props."""
    for query in SCHEMA_QUERIES:
        result = await session.run(query)
        await result.consume()
    result = await session.run(CAN_LEARN_PROPERTY_CLEANUP)
    await result.consume()


async def _list_constraints(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.run("SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties, ownedIndex")
    rows = [dict(record) async for record in result]
    await result.consume()
    return rows


async def _list_indexes(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.run(
        "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state, owningConstraint"
    )
    rows = [dict(record) async for record in result]
    await result.consume()
    return rows


def _constraint_names(constraints: list[dict[str, Any]]) -> set[str]:
    return {str(row["name"]) for row in constraints if row.get("name")}


def _backing_index_states(
    indexes: list[dict[str, Any]],
    constraint_names: set[str],
) -> dict[str, str]:
    """Map expected constraint name -> backing index state (ONLINE / POPULATING / …)."""
    states: dict[str, str] = {}
    for row in indexes:
        owning = row.get("owningConstraint")
        name = row.get("name")
        state = str(row.get("state") or "")
        # Prefer matching by owningConstraint; fall back to index name == constraint name.
        if owning and str(owning) in constraint_names:
            states[str(owning)] = state
        elif name and str(name) in constraint_names:
            states.setdefault(str(name), state)
    return states


async def verify_schema_online(
    session: AsyncSession,
    *,
    timeout_s: float = _DEFAULT_ONLINE_TIMEOUT_S,
) -> dict[str, Any]:
    """
    Assert all expected constraints exist and their backing indexes are ONLINE.

    Polls until timeout if indexes are still POPULATING.
    Raises RuntimeError on missing constraints or indexes that never go ONLINE.
    """
    deadline = time.monotonic() + timeout_s
    last_states: dict[str, str] = {}
    while True:
        constraints = await _list_constraints(session)
        present = _constraint_names(constraints)
        missing = EXPECTED_CONSTRAINT_NAMES - present
        if missing:
            raise RuntimeError(
                "Missing Neo4j constraints required for ingest MERGE lookups: "
                + ", ".join(sorted(missing))
            )

        indexes = await _list_indexes(session)
        last_states = _backing_index_states(indexes, EXPECTED_CONSTRAINT_NAMES)
        not_ready = [
            name
            for name in sorted(EXPECTED_CONSTRAINT_NAMES)
            if last_states.get(name, "").upper() != "ONLINE"
        ]
        if not not_ready:
            return {
                "constraints": constraints,
                "indexes": indexes,
                "states": last_states,
            }

        if time.monotonic() >= deadline:
            detail = ", ".join(f"{n}={last_states.get(n, 'MISSING')}" for n in not_ready)
            raise RuntimeError(
                f"Neo4j constraint-backed indexes not ONLINE within {timeout_s:.0f}s: {detail}"
            )
        await asyncio.sleep(_ONLINE_POLL_INTERVAL_S)


async def ensure_schema(session: AsyncSession, *, timeout_s: float = _DEFAULT_ONLINE_TIMEOUT_S) -> dict[str, Any]:
    """Apply constraints then verify they (and backing indexes) are ONLINE."""
    await apply_schema(session)
    return await verify_schema_online(session, timeout_s=timeout_s)


def format_schema_report(report: dict[str, Any]) -> str:
    lines = ["Constraints (expected = ingest MERGE identity indexes):"]
    states: dict[str, str] = report.get("states") or {}
    for name in sorted(EXPECTED_CONSTRAINT_NAMES):
        state = states.get(name, "UNKNOWN")
        lines.append(f"  {name}: index {state}")
    return "\n".join(lines)


async def _run_verify(settings: Settings) -> int:
    driver: AsyncDriver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    try:
        await driver.verify_connectivity()
        async with driver.session(database=settings.neo4j_database) as session:
            print(f"Applying schema on database '{settings.neo4j_database}'...")
            report = await ensure_schema(session)
            print(format_schema_report(report))
            print("Schema OK: all expected uniqueness constraints are ONLINE.")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI exit path
        print(f"Schema verification failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await driver.close()


def main() -> None:
    raise SystemExit(asyncio.run(_run_verify(Settings.from_environment())))


if __name__ == "__main__":
    main()
