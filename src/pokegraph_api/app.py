from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from pokegraph import PokeGraphClient
from pokegraph.errors import (
    EntityNotFoundError,
    GraphUnavailableError,
    IncompatibleGameContextError,
    InvalidQueryParameterError,
    QueryTimeoutError,
)

from .schemas import ErrorModel, HealthModel, QueryPageModel, page_to_model

DESCRIPTION = """
Read-only HTTP API over the PokéGraph Cypher catalog.

This is the same contract as `PokeGraphClient`. Use **Try it out** to run a query
against the connected Neo4j database. Empty `rows` means no stored match.
Matchups report stored type charts only — they are not generation-specific battle rules.

Recorded example IDs (HeartGold / SoulSilver): `pokemon_id=25`, `version_id=15`,
`version_group_id=10`, `location_area_id=184`, `move_id=85`, `species_id=25`,
`attacker_type_id=13`, `defender_pokemon_id=72`.
"""

SkipLimit = Annotated[int | None, Query(ge=0, description="Pagination offset or page size.")]


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.client = None
        application.state.startup_error = None
        try:
            client = PokeGraphClient.from_environment()
            await client.open()
            application.state.client = client
        except Exception as exc:  # noqa: BLE001 — docs stay up if Neo4j is down
            application.state.startup_error = str(exc)
        try:
            yield
        finally:
            client = getattr(application.state, "client", None)
            if client is not None:
                await client.close()

    application = FastAPI(
        title="PokéGraph Query API",
        version="0.1.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        servers=[{"url": "/", "description": "This server"}],
        openapi_tags=[
            {"name": "Health", "description": "API and Neo4j connectivity."},
            {"name": "Discovery", "description": "Resolve names and list stored coverage."},
            {"name": "Encounters", "description": "Recorded wild encounters by area, Pokémon, or game."},
            {"name": "Learnsets", "description": "Moves a Pokémon can learn in a version group."},
            {"name": "Evolutions", "description": "Stored EVOLVES_TO conditions (not game availability)."},
            {"name": "Matchups", "description": "Stored type charts only — not generation-specific battle rules."},
        ],
        swagger_ui_parameters={
            "tryItOutEnabled": True,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
            "persistAuthorization": True,
        },
    )

    @application.exception_handler(InvalidQueryParameterError)
    async def _invalid(_request: Request, exc: InvalidQueryParameterError):
        return _error(400, exc)

    @application.exception_handler(IncompatibleGameContextError)
    async def _incompatible(_request: Request, exc: IncompatibleGameContextError):
        return _error(400, exc)

    @application.exception_handler(EntityNotFoundError)
    async def _missing(_request: Request, exc: EntityNotFoundError):
        return _error(404, exc, entity=exc.entity, entity_id=exc.entity_id)

    @application.exception_handler(QueryTimeoutError)
    async def _timeout(_request: Request, exc: QueryTimeoutError):
        return _error(504, exc)

    @application.exception_handler(GraphUnavailableError)
    async def _unavailable(_request: Request, exc: GraphUnavailableError):
        return _error(503, exc)

    application.include_router(_routes())
    return application


def _error(
    status: int,
    exc: Exception,
    *,
    entity: str | None = None,
    entity_id: int | None = None,
):
    from fastapi.responses import JSONResponse

    payload = ErrorModel(
        error=type(exc).__name__,
        category=type(exc).__name__,
        detail=str(exc),
        entity=entity,
        entity_id=entity_id,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


def _client(request: Request) -> PokeGraphClient:
    client = getattr(request.app.state, "client", None)
    if client is None:
        detail = getattr(request.app.state, "startup_error", None) or "Neo4j is not connected."
        raise HTTPException(status_code=503, detail=detail)
    return client


Graph = Annotated[PokeGraphClient, Depends(_client)]


def _routes() -> APIRouter:
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @router.get(
        "/v1/health",
        tags=["Health"],
        response_model=HealthModel,
        summary="Check API and database connectivity",
    )
    async def health(request: Request) -> HealthModel:
        client = getattr(request.app.state, "client", None)
        if client is None:
            return HealthModel(
                status="degraded",
                database_ready=False,
                detail=getattr(request.app.state, "startup_error", None),
            )
        return HealthModel(status="ok", database_ready=True)

    @router.get(
        "/v1/discovery/pokemon",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Find Pokémon by name",
    )
    async def find_pokemon(
        graph: Graph,
        name: Annotated[str, Query(examples=["pikachu"])],
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.find_pokemon(name, skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/species",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Find species by name",
    )
    async def find_species(
        graph: Graph,
        name: Annotated[str, Query(examples=["pikachu"])],
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.find_species(name, skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/moves",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Find moves by name",
    )
    async def find_move(
        graph: Graph,
        name: Annotated[str, Query(examples=["thunderbolt"])],
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.find_move(name, skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/location-areas/search",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Find location areas by name",
    )
    async def find_location_areas(
        graph: Graph,
        name: Annotated[str, Query(examples=["pallet-town"])],
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.find_location_areas(name, skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/regions",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="List stored regions",
    )
    async def list_regions(
        graph: Graph,
        region_id: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.list_regions(region_id=region_id, skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/locations",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="List stored locations",
    )
    async def list_locations(
        graph: Graph,
        region_id: int | None = None,
        location_id: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.list_locations(
                region_id=region_id,
                location_id=location_id,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/discovery/location-areas",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="List stored location areas",
    )
    async def list_location_areas(
        graph: Graph,
        region_id: int | None = None,
        location_id: int | None = None,
        location_area_id: int | None = None,
        version_id: Annotated[int | None, Query(examples=[15])] = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.list_location_areas(
                region_id=region_id,
                location_id=location_id,
                location_area_id=location_area_id,
                version_id=version_id,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/discovery/versions",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="List games that have stored data",
    )
    async def list_versions(
        graph: Graph,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.list_versions(skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/version-groups",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="List version groups that have learnset data",
    )
    async def list_version_groups(
        graph: Graph,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.list_version_groups(skip=skip, limit=limit))

    @router.get(
        "/v1/discovery/version-groups/resolve",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Resolve GameVersion to VersionGroup",
    )
    async def resolve_version_group(
        graph: Graph,
        version_id: Annotated[int, Query(examples=[15])],
        version_group_id: Annotated[int | None, Query(examples=[10])] = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.resolve_version_group(version_id, version_group_id=version_group_id)
        )

    @router.get(
        "/v1/discovery/fingerprint",
        tags=["Discovery"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Dataset fingerprint counts",
    )
    async def dataset_fingerprint(graph: Graph) -> QueryPageModel:
        return page_to_model(await graph.dataset_fingerprint())

    @router.get(
        "/v1/encounters/in-area",
        tags=["Encounters"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Pokémon recorded in a location area and game",
    )
    async def pokemon_in_area(
        graph: Graph,
        location_area_id: Annotated[int, Query(examples=[184])],
        version_id: Annotated[int, Query(examples=[15])],
        method_id: int | None = None,
        min_level: Annotated[int | None, Query(examples=[10])] = None,
        max_level: Annotated[int | None, Query(examples=[20])] = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.pokemon_in_area(
                location_area_id,
                version_id,
                method_id=method_id,
                min_level=min_level,
                max_level=max_level,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/encounters/of-pokemon",
        tags=["Encounters"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Locations recorded for a Pokémon in a game",
    )
    async def locations_of_pokemon(
        graph: Graph,
        pokemon_id: Annotated[int, Query(examples=[25])],
        version_id: Annotated[int, Query(examples=[15])],
        method_id: int | None = None,
        min_level: int | None = None,
        max_level: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.locations_of_pokemon(
                pokemon_id,
                version_id,
                method_id=method_id,
                min_level=min_level,
                max_level=max_level,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/encounters/compare",
        tags=["Encounters"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Compare encounter membership between two games",
    )
    async def compare_versions(
        graph: Graph,
        version_id_a: Annotated[int, Query(examples=[15])],
        version_id_b: Annotated[int, Query(examples=[16])],
        location_area_id: Annotated[int | None, Query(examples=[184])] = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.compare_versions(
                version_id_a,
                version_id_b,
                location_area_id=location_area_id,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/learnsets/pokemon/{pokemon_id}",
        tags=["Learnsets"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Learnset entries for a Pokémon",
    )
    async def learnset_for_pokemon(
        graph: Graph,
        pokemon_id: int,
        version_id: Annotated[int | None, Query(examples=[15])] = None,
        version_group_id: Annotated[int | None, Query(examples=[10])] = None,
        learn_method_id: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.learnset_for_pokemon(
                pokemon_id,
                version_id=version_id,
                version_group_id=version_group_id,
                learn_method_id=learn_method_id,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/learnsets/moves/{move_id}",
        tags=["Learnsets"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Who learns a move in a version group",
    )
    async def who_learns_move(
        graph: Graph,
        move_id: int,
        version_id: Annotated[int | None, Query(examples=[15])] = None,
        version_group_id: Annotated[int | None, Query(examples=[10])] = None,
        learn_method_id: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.who_learns_move(
                move_id,
                version_id=version_id,
                version_group_id=version_group_id,
                learn_method_id=learn_method_id,
                skip=skip,
                limit=limit,
            )
        )

    @router.get(
        "/v1/evolutions/chain",
        tags=["Evolutions"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Evolution chain for a species",
    )
    async def evolution_chain(
        graph: Graph,
        species_id: Annotated[int, Query(examples=[25])],
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.evolution_chain(species_id, skip=skip, limit=limit))

    @router.get(
        "/v1/evolutions/from/{species_id}",
        tags=["Evolutions"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Evolutions starting from a species",
    )
    async def evolutions_from_species(
        graph: Graph,
        species_id: int,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.evolutions_from_species(species_id, skip=skip, limit=limit))

    @router.get(
        "/v1/evolutions/to/{species_id}",
        tags=["Evolutions"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Evolutions arriving at a species",
    )
    async def evolutions_to_species(
        graph: Graph,
        species_id: int,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.evolutions_to_species(species_id, skip=skip, limit=limit))

    @router.get(
        "/v1/matchups/defensive/{pokemon_id}",
        tags=["Matchups"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Defensive type profile",
    )
    async def defensive_profile(
        graph: Graph,
        pokemon_id: int,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(await graph.defensive_profile(pokemon_id, skip=skip, limit=limit))

    @router.get(
        "/v1/matchups/effectiveness",
        tags=["Matchups"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Type effectiveness against a Pokémon",
    )
    async def type_effectiveness(
        graph: Graph,
        attacker_type_id: Annotated[int, Query(examples=[13])],
        defender_pokemon_id: Annotated[int, Query(examples=[72])],
    ) -> QueryPageModel:
        return page_to_model(await graph.type_effectiveness(attacker_type_id, defender_pokemon_id))

    @router.get(
        "/v1/matchups/coverage",
        tags=["Matchups"],
        response_model=QueryPageModel,
        responses=_error_responses(),
        summary="Offensive coverage by types or learnset",
    )
    async def offensive_coverage(
        graph: Graph,
        pokemon_id: Annotated[int, Query(examples=[25])],
        defender_pokemon_id: Annotated[int, Query(examples=[72])],
        version_id: Annotated[int | None, Query(examples=[15])] = None,
        version_group_id: int | None = None,
        learn_method_id: int | None = None,
        skip: SkipLimit = None,
        limit: SkipLimit = None,
    ) -> QueryPageModel:
        return page_to_model(
            await graph.offensive_coverage(
                pokemon_id,
                defender_pokemon_id,
                version_id=version_id,
                version_group_id=version_group_id,
                learn_method_id=learn_method_id,
                skip=skip,
                limit=limit,
            )
        )

    return router


def _error_responses() -> dict[int | str, dict[str, Any]]:
    return {
        400: {"model": ErrorModel, "description": "Invalid parameters or incompatible game context"},
        404: {"model": ErrorModel, "description": "Required entity id was not found"},
        503: {"model": ErrorModel, "description": "Database unavailable"},
        504: {"model": ErrorModel, "description": "Query timed out"},
    }


app = create_app()
