from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_QUERY_TIMEOUT_S = 30.0
DEFAULT_MAX_PAGE_SIZE = 200
DEFAULT_DATABASE = "neo4j"


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    username: str
    password: str
    database: str
    read_username: str
    read_password: str
    query_timeout_s: float
    max_page_size: int

    @classmethod
    def from_environment(cls) -> "Neo4jSettings":
        load_dotenv()
        username = _required("NEO4J_USERNAME")
        password = _required("NEO4J_PASSWORD")
        return cls(
            uri=_required("NEO4J_URI"),
            username=username,
            password=password,
            database=os.getenv("NEO4J_DATABASE", DEFAULT_DATABASE),
            read_username=os.getenv("NEO4J_READ_USERNAME") or username,
            read_password=os.getenv("NEO4J_READ_PASSWORD") or password,
            query_timeout_s=_optional_float(
                "POKEGRAPH_QUERY_TIMEOUT_S",
                DEFAULT_QUERY_TIMEOUT_S,
            ),
            max_page_size=_optional_int("POKEGRAPH_MAX_PAGE_SIZE", DEFAULT_MAX_PAGE_SIZE),
        )

    @property
    def write_auth(self) -> tuple[str, str]:
        return (self.username, self.password)

    @property
    def read_auth(self) -> tuple[str, str]:
        return (self.read_username, self.read_password)


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value or value == "replace-with-your-aura-password":
        raise RuntimeError(f"Set {name} in .env before connecting to Neo4j.")
    return value


def _optional_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0.")
    return value


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0.")
    return value
