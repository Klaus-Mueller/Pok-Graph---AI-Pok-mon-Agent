from __future__ import annotations

from typing import Any

from pokegraph.sources.convert import named_ref_from_dict, named_ref_to_dict, provenance_from_dict, provenance_to_dict
from pokegraph.sources.models import (
    Ability,
    EncounterDetail,
    EncounterVersionDetail,
    EvolutionChain,
    EvolutionDetail,
    EvolutionLink,
    GameVersion,
    Item,
    Location,
    LocationArea,
    LocationAreaEncounter,
    Move,
    Pokemon,
    PokemonAbilitySlot,
    PokemonMoveEntry,
    PokemonSpecies,
    PokemonTypeSlot,
    Type,
    TypeRelations,
    VersionGroup,
    VersionGroupDetail,
)


def pokemon_to_dict(model: Pokemon) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "base_experience": model.base_experience,
        "height": model.height,
        "weight": model.weight,
        "is_default": model.is_default,
        "species": named_ref_to_dict(model.species),
        "types": [{"type": named_ref_to_dict(slot.type), "slot": slot.slot} for slot in model.types],
        "abilities": [
            {
                "ability": named_ref_to_dict(slot.ability),
                "slot": slot.slot,
                "is_hidden": slot.is_hidden,
            }
            for slot in model.abilities
        ],
        "moves": [
            {
                "move": named_ref_to_dict(entry.move),
                "version_group_details": [
                    {
                        "version_group": named_ref_to_dict(detail.version_group),
                        "move_learn_method": named_ref_to_dict(detail.move_learn_method),
                        "level_learned_at": detail.level_learned_at,
                        "order": detail.order,
                    }
                    for detail in entry.version_group_details
                ],
            }
            for entry in model.moves
        ],
        "provenance": provenance_to_dict(model.provenance),
    }


def pokemon_from_dict(raw: dict[str, Any]) -> Pokemon:
    return Pokemon(
        id=int(raw["id"]),
        name=raw["name"],
        base_experience=raw.get("base_experience"),
        height=int(raw["height"]),
        weight=int(raw["weight"]),
        is_default=bool(raw["is_default"]),
        species=named_ref_from_dict(raw["species"]),  # type: ignore[arg-type]
        types=tuple(
            PokemonTypeSlot(type=named_ref_from_dict(item["type"]), slot=int(item["slot"]))  # type: ignore[arg-type]
            for item in raw.get("types") or []
        ),
        abilities=tuple(
            PokemonAbilitySlot(
                ability=named_ref_from_dict(item["ability"]),  # type: ignore[arg-type]
                slot=int(item["slot"]),
                is_hidden=bool(item["is_hidden"]),
            )
            for item in raw.get("abilities") or []
        ),
        moves=tuple(
            PokemonMoveEntry(
                move=named_ref_from_dict(item["move"]),  # type: ignore[arg-type]
                version_group_details=tuple(
                    VersionGroupDetail(
                        version_group=named_ref_from_dict(detail["version_group"]),  # type: ignore[arg-type]
                        move_learn_method=named_ref_from_dict(detail["move_learn_method"]),  # type: ignore[arg-type]
                        level_learned_at=int(detail["level_learned_at"]),
                        order=detail.get("order"),
                    )
                    for detail in item.get("version_group_details") or []
                ),
            )
            for item in raw.get("moves") or []
        ),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def species_to_dict(model: PokemonSpecies) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "is_legendary": model.is_legendary,
        "is_mythical": model.is_mythical,
        "generation": model.generation,
        "evolution_chain": named_ref_to_dict(model.evolution_chain),
        "provenance": provenance_to_dict(model.provenance),
    }


def species_from_dict(raw: dict[str, Any]) -> PokemonSpecies:
    return PokemonSpecies(
        id=int(raw["id"]),
        name=raw["name"],
        is_legendary=bool(raw["is_legendary"]),
        is_mythical=bool(raw["is_mythical"]),
        generation=raw.get("generation") or "",
        evolution_chain=named_ref_from_dict(raw.get("evolution_chain")),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def move_to_dict(model: Move) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "power": model.power,
        "accuracy": model.accuracy,
        "pp": model.pp,
        "priority": model.priority,
        "type": named_ref_to_dict(model.type),
        "damage_class": model.damage_class,
        "effect_chance": model.effect_chance,
        "effect": model.effect,
        "short_effect": model.short_effect,
        "target": model.target,
        "ailment": model.ailment,
        "ailment_chance": model.ailment_chance,
        "flinch_chance": model.flinch_chance,
        "stat_chance": model.stat_chance,
        "drain": model.drain,
        "healing": model.healing,
        "min_hits": model.min_hits,
        "max_hits": model.max_hits,
        "min_turns": model.min_turns,
        "max_turns": model.max_turns,
        "contest_type": model.contest_type,
        "contest_effect_id": model.contest_effect_id,
        "provenance": provenance_to_dict(model.provenance),
    }


def move_from_dict(raw: dict[str, Any]) -> Move:
    return Move(
        id=int(raw["id"]),
        name=raw["name"],
        power=raw.get("power"),
        accuracy=raw.get("accuracy"),
        pp=raw.get("pp"),
        priority=raw.get("priority"),
        type=named_ref_from_dict(raw.get("type")),
        damage_class=raw.get("damage_class") or "",
        effect_chance=raw.get("effect_chance"),
        effect=raw.get("effect") or "",
        short_effect=raw.get("short_effect") or "",
        target=raw.get("target") or "",
        ailment=raw.get("ailment") or "",
        ailment_chance=raw.get("ailment_chance"),
        flinch_chance=raw.get("flinch_chance"),
        stat_chance=raw.get("stat_chance"),
        drain=raw.get("drain"),
        healing=raw.get("healing"),
        min_hits=raw.get("min_hits"),
        max_hits=raw.get("max_hits"),
        min_turns=raw.get("min_turns"),
        max_turns=raw.get("max_turns"),
        contest_type=raw.get("contest_type") or "",
        contest_effect_id=raw.get("contest_effect_id"),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def ability_to_dict(model: Ability) -> dict[str, Any]:
    return {"id": model.id, "name": model.name, "provenance": provenance_to_dict(model.provenance)}


def ability_from_dict(raw: dict[str, Any]) -> Ability:
    return Ability(id=int(raw["id"]), name=raw["name"], provenance=provenance_from_dict(raw["provenance"]))


def type_to_dict(model: Type) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "damage_relations": {
            "double_damage_to": [named_ref_to_dict(ref) for ref in model.damage_relations.double_damage_to],
            "half_damage_to": [named_ref_to_dict(ref) for ref in model.damage_relations.half_damage_to],
            "no_damage_to": [named_ref_to_dict(ref) for ref in model.damage_relations.no_damage_to],
        },
        "provenance": provenance_to_dict(model.provenance),
    }


def type_from_dict(raw: dict[str, Any]) -> Type:
    relations = raw.get("damage_relations") or {}
    return Type(
        id=int(raw["id"]),
        name=raw["name"],
        damage_relations=TypeRelations(
            double_damage_to=_refs(relations.get("double_damage_to")),
            half_damage_to=_refs(relations.get("half_damage_to")),
            no_damage_to=_refs(relations.get("no_damage_to")),
        ),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def _refs(raw: Any) -> tuple:
    return tuple(named_ref_from_dict(item) for item in raw or [] if item is not None)


def location_area_to_dict(model: LocationArea) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "location": named_ref_to_dict(model.location),
        "provenance": provenance_to_dict(model.provenance),
    }


def location_area_from_dict(raw: dict[str, Any]) -> LocationArea:
    return LocationArea(
        id=int(raw["id"]),
        name=raw["name"],
        location=named_ref_from_dict(raw["location"]),  # type: ignore[arg-type]
        provenance=provenance_from_dict(raw["provenance"]),
    )


def location_to_dict(model: Location) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "region": named_ref_to_dict(model.region),
        "provenance": provenance_to_dict(model.provenance),
    }


def location_from_dict(raw: dict[str, Any]) -> Location:
    return Location(
        id=int(raw["id"]),
        name=raw["name"],
        region=named_ref_from_dict(raw.get("region")),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def region_to_dict(model: Region) -> dict[str, Any]:
    return {"id": model.id, "name": model.name, "provenance": provenance_to_dict(model.provenance)}


def region_from_dict(raw: dict[str, Any]) -> Region:
    return Region(id=int(raw["id"]), name=raw["name"], provenance=provenance_from_dict(raw["provenance"]))


def version_to_dict(model: GameVersion) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "version_group": named_ref_to_dict(model.version_group),
        "provenance": provenance_to_dict(model.provenance),
    }


def version_from_dict(raw: dict[str, Any]) -> GameVersion:
    return GameVersion(
        id=int(raw["id"]),
        name=raw["name"],
        version_group=named_ref_from_dict(raw.get("version_group")),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def version_group_to_dict(model: VersionGroup) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "regions": [named_ref_to_dict(ref) for ref in model.regions],
        "provenance": provenance_to_dict(model.provenance),
    }


def version_group_from_dict(raw: dict[str, Any]) -> VersionGroup:
    return VersionGroup(
        id=int(raw["id"]),
        name=raw["name"],
        regions=_refs(raw.get("regions")),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def item_to_dict(model: Item) -> dict[str, Any]:
    return {"id": model.id, "name": model.name, "provenance": provenance_to_dict(model.provenance)}


def item_from_dict(raw: dict[str, Any]) -> Item:
    return Item(id=int(raw["id"]), name=raw["name"], provenance=provenance_from_dict(raw["provenance"]))


def encounters_to_dict(rows: list[LocationAreaEncounter]) -> list[dict[str, Any]]:
    return [
        {
            "location_area": named_ref_to_dict(row.location_area),
            "version_details": [
                {
                    "version": named_ref_to_dict(detail.version),
                    "encounter_details": [
                        {
                            "method": named_ref_to_dict(item.method),
                            "min_level": item.min_level,
                            "max_level": item.max_level,
                            "chance": item.chance,
                            "condition_values": [named_ref_to_dict(ref) for ref in item.condition_values],
                        }
                        for item in detail.encounter_details
                    ],
                }
                for detail in row.version_details
            ],
        }
        for row in rows
    ]


def encounters_from_dict(raw: list[dict[str, Any]]) -> list[LocationAreaEncounter]:
    return [
        LocationAreaEncounter(
            location_area=named_ref_from_dict(row["location_area"]),  # type: ignore[arg-type]
            version_details=tuple(
                EncounterVersionDetail(
                    version=named_ref_from_dict(detail["version"]),  # type: ignore[arg-type]
                    encounter_details=tuple(
                        EncounterDetail(
                            method=named_ref_from_dict(item["method"]),  # type: ignore[arg-type]
                            min_level=int(item["min_level"]),
                            max_level=int(item["max_level"]),
                            chance=int(item["chance"]),
                            condition_values=_refs(item.get("condition_values")),
                        )
                        for item in detail.get("encounter_details") or []
                    ),
                )
                for detail in row.get("version_details") or []
            ),
        )
        for row in raw
    ]


def evolution_chain_to_dict(model: EvolutionChain) -> dict[str, Any]:
    return {
        "id": model.id,
        "chain": _link_to_dict(model.chain),
        "provenance": provenance_to_dict(model.provenance),
    }


def evolution_chain_from_dict(raw: dict[str, Any]) -> EvolutionChain:
    return EvolutionChain(
        id=int(raw["id"]),
        chain=_link_from_dict(raw["chain"]),
        provenance=provenance_from_dict(raw["provenance"]),
    )


def _link_to_dict(link: EvolutionLink) -> dict[str, Any]:
    return {
        "species": named_ref_to_dict(link.species),
        "is_baby": link.is_baby,
        "evolution_details": [_detail_to_dict(detail) for detail in link.evolution_details],
        "evolves_to": [_link_to_dict(child) for child in link.evolves_to],
    }


def _link_from_dict(raw: dict[str, Any]) -> EvolutionLink:
    return EvolutionLink(
        species=named_ref_from_dict(raw["species"]),  # type: ignore[arg-type]
        is_baby=bool(raw.get("is_baby", False)),
        evolution_details=tuple(_detail_from_dict(item) for item in raw.get("evolution_details") or []),
        evolves_to=tuple(_link_from_dict(item) for item in raw.get("evolves_to") or []),
    )


def _detail_to_dict(detail: EvolutionDetail) -> dict[str, Any]:
    return {
        "trigger": named_ref_to_dict(detail.trigger),
        "item": named_ref_to_dict(detail.item),
        "held_item": named_ref_to_dict(detail.held_item),
        "known_move": named_ref_to_dict(detail.known_move),
        "known_move_type": named_ref_to_dict(detail.known_move_type),
        "location": named_ref_to_dict(detail.location),
        "party_species": named_ref_to_dict(detail.party_species),
        "trade_species": named_ref_to_dict(detail.trade_species),
        "region": named_ref_to_dict(detail.region),
        "version_group": named_ref_to_dict(detail.version_group),
        "min_level": detail.min_level,
        "min_happiness": detail.min_happiness,
        "min_beauty": detail.min_beauty,
        "min_affection": detail.min_affection,
        "time_of_day": detail.time_of_day,
        "needs_overworld_rain": detail.needs_overworld_rain,
        "turn_upside_down": detail.turn_upside_down,
        "relative_physical_stats": detail.relative_physical_stats,
        "gender": detail.gender,
        "is_default": detail.is_default,
    }


def _detail_from_dict(raw: dict[str, Any]) -> EvolutionDetail:
    return EvolutionDetail(
        trigger=named_ref_from_dict(raw.get("trigger")),
        item=named_ref_from_dict(raw.get("item")),
        held_item=named_ref_from_dict(raw.get("held_item")),
        known_move=named_ref_from_dict(raw.get("known_move")),
        known_move_type=named_ref_from_dict(raw.get("known_move_type")),
        location=named_ref_from_dict(raw.get("location")),
        party_species=named_ref_from_dict(raw.get("party_species")),
        trade_species=named_ref_from_dict(raw.get("trade_species")),
        region=named_ref_from_dict(raw.get("region")),
        version_group=named_ref_from_dict(raw.get("version_group")),
        min_level=raw.get("min_level"),
        min_happiness=raw.get("min_happiness"),
        min_beauty=raw.get("min_beauty"),
        min_affection=raw.get("min_affection"),
        time_of_day=raw.get("time_of_day") or "",
        needs_overworld_rain=bool(raw.get("needs_overworld_rain", False)),
        turn_upside_down=bool(raw.get("turn_upside_down", False)),
        relative_physical_stats=raw.get("relative_physical_stats"),
        gender=raw.get("gender"),
        is_default=bool(raw.get("is_default", False)),
    )
