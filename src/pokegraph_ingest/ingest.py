from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field

import aiohttp
from neo4j import AsyncGraphDatabase
from pokelance import PokeLance

from .cache import EnrichmentCache
from .config import Settings
from .schema import ensure_schema, format_schema_report
from .writes import (
    enrich_hierarchy,
    enrich_moves,
    enrich_types,
    ensure_source,
    flatten_encounters,
    learnset_entry_rows,
    link_has_source,
    write_encounters,
    write_evolution_chain,
    write_learnsets,
    write_pokemon,
)


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

    def set_status(self, status: str) -> None:
        self.status = status
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
            f"{self.status:<10} {label:<28} | "
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


async def ingest(settings: Settings) -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    pokeapi = PokeLance(cache_size=settings.pokeapi_cache_size, cache_endpoints=True)
    cache = EnrichmentCache()
    try:
        names = await _resolve_pokemon_names(settings)
        total = len(names)
        print(f"Connecting to Neo4j ({settings.neo4j_database})...")
        await driver.verify_connectivity()
        print("Ensuring graph constraints and verifying indexes ONLINE...")
        async with driver.session(database=settings.neo4j_database) as session:
            report = await ensure_schema(session)
            print(format_schema_report(report))
            await ensure_source(session, cache)
            print(f"Ingesting {total} Pokémon into Neo4j (MVP relationships)...\n")
            progress = IngestProgress(total=total)
            for name in names:
                progress.begin(name)
                try:
                    progress.set_status("core")
                    pokemon = await pokeapi.pokemon.fetch_pokemon(name)
                    species = await pokeapi.pokemon.fetch_pokemon_species(pokemon.species.name)
                    type_ids, move_ids = await write_pokemon(session, pokemon, species)

                    progress.set_status("learnsets")
                    learnset_rows = learnset_entry_rows(pokemon)
                    await write_learnsets(session, learnset_rows)

                    progress.set_status("moves")
                    await enrich_moves(session, pokeapi, cache, move_ids)

                    progress.set_status("encounters")
                    location_encounters = await pokeapi.pokemon.fetch_location_area_encounter(name)
                    encounter_rows = flatten_encounters(pokemon.id, location_encounters)
                    await write_encounters(session, pokemon.id, encounter_rows)
                    await enrich_hierarchy(session, pokeapi, cache, encounter_rows)

                    progress.set_status("evolution")
                    await write_evolution_chain(session, pokeapi, cache, species)

                    progress.set_status("types")
                    await enrich_types(session, pokeapi, cache, type_ids)

                    progress.set_status("source")
                    await link_has_source(session, pokemon.id, species.id)

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
