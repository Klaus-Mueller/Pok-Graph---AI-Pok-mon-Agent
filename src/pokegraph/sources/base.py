from __future__ import annotations

from typing import Protocol

from .models import (
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
    Region,
    Type,
    VersionGroup,
)


class DataSource(Protocol):
    async def get_pokemon(self, identifier: str | int, *, force_refresh: bool = False) -> Pokemon: ...

    async def get_species(self, identifier: str | int, *, force_refresh: bool = False) -> PokemonSpecies: ...

    async def get_type(self, identifier: str | int, *, force_refresh: bool = False) -> Type: ...

    async def get_ability(self, identifier: str | int, *, force_refresh: bool = False) -> Ability: ...

    async def get_move(self, identifier: str | int, *, force_refresh: bool = False) -> Move: ...

    async def get_version(self, identifier: str | int, *, force_refresh: bool = False) -> GameVersion: ...

    async def get_version_group(self, identifier: str | int, *, force_refresh: bool = False) -> VersionGroup: ...

    async def get_region(self, identifier: str | int, *, force_refresh: bool = False) -> Region: ...

    async def get_location(self, identifier: str | int, *, force_refresh: bool = False) -> Location: ...

    async def get_location_area(self, identifier: str | int, *, force_refresh: bool = False) -> LocationArea: ...

    async def get_encounters(
        self,
        pokemon: str | int,
        *,
        force_refresh: bool = False,
    ) -> EncounterSet: ...

    async def get_evolution_chain(self, identifier: str | int, *, force_refresh: bool = False) -> EvolutionChain: ...

    async def get_item(self, identifier: str | int, *, force_refresh: bool = False) -> Item: ...

    async def close(self) -> None: ...
