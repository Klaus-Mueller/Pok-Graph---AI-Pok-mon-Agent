from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from pokegraph.config import Neo4jSettings

DEFAULT_POKEMON_LIST_URL = "https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0"


@dataclass(frozen=True)
class Settings:
    neo4j: Neo4jSettings
    pokemon_names: tuple[str, ...]
    pokeapi_pokemon_list_url: str
    pokeapi_cache_size: int
    pokeapi_cache_dir: Path | None
    pokeapi_cache_ttl_s: float | None

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        raw_names = os.getenv("POKEGRAPH_POKEMON_NAMES")
        names = (
            tuple(name.strip().lower() for name in raw_names.split(",") if name.strip())
            if raw_names
            else ()
        )
        cache_dir = os.getenv("POKEGRAPH_CACHE_DIR")
        ttl_raw = os.getenv("POKEGRAPH_CACHE_TTL_S")
        return cls(
            neo4j=Neo4jSettings.from_environment(),
            pokemon_names=names,
            pokeapi_pokemon_list_url=os.getenv(
                "POKEGRAPH_POKEAPI_POKEMON_LIST_URL",
                DEFAULT_POKEMON_LIST_URL,
            ),
            pokeapi_cache_size=int(os.getenv("POKEGRAPH_POKEAPI_CACHE_SIZE", "2000")),
            pokeapi_cache_dir=Path(cache_dir).expanduser() if cache_dir else None,
            pokeapi_cache_ttl_s=float(ttl_raw) if ttl_raw else None,
        )

    @property
    def neo4j_uri(self) -> str:
        return self.neo4j.uri

    @property
    def neo4j_username(self) -> str:
        return self.neo4j.username

    @property
    def neo4j_password(self) -> str:
        return self.neo4j.password

    @property
    def neo4j_database(self) -> str:
        return self.neo4j.database
