from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from pokegraph.errors import SourceNormalizationError
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
    NamedRef,
    Pokemon,
    PokemonAbilitySlot,
    PokemonMoveEntry,
    PokemonSpecies,
    PokemonTypeSlot,
    Provenance,
    Region,
    Type,
    TypeRelations,
    VersionGroup,
    VersionGroupDetail,
)

_ID_IN_URL = re.compile(r"/(\d+)/?$")


def resource_id(resource: Any) -> int | None:
    if resource is None:
        return None
    raw_id = getattr(resource, "id", None)
    if isinstance(raw_id, int) and not isinstance(raw_id, bool):
        return raw_id
    url = getattr(resource, "url", "") or ""
    match = _ID_IN_URL.search(url)
    return int(match.group(1)) if match else None


def resource_name(resource: Any) -> str:
    if resource is None:
        return ""
    return getattr(resource, "name", "") or ""


def named_ref(resource: Any) -> NamedRef | None:
    if resource is None:
        return None
    return NamedRef(
        id=resource_id(resource),
        name=resource_name(resource),
        url=getattr(resource, "url", "") or "",
    )


def require_named_ref(resource: Any, label: str) -> NamedRef:
    ref = named_ref(resource)
    if ref is None:
        raise SourceNormalizationError(f"Missing {label} reference.")
    return ref


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def payload_hash(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def english_effect(raw: Any) -> tuple[str, str]:
    for entry in getattr(raw, "effect_entries", None) or []:
        language = getattr(entry, "language", None)
        if resource_name(language) == "en":
            return (
                getattr(entry, "effect", None) or "",
                getattr(entry, "short_effect", None) or "",
            )
    return "", ""


def normalize_pokemon(raw: Any, provenance: Provenance) -> Pokemon:
    try:
        types = tuple(
            PokemonTypeSlot(type=require_named_ref(entry.type, "type"), slot=int(entry.slot))
            for entry in getattr(raw, "types", []) or []
        )
        abilities = tuple(
            PokemonAbilitySlot(
                ability=require_named_ref(entry.ability, "ability"),
                slot=int(entry.slot),
                is_hidden=bool(entry.is_hidden),
            )
            for entry in getattr(raw, "abilities", []) or []
        )
        moves = tuple(_pokemon_move(entry) for entry in getattr(raw, "moves", []) or [])
        return Pokemon(
            id=int(raw.id),
            name=resource_name(raw),
            base_experience=getattr(raw, "base_experience", None),
            height=int(getattr(raw, "height", 0) or 0),
            weight=int(getattr(raw, "weight", 0) or 0),
            is_default=bool(getattr(raw, "is_default", False)),
            species=require_named_ref(getattr(raw, "species", None), "species"),
            types=types,
            abilities=abilities,
            moves=moves,
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize Pokémon.") from exc


def _pokemon_move(entry: Any) -> PokemonMoveEntry:
    details = tuple(
        VersionGroupDetail(
            version_group=require_named_ref(detail.version_group, "version_group"),
            move_learn_method=require_named_ref(detail.move_learn_method, "move_learn_method"),
            level_learned_at=int(getattr(detail, "level_learned_at", 0) or 0),
            order=getattr(detail, "order", None),
        )
        for detail in getattr(entry, "version_group_details", []) or []
    )
    return PokemonMoveEntry(move=require_named_ref(entry.move, "move"), version_group_details=details)


def normalize_species(raw: Any, provenance: Provenance) -> PokemonSpecies:
    try:
        return PokemonSpecies(
            id=int(raw.id),
            name=resource_name(raw),
            is_legendary=bool(getattr(raw, "is_legendary", False)),
            is_mythical=bool(getattr(raw, "is_mythical", False)),
            generation=resource_name(getattr(raw, "generation", None)),
            evolution_chain=named_ref(getattr(raw, "evolution_chain", None)),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize species.") from exc


def normalize_move(raw: Any, provenance: Provenance) -> Move:
    try:
        meta = getattr(raw, "meta", None)
        effect, short_effect = english_effect(raw)
        ailment = getattr(meta, "ailment", None) if meta is not None else None
        contest_effect = getattr(raw, "contest_effect", None)
        return Move(
            id=int(raw.id),
            name=resource_name(raw),
            power=getattr(raw, "power", None),
            accuracy=getattr(raw, "accuracy", None),
            pp=getattr(raw, "pp", None),
            priority=getattr(raw, "priority", None),
            type=named_ref(getattr(raw, "type", None)),
            damage_class=resource_name(getattr(raw, "damage_class", None)),
            effect_chance=getattr(raw, "effect_chance", None),
            effect=effect,
            short_effect=short_effect,
            target=resource_name(getattr(raw, "target", None)),
            ailment=resource_name(ailment),
            ailment_chance=getattr(meta, "ailment_chance", None) if meta is not None else None,
            flinch_chance=getattr(meta, "flinch_chance", None) if meta is not None else None,
            stat_chance=getattr(meta, "stat_chance", None) if meta is not None else None,
            drain=getattr(meta, "drain", None) if meta is not None else None,
            healing=getattr(meta, "healing", None) if meta is not None else None,
            min_hits=getattr(meta, "min_hits", None) if meta is not None else None,
            max_hits=getattr(meta, "max_hits", None) if meta is not None else None,
            min_turns=getattr(meta, "min_turns", None) if meta is not None else None,
            max_turns=getattr(meta, "max_turns", None) if meta is not None else None,
            contest_type=resource_name(getattr(raw, "contest_type", None)),
            contest_effect_id=resource_id(contest_effect),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize move.") from exc


def normalize_ability(raw: Any, provenance: Provenance) -> Ability:
    try:
        return Ability(id=int(raw.id), name=resource_name(raw), provenance=provenance)
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize ability.") from exc


def normalize_type(raw: Any, provenance: Provenance) -> Type:
    try:
        relations = getattr(raw, "damage_relations", None)
        return Type(
            id=int(raw.id),
            name=resource_name(raw),
            damage_relations=TypeRelations(
                double_damage_to=_ref_tuple(getattr(relations, "double_damage_to", []) if relations else []),
                half_damage_to=_ref_tuple(getattr(relations, "half_damage_to", []) if relations else []),
                no_damage_to=_ref_tuple(getattr(relations, "no_damage_to", []) if relations else []),
            ),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize type.") from exc


def _ref_tuple(values: Any) -> tuple[NamedRef, ...]:
    refs: list[NamedRef] = []
    for value in values or []:
        ref = named_ref(value)
        if ref is not None:
            refs.append(ref)
    return tuple(refs)


def normalize_encounters(raw: Any) -> list[LocationAreaEncounter]:
    try:
        return [_location_area_encounter(entry) for entry in raw or []]
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize encounters.") from exc


def _location_area_encounter(entry: Any) -> LocationAreaEncounter:
    versions = []
    for version_detail in getattr(entry, "version_details", []) or []:
        details = tuple(
            EncounterDetail(
                method=require_named_ref(detail.method, "method"),
                min_level=int(detail.min_level),
                max_level=int(detail.max_level),
                chance=int(detail.chance),
                condition_values=_ref_tuple(getattr(detail, "condition_values", [])),
            )
            for detail in getattr(version_detail, "encounter_details", []) or []
        )
        versions.append(
            EncounterVersionDetail(
                version=require_named_ref(version_detail.version, "version"),
                encounter_details=details,
            )
        )
    return LocationAreaEncounter(
        location_area=require_named_ref(entry.location_area, "location_area"),
        version_details=tuple(versions),
    )


def normalize_location_area(raw: Any, provenance: Provenance) -> LocationArea:
    try:
        return LocationArea(
            id=int(raw.id),
            name=resource_name(raw),
            location=require_named_ref(getattr(raw, "location", None), "location"),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize location area.") from exc


def normalize_location(raw: Any, provenance: Provenance) -> Location:
    try:
        return Location(
            id=int(raw.id),
            name=resource_name(raw),
            region=named_ref(getattr(raw, "region", None)),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize location.") from exc


def normalize_region(raw: Any, provenance: Provenance) -> Region:
    try:
        return Region(id=int(raw.id), name=resource_name(raw), provenance=provenance)
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize region.") from exc


def normalize_version(raw: Any, provenance: Provenance) -> GameVersion:
    try:
        return GameVersion(
            id=int(raw.id),
            name=resource_name(raw),
            version_group=named_ref(getattr(raw, "version_group", None)),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize version.") from exc


def normalize_version_group(raw: Any, provenance: Provenance) -> VersionGroup:
    try:
        return VersionGroup(
            id=int(raw.id),
            name=resource_name(raw),
            regions=_ref_tuple(getattr(raw, "regions", [])),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize version group.") from exc


def normalize_item(raw: Any, provenance: Provenance) -> Item:
    try:
        return Item(id=int(raw.id), name=resource_name(raw), provenance=provenance)
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize item.") from exc


def normalize_evolution_chain(raw: Any, provenance: Provenance) -> EvolutionChain:
    try:
        return EvolutionChain(
            id=int(raw.id),
            chain=_evolution_link(getattr(raw, "chain", None)),
            provenance=provenance,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise SourceNormalizationError("Could not normalize evolution chain.") from exc


def _evolution_link(link: Any) -> EvolutionLink:
    if link is None:
        raise SourceNormalizationError("Evolution chain is missing its root link.")
    details = tuple(_evolution_detail(detail) for detail in getattr(link, "evolution_details", []) or [])
    children = tuple(_evolution_link(child) for child in getattr(link, "evolves_to", []) or [])
    return EvolutionLink(
        species=require_named_ref(getattr(link, "species", None), "species"),
        is_baby=bool(getattr(link, "is_baby", False)),
        evolution_details=details,
        evolves_to=children,
    )


def _evolution_detail(detail: Any) -> EvolutionDetail:
    return EvolutionDetail(
        trigger=named_ref(getattr(detail, "trigger", None)),
        item=named_ref(getattr(detail, "item", None)),
        held_item=named_ref(getattr(detail, "held_item", None)),
        known_move=named_ref(getattr(detail, "known_move", None)),
        known_move_type=named_ref(getattr(detail, "known_move_type", None)),
        location=named_ref(getattr(detail, "location", None)),
        party_species=named_ref(getattr(detail, "party_species", None)),
        trade_species=named_ref(getattr(detail, "trade_species", None)),
        region=named_ref(getattr(detail, "region", None)),
        version_group=named_ref(getattr(detail, "version_group", None)),
        min_level=getattr(detail, "min_level", None),
        min_happiness=getattr(detail, "min_happiness", None),
        min_beauty=getattr(detail, "min_beauty", None),
        min_affection=getattr(detail, "min_affection", None),
        time_of_day=getattr(detail, "time_of_day", None) or "",
        needs_overworld_rain=bool(getattr(detail, "needs_overworld_rain", False)),
        turn_upside_down=bool(getattr(detail, "turn_upside_down", False)),
        relative_physical_stats=getattr(detail, "relative_physical_stats", None),
        gender=getattr(detail, "gender", None),
        is_default=bool(getattr(detail, "is_default", False)),
    )


def named_ref_to_dict(ref: NamedRef | None) -> dict[str, Any] | None:
    if ref is None:
        return None
    return {"id": ref.id, "name": ref.name, "url": ref.url}


def named_ref_from_dict(raw: dict[str, Any] | None) -> NamedRef | None:
    if raw is None:
        return None
    return NamedRef(id=raw.get("id"), name=raw.get("name") or "", url=raw.get("url") or "")


def provenance_to_dict(provenance: Provenance) -> dict[str, Any]:
    return {
        "source_url": provenance.source_url,
        "retrieved_at": provenance.retrieved_at.isoformat(),
        "source_version": provenance.source_version,
        "adapter_version": provenance.adapter_version,
        "payload_hash": provenance.payload_hash,
    }


def provenance_from_dict(raw: dict[str, Any]) -> Provenance:
    return Provenance(
        source_url=raw.get("source_url") or "",
        retrieved_at=datetime.fromisoformat(raw["retrieved_at"]),
        source_version=raw.get("source_version"),
        adapter_version=raw.get("adapter_version") or "",
        payload_hash=raw.get("payload_hash"),
    )
