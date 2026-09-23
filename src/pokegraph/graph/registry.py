from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pokegraph.config import DEFAULT_MAX_PAGE_SIZE
from pokegraph.errors import InvalidQueryParameterError
from pokegraph.graph.catalog import catalog_file, load_cypher

_PARAM_RE = re.compile(r"\$(\w+)\s*\((\w+)\)")
_LISTING_DEFAULTS = {"skip": 0, "limit": 50}

QUERY_PATHS: dict[str, str] = {
    "battles.team_for_battle": "battles/team_for_battle.cypher",
    "battles.context_for_battle": "battles/context_for_battle.cypher",
    "battles.list_battles": "battles/list_battles.cypher",
    "battles.regional_candidates_for_battle": "battles/regional_candidates_for_battle.cypher",
    "encounters.pokemon_in_region": "encounters/pokemon_in_region.cypher",
    "discovery.dataset_fingerprint": "discovery/dataset_fingerprint.cypher",
    "discovery.find_location_area_by_name": "discovery/find_location_area_by_name.cypher",
    "discovery.find_move_by_name": "discovery/find_move_by_name.cypher",
    "discovery.find_pokemon_by_name": "discovery/find_pokemon_by_name.cypher",
    "discovery.find_species_by_name": "discovery/find_species_by_name.cypher",
    "discovery.get_location_area": "discovery/get_location_area.cypher",
    "discovery.get_move": "discovery/get_move.cypher",
    "discovery.get_pokemon": "discovery/get_pokemon.cypher",
    "discovery.get_species": "discovery/get_species.cypher",
    "discovery.get_type": "discovery/get_type.cypher",
    "discovery.get_version": "discovery/get_version.cypher",
    "discovery.get_version_group": "discovery/get_version_group.cypher",
    "discovery.list_location_areas": "discovery/list_location_areas.cypher",
    "discovery.list_locations": "discovery/list_locations.cypher",
    "discovery.list_regions": "discovery/list_regions.cypher",
    "discovery.list_version_groups_with_data": "discovery/list_version_groups_with_data.cypher",
    "discovery.list_versions_with_data": "discovery/list_versions_with_data.cypher",
    "discovery.resolve_version_group": "discovery/resolve_version_group.cypher",
    "encounters.compare_versions": "encounters/compare_versions.cypher",
    "encounters.locations_of_pokemon": "encounters/locations_of_pokemon.cypher",
    "encounters.pokemon_in_area": "encounters/pokemon_in_area.cypher",
    "evolutions.evolution_chain": "evolutions/evolution_chain.cypher",
    "evolutions.evolutions_from_species": "evolutions/evolutions_from_species.cypher",
    "evolutions.evolutions_to_species": "evolutions/evolutions_to_species.cypher",
    "learnsets.learnset_for_pokemon": "learnsets/learnset_for_pokemon.cypher",
    "learnsets.who_learns_move": "learnsets/who_learns_move.cypher",
    "matchups.defensive_profile": "matchups/defensive_profile.cypher",
    "matchups.offensive_coverage_by_learnset": "matchups/offensive_coverage_by_learnset.cypher",
    "matchups.offensive_coverage_by_types": "matchups/offensive_coverage_by_types.cypher",
    "matchups.type_effectiveness": "matchups/type_effectiveness.cypher",
}

ENTITY_LABELS = {
    "pokemon_id": "Pokemon",
    "species_id": "PokemonSpecies",
    "starter_species_id": "PokemonSpecies",
    "location_area_id": "LocationArea",
    "move_id": "Move",
    "version_id": "GameVersion",
    "version_id_a": "GameVersion",
    "version_id_b": "GameVersion",
    "version_group_id": "VersionGroup",
    "type_id": "Type",
    "attacker_type_id": "Type",
    "defender_pokemon_id": "Pokemon",
}


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: str
    required: bool
    default: Any = None


@dataclass(frozen=True)
class ExistenceCheck:
    source_param: str
    query_id: str
    target_param: str
    entity: str


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    relative_path: str
    params: tuple[ParamSpec, ...]
    columns: tuple[str, ...]
    limitations: tuple[str, ...]
    existence_checks: tuple[ExistenceCheck, ...] = ()

    def param_map(self) -> dict[str, ParamSpec]:
        return {param.name: param for param in self.params}


def _parse_header_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("//"):
            break
        body = stripped[2:].strip()
        if ":" not in body:
            continue
        key, value = body.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_param_list(raw: str, *, required: bool) -> tuple[ParamSpec, ...]:
    if raw in {"", "(none)", "none"}:
        return ()
    params: list[ParamSpec] = []
    for part in raw.split(","):
        match = _PARAM_RE.search(part)
        if match is None:
            continue
        name, typ = match.group(1), match.group(2)
        default = None if required else _LISTING_DEFAULTS.get(name)
        params.append(ParamSpec(name=name, type=typ, required=required, default=default))
    return tuple(params)


def _parse_columns(raw: str) -> tuple[str, ...]:
    if raw in {"", "(none)", "none"}:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def parse_query_header(text: str) -> tuple[tuple[ParamSpec, ...], tuple[str, ...], tuple[str, ...]]:
    fields = _parse_header_fields(text)
    required = _parse_param_list(fields.get("required", "(none)"), required=True)
    optional = _parse_param_list(fields.get("optional", "(none)"), required=False)
    columns = _parse_columns(fields.get("returns", ""))
    limitation = fields.get("does_not", "").strip()
    limitations = (limitation,) if limitation else ()
    return required + optional, columns, limitations


def _existence(*pairs: tuple[str, str, str]) -> tuple[ExistenceCheck, ...]:
    checks: list[ExistenceCheck] = []
    for source_param, query_id, target_param in pairs:
        checks.append(
            ExistenceCheck(
                source_param=source_param,
                query_id=query_id,
                target_param=target_param,
                entity=ENTITY_LABELS[source_param],
            )
        )
    return tuple(checks)


QUERY_EXTRAS: dict[str, tuple[ExistenceCheck, ...]] = {
    "discovery.resolve_version_group": _existence(
        ("version_id", "discovery.get_version", "version_id"),
    ),
    "encounters.compare_versions": _existence(
        ("version_id_a", "discovery.get_version", "version_id"),
        ("version_id_b", "discovery.get_version", "version_id"),
    ),
    "encounters.locations_of_pokemon": _existence(
        ("pokemon_id", "discovery.get_pokemon", "pokemon_id"),
        ("version_id", "discovery.get_version", "version_id"),
    ),
    "encounters.pokemon_in_area": _existence(
        ("location_area_id", "discovery.get_location_area", "location_area_id"),
        ("version_id", "discovery.get_version", "version_id"),
    ),
    "evolutions.evolution_chain": _existence(
        ("species_id", "discovery.get_species", "species_id"),
    ),
    "evolutions.evolutions_from_species": _existence(
        ("species_id", "discovery.get_species", "species_id"),
    ),
    "evolutions.evolutions_to_species": _existence(
        ("species_id", "discovery.get_species", "species_id"),
    ),
    "learnsets.learnset_for_pokemon": _existence(
        ("pokemon_id", "discovery.get_pokemon", "pokemon_id"),
        ("version_group_id", "discovery.get_version_group", "version_group_id"),
    ),
    "learnsets.who_learns_move": _existence(
        ("move_id", "discovery.get_move", "move_id"),
        ("version_group_id", "discovery.get_version_group", "version_group_id"),
    ),
    "matchups.defensive_profile": _existence(
        ("pokemon_id", "discovery.get_pokemon", "pokemon_id"),
    ),
    "matchups.offensive_coverage_by_learnset": _existence(
        ("pokemon_id", "discovery.get_pokemon", "pokemon_id"),
        ("version_group_id", "discovery.get_version_group", "version_group_id"),
        ("defender_pokemon_id", "discovery.get_pokemon", "pokemon_id"),
    ),
    "matchups.offensive_coverage_by_types": _existence(
        ("pokemon_id", "discovery.get_pokemon", "pokemon_id"),
        ("defender_pokemon_id", "discovery.get_pokemon", "pokemon_id"),
    ),
    "battles.context_for_battle": _existence(("version_id", "discovery.get_version", "version_id")),
    "battles.team_for_battle": _existence(
        ("version_id", "discovery.get_version", "version_id"),
        ("starter_species_id", "discovery.get_species", "species_id"),
    ),
    "battles.regional_candidates_for_battle": _existence(
        ("version_id", "discovery.get_version", "version_id"),
        ("starter_species_id", "discovery.get_species", "species_id"),
    ),
    "encounters.pokemon_in_region": _existence(
        ("version_id", "discovery.get_version", "version_id"),
    ),
    "matchups.type_effectiveness": _existence(
        ("attacker_type_id", "discovery.get_type", "type_id"),
        ("defender_pokemon_id", "discovery.get_pokemon", "pokemon_id"),
    ),
}


@dataclass
class QueryRegistry:
    specs: dict[str, QuerySpec] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "QueryRegistry":
        specs: dict[str, QuerySpec] = {}
        for query_id, relative_path in QUERY_PATHS.items():
            text = catalog_file(relative_path).read_text(encoding="utf-8")
            params, columns, limitations = parse_query_header(text)
            specs[query_id] = QuerySpec(
                query_id=query_id,
                relative_path=relative_path,
                params=params,
                columns=columns,
                limitations=limitations,
                existence_checks=QUERY_EXTRAS.get(query_id, ()),
            )
        return cls(specs)

    def get(self, query_id: str) -> QuerySpec:
        try:
            return self.specs[query_id]
        except KeyError as exc:
            raise InvalidQueryParameterError(f"Unknown catalog query {query_id}.") from exc

    def cypher(self, query_id: str) -> str:
        return load_cypher(self.get(query_id).relative_path)

    def bind(
        self,
        query_id: str,
        raw: dict[str, Any],
        *,
        max_page_size: int = DEFAULT_MAX_PAGE_SIZE,
    ) -> dict[str, Any]:
        spec = self.get(query_id)
        known = spec.param_map()
        unknown = sorted(set(raw) - set(known))
        if unknown:
            raise InvalidQueryParameterError(
                f"Unknown parameter(s) for {query_id}: {', '.join(unknown)}."
            )
        bound: dict[str, Any] = {}
        for param in spec.params:
            if param.name in raw:
                value = raw[param.name]
            elif param.required:
                raise InvalidQueryParameterError(
                    f"Missing required parameter {param.name} for {query_id}."
                )
            else:
                value = param.default
            bound[param.name] = _coerce(
                query_id,
                param,
                value,
                max_page_size=max_page_size,
                explicit=param.name in raw,
            )
        _validate_ranges(query_id, bound)
        return bound


def _coerce(
    query_id: str,
    param: ParamSpec,
    value: Any,
    *,
    max_page_size: int,
    explicit: bool,
) -> Any:
    if value is None:
        if param.required:
            raise InvalidQueryParameterError(
                f"Parameter {param.name} is required for {query_id}."
            )
        return None
    if param.type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidQueryParameterError(
                f"Parameter {param.name} for {query_id} must be an integer."
            )
        if param.name in {"skip", "limit"} and value < 0:
            raise InvalidQueryParameterError(
                f"Parameter {param.name} for {query_id} must be >= 0."
            )
        if param.name == "limit" and value > max_page_size:
            if not explicit:
                return max_page_size
            raise InvalidQueryParameterError(
                f"Parameter limit for {query_id} must be <= {max_page_size}."
            )
        return value
    if param.type == "string":
        if not isinstance(value, str):
            raise InvalidQueryParameterError(
                f"Parameter {param.name} for {query_id} must be a string."
            )
        if param.required and value.strip() == "":
            raise InvalidQueryParameterError(
                f"Parameter {param.name} for {query_id} must not be empty."
            )
        return value
    raise InvalidQueryParameterError(
        f"Unsupported parameter type {param.type} for {param.name}."
    )


def _validate_ranges(query_id: str, bound: dict[str, Any]) -> None:
    minimum = bound.get("min_level")
    maximum = bound.get("max_level")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise InvalidQueryParameterError(
            f"min_level cannot be greater than max_level for {query_id}."
        )
