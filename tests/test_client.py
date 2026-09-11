from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from pokegraph.config import Neo4jSettings
from pokegraph.errors import (
    EntityNotFoundError,
    IncompatibleGameContextError,
    InvalidQueryParameterError,
)
from pokegraph.graph.client import PokeGraphClient
from pokegraph.graph.connection import GraphConnection
from pokegraph.graph.registry import QueryRegistry
from pokegraph.graph.serialize import jsonable


def _settings() -> Neo4jSettings:
    return Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        read_username="reader",
        read_password="read-secret",
        query_timeout_s=5.0,
        max_page_size=20,
    )


class FakeRecord:
    def __init__(self, data: dict) -> None:
        self._data = data

    def data(self) -> dict:
        return self._data


class ClientParameterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.responses: dict[str, list[dict]] = {}

        async def run(cypher: str, params: dict, timeout: float):
            self.calls.append((cypher, params))
            if "RETURN p.id AS pokemon_id" in cypher and "HAS_LEARNSET_ENTRY" not in cypher:
                key = "get_pokemon"
            elif "RETURN vg.id AS version_group_id" in cypher and "IN_VERSION_GROUP" not in cypher:
                key = "get_version_group"
            elif "RETURN v.id AS version_id" in cypher and "IN_VERSION_GROUP" not in cypher:
                key = "get_version"
            elif "IN_VERSION_GROUP" in cypher and "version_group_name" in cypher:
                key = "resolve"
            elif "HAS_LEARNSET_ENTRY" in cypher and "learnset_entry_id" in cypher:
                key = "learnset"
            else:
                key = ""
            rows = self.responses.get(key, [])
            return [FakeRecord(row) for row in rows]

        self.client = PokeGraphClient(
            _settings(),
            connection=GraphConnection(_settings(), run=run),
            registry=QueryRegistry.load(),
        )

    async def test_empty_name_is_invalid(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            await self.client.find_pokemon("")

    async def test_learnset_requires_game_context(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            await self.client.learnset_for_pokemon(25)

    async def test_incompatible_version_and_group(self) -> None:
        self.responses["get_version"] = [{"version_id": 15}]
        self.responses["resolve"] = []
        with self.assertRaises(IncompatibleGameContextError):
            await self.client.learnset_for_pokemon(25, version_id=15, version_group_id=99)

    async def test_missing_entity(self) -> None:
        self.responses["get_pokemon"] = []
        with self.assertRaises(EntityNotFoundError):
            await self.client.locations_of_pokemon(999, version_id=15)

    async def test_limit_capped_by_settings(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            await self.client.find_pokemon("pikachu", limit=50)

    def test_jsonable_datetime(self) -> None:
        value = datetime(2026, 1, 1, tzinfo=timezone.utc)
        neo = SimpleNamespace(iso_format=lambda: "2026-01-01T00:00:00Z")
        self.assertEqual(jsonable(value), "2026-01-01T00:00:00+00:00")
        self.assertEqual(jsonable(neo), "2026-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
