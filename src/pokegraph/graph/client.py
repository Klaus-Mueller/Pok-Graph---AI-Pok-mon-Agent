from __future__ import annotations

import logging
import time
from typing import Any

from pokegraph.config import Neo4jSettings
from pokegraph.errors import (
    EntityNotFoundError,
    IncompatibleGameContextError,
    InvalidQueryParameterError,
)
from pokegraph.graph.connection import GraphConnection
from pokegraph.graph.models import GameContext, QueryPage
from pokegraph.graph.registry import QueryRegistry
from pokegraph.graph.serialize import records_to_dicts

logger = logging.getLogger("pokegraph.query")


class PokeGraphClient:
    """Read-only catalog client. Does not apply schema or call PokéAPI."""

    def __init__(
        self,
        settings: Neo4jSettings,
        *,
        connection: GraphConnection | None = None,
        registry: QueryRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._connection = connection or GraphConnection(settings)
        self._registry = registry or QueryRegistry.load()
        self._owns_connection = connection is None

    @classmethod
    def from_environment(cls) -> "PokeGraphClient":
        return cls(Neo4jSettings.from_environment())

    async def open(self) -> None:
        await self._connection.open()

    async def close(self) -> None:
        if self._owns_connection:
            await self._connection.close()

    async def verify_connectivity(self) -> None:
        await self._connection.verify_connectivity()

    async def __aenter__(self) -> "PokeGraphClient":
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def execute(self, query_id: str, **params: Any) -> QueryPage:
        spec = self._registry.get(query_id)
        bound = self._registry.bind(
            query_id,
            params,
            max_page_size=self._settings.max_page_size,
        )
        await self._assert_entities(spec.existence_checks, bound)
        started = time.monotonic()
        error_category: str | None = None
        rows: list[dict[str, Any]] | None = None
        try:
            records = await self._connection.execute_read(
                self._registry.cypher(query_id),
                bound,
                timeout_s=self._settings.query_timeout_s,
            )
            rows = records_to_dicts(records)
        except Exception as exc:
            error_category = type(exc).__name__
            raise
        finally:
            logger.info(
                "catalog_query query_id=%s duration_ms=%s row_count=%s error=%s",
                query_id,
                int((time.monotonic() - started) * 1000),
                None if rows is None else len(rows),
                error_category,
            )
        return QueryPage(
            query_id=query_id,
            rows=rows,
            skip=int(bound["skip"]) if bound.get("skip") is not None else 0,
            limit=int(bound["limit"]) if bound.get("limit") is not None else 0,
            context=_context_from_bound(bound),
            limitations=spec.limitations,
            data_complete=_page_data_complete(rows),
        )

    async def _run_unchecked(self, query_id: str, **params: Any) -> list[dict[str, Any]]:
        bound = self._registry.bind(
            query_id,
            params,
            max_page_size=self._settings.max_page_size,
        )
        records = await self._connection.execute_read(
            self._registry.cypher(query_id),
            bound,
            timeout_s=self._settings.query_timeout_s,
        )
        return records_to_dicts(records)

    async def _assert_entities(self, checks, bound: dict[str, Any]) -> None:
        for check in checks:
            value = bound.get(check.source_param)
            if value is None:
                continue
            rows = await self._run_unchecked(check.query_id, **{check.target_param: value})
            if not rows:
                raise EntityNotFoundError(check.entity, int(value))

    async def find_pokemon(self, name: str, *, skip: int | None = None, limit: int | None = None) -> QueryPage:
        return await self.execute(
            "discovery.find_pokemon_by_name",
            name=name,
            **_page(skip, limit),
        )

    async def find_species(self, name: str, *, skip: int | None = None, limit: int | None = None) -> QueryPage:
        return await self.execute(
            "discovery.find_species_by_name",
            name=name,
            **_page(skip, limit),
        )

    async def find_move(self, name: str, *, skip: int | None = None, limit: int | None = None) -> QueryPage:
        return await self.execute(
            "discovery.find_move_by_name",
            name=name,
            **_page(skip, limit),
        )

    async def find_location_areas(
        self,
        name: str,
        *,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "discovery.find_location_area_by_name",
            name=name,
            **_page(skip, limit),
        )

    async def list_regions(
        self,
        *,
        region_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "discovery.list_regions",
            region_id=region_id,
            **_page(skip, limit),
        )

    async def list_locations(
        self,
        *,
        region_id: int | None = None,
        location_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "discovery.list_locations",
            region_id=region_id,
            location_id=location_id,
            **_page(skip, limit),
        )

    async def list_location_areas(
        self,
        *,
        region_id: int | None = None,
        location_id: int | None = None,
        location_area_id: int | None = None,
        version_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "discovery.list_location_areas",
            region_id=region_id,
            location_id=location_id,
            location_area_id=location_area_id,
            version_id=version_id,
            **_page(skip, limit),
        )

    async def list_versions(self, *, skip: int | None = None, limit: int | None = None) -> QueryPage:
        return await self.execute("discovery.list_versions_with_data", **_page(skip, limit))

    async def list_version_groups(self, *, skip: int | None = None, limit: int | None = None) -> QueryPage:
        return await self.execute("discovery.list_version_groups_with_data", **_page(skip, limit))

    async def resolve_version_group(
        self,
        version_id: int,
        *,
        version_group_id: int | None = None,
    ) -> QueryPage:
        page = await self.execute(
            "discovery.resolve_version_group",
            version_id=version_id,
            version_group_id=version_group_id,
        )
        if version_group_id is not None and not page.rows:
            raise IncompatibleGameContextError(
                f"GameVersion {version_id} is not in VersionGroup {version_group_id}."
            )
        if page.rows:
            row = page.rows[0]
            return QueryPage(
                query_id=page.query_id,
                rows=page.rows,
                skip=page.skip,
                limit=page.limit,
                context=GameContext(
                    version_id=row.get("version_id"),
                    version_name=row.get("version_name"),
                    version_group_id=row.get("version_group_id"),
                    version_group_name=row.get("version_group_name"),
                ),
                limitations=page.limitations,
                data_complete=page.data_complete,
            )
        return page

    async def dataset_fingerprint(self) -> QueryPage:
        return await self.execute("discovery.dataset_fingerprint")

    async def pokemon_in_area(
        self,
        location_area_id: int,
        version_id: int,
        *,
        method_id: int | None = None,
        min_level: int | None = None,
        max_level: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self._with_version_context(
            await self.execute(
                "encounters.pokemon_in_area",
                location_area_id=location_area_id,
                version_id=version_id,
                method_id=method_id,
                min_level=min_level,
                max_level=max_level,
                **_page(skip, limit),
            )
        )

    async def locations_of_pokemon(
        self,
        pokemon_id: int,
        version_id: int,
        *,
        method_id: int | None = None,
        min_level: int | None = None,
        max_level: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self._with_version_context(
            await self.execute(
                "encounters.locations_of_pokemon",
                pokemon_id=pokemon_id,
                version_id=version_id,
                method_id=method_id,
                min_level=min_level,
                max_level=max_level,
                **_page(skip, limit),
            )
        )

    async def compare_versions(
        self,
        version_id_a: int,
        version_id_b: int,
        *,
        location_area_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "encounters.compare_versions",
            version_id_a=version_id_a,
            version_id_b=version_id_b,
            location_area_id=location_area_id,
            **_page(skip, limit),
        )

    async def learnset_for_pokemon(
        self,
        pokemon_id: int,
        *,
        version_id: int | None = None,
        version_group_id: int | None = None,
        learn_method_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        context = await self._resolve_learnset_context(version_id, version_group_id)
        page = await self.execute(
            "learnsets.learnset_for_pokemon",
            pokemon_id=pokemon_id,
            version_group_id=context.version_group_id,
            learn_method_id=learn_method_id,
            **_page(skip, limit),
        )
        return _replace_context(page, context)

    async def who_learns_move(
        self,
        move_id: int,
        *,
        version_id: int | None = None,
        version_group_id: int | None = None,
        learn_method_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        context = await self._resolve_learnset_context(version_id, version_group_id)
        page = await self.execute(
            "learnsets.who_learns_move",
            move_id=move_id,
            version_group_id=context.version_group_id,
            learn_method_id=learn_method_id,
            **_page(skip, limit),
        )
        return _replace_context(page, context)

    async def evolution_chain(
        self,
        species_id: int,
        *,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "evolutions.evolution_chain",
            species_id=species_id,
            **_page(skip, limit),
        )

    async def evolutions_from_species(
        self,
        species_id: int,
        *,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "evolutions.evolutions_from_species",
            species_id=species_id,
            **_page(skip, limit),
        )

    async def evolutions_to_species(
        self,
        species_id: int,
        *,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "evolutions.evolutions_to_species",
            species_id=species_id,
            **_page(skip, limit),
        )

    async def defensive_profile(
        self,
        pokemon_id: int,
        *,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        return await self.execute(
            "matchups.defensive_profile",
            pokemon_id=pokemon_id,
            **_page(skip, limit),
        )

    async def type_effectiveness(self, attacker_type_id: int, defender_pokemon_id: int) -> QueryPage:
        return await self.execute(
            "matchups.type_effectiveness",
            attacker_type_id=attacker_type_id,
            defender_pokemon_id=defender_pokemon_id,
        )

    async def offensive_coverage(
        self,
        pokemon_id: int,
        defender_pokemon_id: int,
        *,
        version_id: int | None = None,
        version_group_id: int | None = None,
        learn_method_id: int | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> QueryPage:
        if version_id is not None or version_group_id is not None or learn_method_id is not None:
            context = await self._resolve_learnset_context(version_id, version_group_id)
            page = await self.execute(
                "matchups.offensive_coverage_by_learnset",
                pokemon_id=pokemon_id,
                version_group_id=context.version_group_id,
                defender_pokemon_id=defender_pokemon_id,
                learn_method_id=learn_method_id,
                **_page(skip, limit),
            )
            return _replace_context(page, context)
        return await self.execute(
            "matchups.offensive_coverage_by_types",
            pokemon_id=pokemon_id,
            defender_pokemon_id=defender_pokemon_id,
            **_page(skip, limit),
        )

    async def _resolve_learnset_context(
        self,
        version_id: int | None,
        version_group_id: int | None,
    ) -> GameContext:
        if version_id is None and version_group_id is None:
            raise InvalidQueryParameterError(
                "Provide version_id and/or version_group_id for learnset queries."
            )
        if version_id is None:
            return GameContext(version_group_id=version_group_id)
        page = await self.resolve_version_group(version_id, version_group_id=version_group_id)
        if not page.rows:
            raise EntityNotFoundError("VersionGroup", version_id)
        return page.context

    async def _with_version_context(self, page: QueryPage) -> QueryPage:
        if not page.rows:
            return page
        row = page.rows[0]
        return _replace_context(
            page,
            GameContext(
                version_id=row.get("version_id"),
                version_name=row.get("version_name"),
                version_group_id=page.context.version_group_id,
                version_group_name=page.context.version_group_name,
            ),
        )


def _page(skip: int | None, limit: int | None) -> dict[str, int]:
    params: dict[str, int] = {}
    if skip is not None:
        params["skip"] = skip
    if limit is not None:
        params["limit"] = limit
    return params


def _context_from_bound(bound: dict[str, Any]) -> GameContext:
    return GameContext(
        version_id=bound.get("version_id"),
        version_group_id=bound.get("version_group_id"),
    )


def _replace_context(page: QueryPage, context: GameContext) -> QueryPage:
    return QueryPage(
        query_id=page.query_id,
        rows=page.rows,
        skip=page.skip,
        limit=page.limit,
        context=context,
        limitations=page.limitations,
        data_complete=page.data_complete,
    )


def _page_data_complete(rows: list[dict[str, Any]]) -> bool | None:
    flags = [row["data_complete"] for row in rows if "data_complete" in row]
    if not flags:
        return None
    return all(bool(flag) for flag in flags)
