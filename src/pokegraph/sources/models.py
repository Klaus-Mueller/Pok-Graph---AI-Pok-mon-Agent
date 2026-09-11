from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SOURCE_VERSION_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Provenance:
    source_url: str
    retrieved_at: datetime
    source_version: str | None = SOURCE_VERSION_UNAVAILABLE
    adapter_version: str = ""
    payload_hash: str | None = None


@dataclass(frozen=True)
class NamedRef:
    id: int | None
    name: str
    url: str = ""


@dataclass(frozen=True)
class PokemonTypeSlot:
    type: NamedRef
    slot: int


@dataclass(frozen=True)
class PokemonAbilitySlot:
    ability: NamedRef
    slot: int
    is_hidden: bool


@dataclass(frozen=True)
class VersionGroupDetail:
    version_group: NamedRef
    move_learn_method: NamedRef
    level_learned_at: int
    order: int | None


@dataclass(frozen=True)
class PokemonMoveEntry:
    move: NamedRef
    version_group_details: tuple[VersionGroupDetail, ...] = ()


@dataclass(frozen=True)
class Pokemon:
    id: int
    name: str
    base_experience: int | None
    height: int
    weight: int
    is_default: bool
    species: NamedRef
    types: tuple[PokemonTypeSlot, ...]
    abilities: tuple[PokemonAbilitySlot, ...]
    moves: tuple[PokemonMoveEntry, ...]
    provenance: Provenance


@dataclass(frozen=True)
class PokemonSpecies:
    id: int
    name: str
    is_legendary: bool
    is_mythical: bool
    generation: str
    evolution_chain: NamedRef | None
    provenance: Provenance


@dataclass(frozen=True)
class Move:
    id: int
    name: str
    power: int | None
    accuracy: int | None
    pp: int | None
    priority: int | None
    type: NamedRef | None
    damage_class: str
    effect_chance: int | None
    effect: str
    short_effect: str
    target: str
    ailment: str
    ailment_chance: int | None
    flinch_chance: int | None
    stat_chance: int | None
    drain: int | None
    healing: int | None
    min_hits: int | None
    max_hits: int | None
    min_turns: int | None
    max_turns: int | None
    contest_type: str
    contest_effect_id: int | None
    provenance: Provenance

    @property
    def type_id(self) -> int | None:
        return None if self.type is None else self.type.id

    @property
    def type_name(self) -> str:
        return "" if self.type is None else self.type.name


@dataclass(frozen=True)
class Ability:
    id: int
    name: str
    provenance: Provenance


@dataclass(frozen=True)
class TypeRelations:
    double_damage_to: tuple[NamedRef, ...] = ()
    half_damage_to: tuple[NamedRef, ...] = ()
    no_damage_to: tuple[NamedRef, ...] = ()


@dataclass(frozen=True)
class Type:
    id: int
    name: str
    damage_relations: TypeRelations
    provenance: Provenance


@dataclass(frozen=True)
class EncounterDetail:
    method: NamedRef
    min_level: int
    max_level: int
    chance: int
    condition_values: tuple[NamedRef, ...] = ()


@dataclass(frozen=True)
class EncounterVersionDetail:
    version: NamedRef
    encounter_details: tuple[EncounterDetail, ...] = ()


@dataclass(frozen=True)
class LocationAreaEncounter:
    location_area: NamedRef
    version_details: tuple[EncounterVersionDetail, ...] = ()


@dataclass(frozen=True)
class EncounterSet:
    rows: tuple[LocationAreaEncounter, ...]
    provenance: Provenance


@dataclass(frozen=True)
class LocationArea:
    id: int
    name: str
    location: NamedRef
    provenance: Provenance


@dataclass(frozen=True)
class Location:
    id: int
    name: str
    region: NamedRef | None
    provenance: Provenance


@dataclass(frozen=True)
class Region:
    id: int
    name: str
    provenance: Provenance


@dataclass(frozen=True)
class GameVersion:
    id: int
    name: str
    version_group: NamedRef | None
    provenance: Provenance


@dataclass(frozen=True)
class VersionGroup:
    id: int
    name: str
    provenance: Provenance
    regions: tuple[NamedRef, ...] = ()


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    provenance: Provenance


@dataclass(frozen=True)
class EvolutionDetail:
    trigger: NamedRef | None
    item: NamedRef | None
    held_item: NamedRef | None
    known_move: NamedRef | None
    known_move_type: NamedRef | None
    location: NamedRef | None
    party_species: NamedRef | None
    trade_species: NamedRef | None
    region: NamedRef | None
    version_group: NamedRef | None
    min_level: int | None
    min_happiness: int | None
    min_beauty: int | None
    min_affection: int | None
    time_of_day: str
    needs_overworld_rain: bool
    turn_upside_down: bool
    relative_physical_stats: int | None
    gender: int | None
    is_default: bool


@dataclass(frozen=True)
class EvolutionLink:
    species: NamedRef
    is_baby: bool
    evolution_details: tuple[EvolutionDetail, ...] = ()
    evolves_to: tuple["EvolutionLink", ...] = ()


@dataclass(frozen=True)
class EvolutionChain:
    id: int
    chain: EvolutionLink
    provenance: Provenance
