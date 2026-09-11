from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pokelance import PokeLance

from pokegraph import __version__
from pokegraph.errors import SourceFetchError
from pokegraph.sources.cache import DiskCache
from pokegraph.sources.convert import (
    normalize_ability,
    normalize_encounters,
    normalize_evolution_chain,
    normalize_item,
    normalize_location,
    normalize_location_area,
    normalize_move,
    normalize_pokemon,
    normalize_region,
    normalize_species,
    normalize_type,
    normalize_version,
    normalize_version_group,
    payload_hash,
    utc_now,
)
from pokegraph.sources.models import (
    SOURCE_VERSION_UNAVAILABLE,
    Ability,
    EvolutionChain,
    GameVersion,
    Item,
    Location,
    LocationArea,
    EncounterSet,
    Move,
    Pokemon,
    PokemonSpecies,
    Provenance,
    Region,
    Type,
    VersionGroup,
)
from pokegraph.sources.serde import (
    ability_from_dict,
    ability_to_dict,
    encounters_from_dict,
    encounters_to_dict,
    evolution_chain_from_dict,
    evolution_chain_to_dict,
    item_from_dict,
    item_to_dict,
    location_area_from_dict,
    location_area_to_dict,
    location_from_dict,
    location_to_dict,
    move_from_dict,
    move_to_dict,
    pokemon_from_dict,
    pokemon_to_dict,
    region_from_dict,
    region_to_dict,
    species_from_dict,
    species_to_dict,
    type_from_dict,
    type_to_dict,
    version_from_dict,
    version_group_from_dict,
    version_group_to_dict,
    version_to_dict,
)

logger = logging.getLogger("pokegraph.source")

T = TypeVar("T")
POKEAPI_BASE = "https://pokeapi.co/api/v2"


class PokeApiSource:
    """PokéAPI adapter. This is the only module that imports PokeLance."""

    def __init__(
        self,
        *,
        cache_size: int = 2000,
        cache_dir: Path | None = None,
        cache_ttl_s: float | None = None,
        client: PokeLance | None = None,
    ) -> None:
        self._client = client or PokeLance(cache_size=cache_size, cache_endpoints=True)
        self._owns_client = client is None
        self._cache = DiskCache(cache_dir, ttl_s=cache_ttl_s)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.close()

    async def get_pokemon(self, identifier: str | int, *, force_refresh: bool = False) -> Pokemon:
        return await self._cached(
            "pokemon",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.pokemon.fetch_pokemon(identifier),
            normalize=normalize_pokemon,
            to_dict=pokemon_to_dict,
            from_dict=pokemon_from_dict,
            source_url=f"{POKEAPI_BASE}/pokemon/{identifier}/",
        )

    async def get_species(self, identifier: str | int, *, force_refresh: bool = False) -> PokemonSpecies:
        return await self._cached(
            "pokemon-species",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.pokemon.fetch_pokemon_species(identifier),
            normalize=normalize_species,
            to_dict=species_to_dict,
            from_dict=species_from_dict,
            source_url=f"{POKEAPI_BASE}/pokemon-species/{identifier}/",
        )

    async def get_type(self, identifier: str | int, *, force_refresh: bool = False) -> Type:
        return await self._cached(
            "type",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.pokemon.fetch_type(identifier),
            normalize=normalize_type,
            to_dict=type_to_dict,
            from_dict=type_from_dict,
            source_url=f"{POKEAPI_BASE}/type/{identifier}/",
        )

    async def get_ability(self, identifier: str | int, *, force_refresh: bool = False) -> Ability:
        return await self._cached(
            "ability",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._fetch_named("ability", identifier),
            normalize=normalize_ability,
            to_dict=ability_to_dict,
            from_dict=ability_from_dict,
            source_url=f"{POKEAPI_BASE}/ability/{identifier}/",
        )

    async def get_move(self, identifier: str | int, *, force_refresh: bool = False) -> Move:
        return await self._cached(
            "move",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.move.fetch_move(identifier),
            normalize=normalize_move,
            to_dict=move_to_dict,
            from_dict=move_from_dict,
            source_url=f"{POKEAPI_BASE}/move/{identifier}/",
        )

    async def get_version(self, identifier: str | int, *, force_refresh: bool = False) -> GameVersion:
        return await self._cached(
            "version",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.game.fetch_version(identifier),
            normalize=normalize_version,
            to_dict=version_to_dict,
            from_dict=version_from_dict,
            source_url=f"{POKEAPI_BASE}/version/{identifier}/",
        )

    async def get_version_group(self, identifier: str | int, *, force_refresh: bool = False) -> VersionGroup:
        return await self._cached(
            "version-group",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.game.fetch_version_group(identifier),
            normalize=normalize_version_group,
            to_dict=version_group_to_dict,
            from_dict=version_group_from_dict,
            source_url=f"{POKEAPI_BASE}/version-group/{identifier}/",
        )

    async def get_region(self, identifier: str | int, *, force_refresh: bool = False) -> Region:
        return await self._cached(
            "region",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._fetch_named("region", identifier),
            normalize=normalize_region,
            to_dict=region_to_dict,
            from_dict=region_from_dict,
            source_url=f"{POKEAPI_BASE}/region/{identifier}/",
        )

    async def get_location(self, identifier: str | int, *, force_refresh: bool = False) -> Location:
        return await self._cached(
            "location",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.location.fetch_location(identifier),
            normalize=normalize_location,
            to_dict=location_to_dict,
            from_dict=location_from_dict,
            source_url=f"{POKEAPI_BASE}/location/{identifier}/",
        )

    async def get_location_area(self, identifier: str | int, *, force_refresh: bool = False) -> LocationArea:
        return await self._cached(
            "location-area",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.location.fetch_location_area(identifier),
            normalize=normalize_location_area,
            to_dict=location_area_to_dict,
            from_dict=location_area_from_dict,
            source_url=f"{POKEAPI_BASE}/location-area/{identifier}/",
        )

    async def get_encounters(
        self,
        pokemon: str | int,
        *,
        force_refresh: bool = False,
    ) -> EncounterSet:
        source_url = f"{POKEAPI_BASE}/pokemon/{pokemon}/encounters/"
        started = time.monotonic()
        error_category: str | None = None
        try:
            if not force_refresh:
                cached = self._cache.get("pokemon-encounters", pokemon)
                if cached is not None:
                    return EncounterSet(
                        rows=tuple(encounters_from_dict(cached.data)),
                        provenance=Provenance(
                            source_url=cached.source_url,
                            retrieved_at=cached.retrieved_at,
                            source_version=cached.source_version,
                            adapter_version=cached.adapter_version,
                            payload_hash=cached.payload_hash,
                        ),
                    )
            try:
                raw = await self._client.pokemon.fetch_location_area_encounter(pokemon)
            except Exception as exc:  # noqa: BLE001
                raise SourceFetchError(f"Failed to fetch pokemon-encounters {pokemon}.") from exc
            retrieved_at = utc_now()
            rows = tuple(normalize_encounters(raw))
            data = encounters_to_dict(list(rows))
            hashed = payload_hash({"items": data})
            provenance = Provenance(
                source_url=source_url,
                retrieved_at=retrieved_at,
                source_version=_source_version(raw),
                adapter_version=__version__,
                payload_hash=hashed,
            )
            self._cache.put(
                "pokemon-encounters",
                pokemon,
                data,
                retrieved_at=retrieved_at,
                source_url=source_url,
                source_version=provenance.source_version,
                adapter_version=__version__,
                payload_hash=hashed,
            )
            return EncounterSet(rows=rows, provenance=provenance)
        except Exception as exc:
            error_category = type(exc).__name__
            raise
        finally:
            logger.info(
                "source_fetch resource=%s duration_ms=%s row_count=%s error=%s",
                "pokemon-encounters",
                int((time.monotonic() - started) * 1000),
                None if error_category else "ok",
                error_category,
            )

    async def get_evolution_chain(self, identifier: str | int, *, force_refresh: bool = False) -> EvolutionChain:
        return await self._cached(
            "evolution-chain",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._client.evolution.fetch_evolution_chain(identifier),
            normalize=normalize_evolution_chain,
            to_dict=evolution_chain_to_dict,
            from_dict=evolution_chain_from_dict,
            source_url=f"{POKEAPI_BASE}/evolution-chain/{identifier}/",
        )

    async def get_item(self, identifier: str | int, *, force_refresh: bool = False) -> Item:
        return await self._cached(
            "item",
            identifier,
            force_refresh=force_refresh,
            fetch=lambda: self._fetch_named("item", identifier),
            normalize=normalize_item,
            to_dict=item_to_dict,
            from_dict=item_from_dict,
            source_url=f"{POKEAPI_BASE}/item/{identifier}/",
        )

    async def _fetch_named(self, resource: str, identifier: str | int) -> Any:
        group = {
            "ability": getattr(self._client, "pokemon", None),
            "item": getattr(self._client, "item", None),
            "region": getattr(self._client, "location", None),
        }.get(resource)
        method_name = f"fetch_{resource.replace('-', '_')}"
        method = getattr(group, method_name, None) if group is not None else None
        if method is None:
            raise SourceFetchError(f"PokeLance does not expose {method_name}.")
        return await method(identifier)

    async def _cached(
        self,
        resource: str,
        identifier: str | int,
        *,
        force_refresh: bool,
        fetch: Callable[[], Awaitable[Any]],
        normalize: Callable[..., T],
        to_dict: Callable[[T], Any],
        from_dict: Callable[[Any], T],
        source_url: str,
    ) -> T:
        started = time.monotonic()
        error_category: str | None = None
        result_count = 1
        try:
            if not force_refresh:
                cached = self._cache.get(resource, identifier)
                if cached is not None:
                    model = from_dict(cached.data)
                    duration_ms = int((time.monotonic() - started) * 1000)
                    logger.info(
                        "source_fetch resource=%s duration_ms=%s row_count=%s error=%s",
                        resource,
                        duration_ms,
                        result_count,
                        None,
                    )
                    return model
            try:
                raw = await fetch()
            except Exception as exc:  # noqa: BLE001 — mapped to source error
                raise SourceFetchError(f"Failed to fetch {resource} {identifier}.") from exc
            retrieved_at = utc_now()
            provenance = Provenance(
                source_url=source_url,
                retrieved_at=retrieved_at,
                source_version=_source_version(raw),
                adapter_version=__version__,
            )
            model = normalize(raw, provenance)
            data = to_dict(model)
            hashed = payload_hash(data if isinstance(data, dict) else {"items": data})
            if hasattr(model, "provenance"):
                model = _with_hash(model, hashed)
                data = to_dict(model)
            self._cache.put(
                resource,
                identifier,
                data,
                retrieved_at=retrieved_at,
                source_url=source_url,
                source_version=_source_version(raw),
                adapter_version=__version__,
                payload_hash=hashed,
            )
            return model
        except Exception as exc:
            error_category = type(exc).__name__
            raise
        finally:
            if error_category is not None:
                logger.info(
                    "source_fetch resource=%s duration_ms=%s row_count=%s error=%s",
                    resource,
                    int((time.monotonic() - started) * 1000),
                    None,
                    error_category,
                )


def _source_version(raw: Any) -> str:
    for attr in ("version", "revision", "etag"):
        value = getattr(raw, attr, None)
        if value:
            return str(value)
    return SOURCE_VERSION_UNAVAILABLE


def _with_hash(model: Any, hashed: str) -> Any:
    provenance = model.provenance
    updated = Provenance(
        source_url=provenance.source_url,
        retrieved_at=provenance.retrieved_at,
        source_version=provenance.source_version,
        adapter_version=provenance.adapter_version,
        payload_hash=hashed,
    )
    return type(model)(**{**model.__dict__, "provenance": updated})
