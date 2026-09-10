from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

REPO_ROOT = Path(__file__).resolve().parents[2]
QUERIES_DIR = REPO_ROOT / "queries"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "graph.cypher"


def load_cypher(path: Path) -> str:
    """Return Cypher with // comment lines removed."""
    lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def query_path(*parts: str) -> Path:
    return QUERIES_DIR.joinpath(*parts)


def listing_params(**extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"skip": 0, "limit": 50}
    params.update(extra)
    return params


def neo4j_settings() -> dict[str, str] | None:
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not username or not password:
        return None
    if password == "replace-with-your-aura-password":
        return None
    return {
        "uri": uri,
        "username": username,
        "password": password,
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }


def connect_driver():
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    settings = neo4j_settings()
    if settings is None:
        return None, None
    driver = GraphDatabase.driver(
        settings["uri"],
        auth=(settings["username"], settings["password"]),
    )
    return driver, settings["database"]


def records_to_dicts(result) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in result:
        row = {}
        for key, value in record.data().items():
            row[key] = _jsonable(value)
        rows.append(row)
    return rows


def _jsonable(value: Any) -> Any:
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
