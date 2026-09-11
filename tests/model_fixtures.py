from __future__ import annotations

from datetime import datetime, timezone

from pokegraph.sources.models import (
    Move,
    NamedRef,
    Pokemon,
    PokemonMoveEntry,
    Provenance,
    VersionGroupDetail,
)


def provenance(**overrides: object) -> Provenance:
    values: dict[str, object] = {
        "source_url": "https://pokeapi.co/api/v2/pokemon/25/",
        "retrieved_at": datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
        "source_version": "unavailable",
        "adapter_version": "0.1.0",
    }
    values.update(overrides)
    return Provenance(**values)  # type: ignore[arg-type]


def named(name: str, resource_id: int | None, url: str | None = None) -> NamedRef:
    if url is None:
        url = f"https://pokeapi.co/api/v2/resource/{resource_id}/" if resource_id is not None else ""
    return NamedRef(id=resource_id, name=name, url=url)


def detail(
    *,
    version_group: tuple[str, int],
    method: tuple[str, int],
    level: int,
    order: int | None,
) -> VersionGroupDetail:
    return VersionGroupDetail(
        version_group=named(*version_group),
        move_learn_method=named(*method),
        level_learned_at=level,
        order=order,
    )


def pokemon_with_moves(moves: list[PokemonMoveEntry], **overrides: object) -> Pokemon:
    values: dict[str, object] = {
        "id": 25,
        "name": "pikachu",
        "base_experience": 112,
        "height": 4,
        "weight": 60,
        "is_default": True,
        "species": named("pikachu", 25),
        "types": (),
        "abilities": (),
        "moves": tuple(moves),
        "provenance": provenance(),
    }
    values.update(overrides)
    return Pokemon(**values)  # type: ignore[arg-type]


def base_move(**overrides: object) -> Move:
    values: dict[str, object] = {
        "id": 1,
        "name": "pound",
        "power": 40,
        "accuracy": 100,
        "pp": 35,
        "priority": 0,
        "type": named("normal", 1),
        "damage_class": "physical",
        "effect_chance": None,
        "effect": "",
        "short_effect": "",
        "target": "selected-pokemon",
        "ailment": "",
        "ailment_chance": None,
        "flinch_chance": None,
        "stat_chance": None,
        "drain": None,
        "healing": None,
        "min_hits": None,
        "max_hits": None,
        "min_turns": None,
        "max_turns": None,
        "contest_type": "",
        "contest_effect_id": None,
        "provenance": provenance(source_url="https://pokeapi.co/api/v2/move/1/"),
    }
    values.update(overrides)
    return Move(**values)  # type: ignore[arg-type]
