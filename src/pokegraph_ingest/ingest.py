from __future__ import annotations

import asyncio
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from neo4j import AsyncGraphDatabase, AsyncManagedTransaction, AsyncSession
from pokelance import PokeLance

from .config import Settings


SCHEMA_QUERIES = (
    "CREATE CONSTRAINT pokemon_id IF NOT EXISTS FOR (p:Pokemon) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT species_id IF NOT EXISTS FOR (s:PokemonSpecies) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT type_id IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT ability_id IF NOT EXISTS FOR (a:Ability) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT move_id IF NOT EXISTS FOR (m:Move) REQUIRE m.id IS UNIQUE",
)

# Commit relationship MERGEs in small batches so large move lists do not create huge transactions.
RELATIONSHIP_BATCH_SIZE = 500
PROGRESS_BAR_WIDTH = 28


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


@dataclass
class IngestProgress:
    total: int
    started_at: float = field(default_factory=time.monotonic)
    done: int = 0
    ok: int = 0
    failed: int = 0
    current: str = ""
    status: str = "starting"
    _last_width: int = 0

    def begin(self, name: str) -> None:
        self.current = name
        self.status = "fetching"
        self._render()

    def succeed(self, name: str, pokemon_id: int) -> None:
        self.done += 1
        self.ok += 1
        self.current = f"{name} #{pokemon_id}"
        self.status = "ok"
        self._render()

    def fail(self, name: str, error: str) -> None:
        self.done += 1
        self.failed += 1
        self.current = name
        self.status = "fail"
        self._render()
        # Keep failure details on their own line so the live bar stays readable.
        print(f"\n  ! failed {name}: {error}", file=sys.stderr, flush=True)
        self._render()

    def finish(self) -> None:
        self.status = "done"
        self._render(final=True)

    def _render(self, *, final: bool = False) -> None:
        elapsed = time.monotonic() - self.started_at
        ratio = (self.done / self.total) if self.total else 1.0
        filled = int(PROGRESS_BAR_WIDTH * ratio)
        bar = f"{'█' * filled}{'░' * (PROGRESS_BAR_WIDTH - filled)}"
        percent = ratio * 100
        rate = (self.done / elapsed) if elapsed > 0 and self.done else 0.0
        remaining = self.total - self.done
        eta = (remaining / rate) if rate > 0 else 0.0
        eta_text = _format_duration(eta) if rate > 0 and not final else "—"
        label = self.current or "…"
        if len(label) > 28:
            label = label[:25] + "..."
        line = (
            f"\r[{bar}] {self.done}/{self.total} {percent:5.1f}% | "
            f"{self.status:<8} {label:<28} | "
            f"ok:{self.ok} fail:{self.failed} | "
            f"{rate:5.2f}/s | elapsed {_format_duration(elapsed)} | ETA {eta_text}"
        )
        pad = max(0, self._last_width - len(line))
        sys.stdout.write(line + (" " * pad))
        sys.stdout.flush()
        self._last_width = len(line)
        if final:
            sys.stdout.write("\n")
            sys.stdout.flush()
            print(
                f"Done: {self.ok} ingested, {self.failed} failed "
                f"in {_format_duration(elapsed)} ({rate:.2f}/s)."
            )


def _resource_id(resource: Any) -> int | None:
    url = getattr(resource, "url", "") or ""
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None


def _resource_name(resource: Any) -> str:
    return getattr(resource, "name", "") or ""


def _relationship_rows(pokemon: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    types = []
    for entry in getattr(pokemon, "types", []):
        resource = entry.type
        resource_id = _resource_id(resource)
        if resource_id is not None:
            types.append({"id": resource_id, "name": _resource_name(resource), "slot": entry.slot})

    abilities = []
    for entry in getattr(pokemon, "abilities", []):
        resource = entry.ability
        resource_id = _resource_id(resource)
        if resource_id is not None:
            abilities.append(
                {"id": resource_id, "name": _resource_name(resource), "slot": entry.slot, "is_hidden": entry.is_hidden}
            )

    moves = []
    for entry in getattr(pokemon, "moves", []):
        resource = entry.move
        resource_id = _resource_id(resource)
        if resource_id is None:
            continue
        for detail in getattr(entry, "version_group_details", []):
            version_group = detail.version_group
            moves.append(
                {
                    "id": resource_id,
                    "name": _resource_name(resource),
                    "version_group": _resource_name(version_group),
                    "level": detail.level_learned_at,
                    "method": _resource_name(detail.move_learn_method),
                }
            )
    return types, abilities, moves


async def _fetch_pokemon_catalog(url: str) -> list[str]:
    async with aiohttp.ClientSession() as http:
        async with http.get(url) as response:
            response.raise_for_status()
            payload = await response.json()
    results = payload.get("results")
    if not results:
        raise RuntimeError(f"PokéAPI catalog at {url} returned no results.")
    names = [item["name"] for item in results if item.get("name")]
    if not names:
        raise RuntimeError(f"PokéAPI catalog at {url} returned no Pokémon names.")
    return names


async def _resolve_pokemon_names(settings: Settings) -> list[str]:
    if settings.pokemon_names:
        print(f"Using {len(settings.pokemon_names)} Pokémon from POKEGRAPH_POKEMON_NAMES.")
        return list(settings.pokemon_names)
    print(f"Fetching Pokémon catalog from {settings.pokeapi_pokemon_list_url}...")
    names = await _fetch_pokemon_catalog(settings.pokeapi_pokemon_list_url)
    print(f"Catalog returned {len(names)} Pokémon.")
    return names


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
        generation=_resource_name(species.generation),
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
    # CALL ... IN TRANSACTIONS requires auto-commit (session.run), not execute_write.
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
              MERGE (p)-[r:CAN_LEARN]->(m)
              SET r.version_group = item.version_group,
                  r.level = item.level,
                  r.method = item.method
            }} IN TRANSACTIONS OF {batch} ROWS
            """,
            pokemon_id=pokemon_id,
            moves=moves,
        )
        await result.consume()


async def _write_pokemon(session: AsyncSession, pokemon: Any, species: Any) -> None:
    types, abilities, moves = _relationship_rows(pokemon)
    await session.execute_write(_write_pokemon_core, pokemon, species)
    await _write_relationship_batches(session, pokemon.id, types, abilities, moves)


async def ingest(settings: Settings) -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    pokeapi = PokeLance(cache_size=settings.pokeapi_cache_size, cache_endpoints=True)
    try:
        names = await _resolve_pokemon_names(settings)
        total = len(names)
        print(f"Connecting to Neo4j ({settings.neo4j_database})...")
        await driver.verify_connectivity()
        print("Ensuring graph constraints...")
        async with driver.session(database=settings.neo4j_database) as session:
            for query in SCHEMA_QUERIES:
                result = await session.run(query)
                await result.consume()
            print(f"Ingesting {total} Pokémon into Neo4j...\n")
            progress = IngestProgress(total=total)
            for name in names:
                progress.begin(name)
                try:
                    pokemon = await pokeapi.pokemon.fetch_pokemon(name)
                    species = await pokeapi.pokemon.fetch_pokemon_species(pokemon.species.name)
                    await _write_pokemon(session, pokemon, species)
                    progress.succeed(name, pokemon.id)
                except Exception as exc:  # noqa: BLE001 — continue full catalog on per-item failures
                    progress.fail(name, str(exc))
            progress.finish()
    finally:
        await pokeapi.close()
        await driver.close()


def main() -> None:
    asyncio.run(ingest(Settings.from_environment()))


if __name__ == "__main__":
    main()
