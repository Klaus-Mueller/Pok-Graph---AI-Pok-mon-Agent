from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_POKEMON_LIST_URL = "https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0"


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str
    pokemon_names: tuple[str, ...]
    pokeapi_pokemon_list_url: str
    pokeapi_cache_size: int

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()

        # Optional override for short local runs. When unset/empty, ingest fetches the full catalog.
        raw_names = os.getenv("POKEGRAPH_POKEMON_NAMES")
        names = (
            tuple(name.strip().lower() for name in raw_names.split(",") if name.strip())
            if raw_names
            else ()
        )
        return cls(
            neo4j_uri=_required("NEO4J_URI"),
            neo4j_username=_required("NEO4J_USERNAME"),
            neo4j_password=_required("NEO4J_PASSWORD"),
            neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
            pokemon_names=names,
            pokeapi_pokemon_list_url=os.getenv(
                "POKEGRAPH_POKEAPI_POKEMON_LIST_URL",
                DEFAULT_POKEMON_LIST_URL,
            ),
            pokeapi_cache_size=int(os.getenv("POKEGRAPH_POKEAPI_CACHE_SIZE", "2000")),
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value or value == "replace-with-your-aura-password":
        raise RuntimeError(f"Set {name} in .env before running the ingestion.")
    return value
