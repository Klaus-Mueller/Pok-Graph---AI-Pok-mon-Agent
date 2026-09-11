from __future__ import annotations

import unittest

from pokegraph.config import Neo4jSettings
from pokegraph.errors import EntityNotFoundError, IncompatibleGameContextError
from pokegraph.graph.client import PokeGraphClient
from pokegraph.graph.connection import GraphConnection, create_driver
from pokegraph.graph.registry import QueryRegistry
from tests.integration.query_lib import FIXTURE_PATH, load_cypher
from tests.integration.test_queries import (
    AREA,
    E_ONLY_A,
    E_SHARED_A,
    LM_MACHINE,
    LS_LEVEL,
    LS_MACHINE,
    P_DUAL,
    P_SHARED,
    S_BRANCH,
    T_ELECTRIC,
    V_A,
    V_B,
    VG_AB,
    VG_OTHER,
)


class ClientCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        try:
            settings = Neo4jSettings.from_environment()
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        self.driver = create_driver(settings, read_only=False)
        try:
            await self.driver.verify_connectivity()
        except Exception as exc:  # pragma: no cover
            await self.driver.close()
            raise unittest.SkipTest(f"Neo4j is not reachable: {exc}") from exc
        self.session = self.driver.session(database=settings.database)
        self.tx = await self.session.begin_transaction()
        await self.tx.run(load_cypher(FIXTURE_PATH))

        async def run(cypher: str, params: dict, timeout: float):
            result = await self.tx.run(cypher, **params)
            return [record async for record in result]

        self.client = PokeGraphClient(
            settings,
            connection=GraphConnection(settings, run=run),
            registry=QueryRegistry.load(),
        )

    async def asyncTearDown(self) -> None:
        if getattr(self, "tx", None) is not None and not self.tx.closed:
            await self.tx.rollback()
        if getattr(self, "session", None) is not None:
            await self.session.close()
        if getattr(self, "driver", None) is not None:
            await self.driver.close()

    async def test_find_pokemon_and_empty_name_search(self) -> None:
        page = await self.client.find_pokemon("fixture-shared")
        self.assertEqual(page.rows[0]["pokemon_id"], P_SHARED)
        missing = await self.client.find_pokemon("no-such-pokemon")
        self.assertEqual(missing.rows, [])

    async def test_pokemon_in_area_matches_catalog(self) -> None:
        page = await self.client.pokemon_in_area(AREA, V_A, min_level=10, max_level=20)
        self.assertEqual(
            [(row["pokemon_id"], row["encounter_id"]) for row in page.rows],
            [(-102, E_ONLY_A), (P_SHARED, E_SHARED_A)],
        )
        self.assertEqual(page.context.version_id, V_A)
        self.assertIn("source_url", page.rows[0])

    async def test_missing_pokemon_is_not_found(self) -> None:
        with self.assertRaises(EntityNotFoundError):
            await self.client.locations_of_pokemon(-99999, V_A)

    async def test_learnset_resolves_version_group(self) -> None:
        page = await self.client.learnset_for_pokemon(P_SHARED, version_id=V_A)
        self.assertEqual(page.context.version_group_id, VG_AB)
        self.assertEqual(
            [row["learnset_entry_id"] for row in page.rows],
            [LS_MACHINE, LS_LEVEL],
        )
        self.assertEqual(page.rows[0]["learn_method_id"], LM_MACHINE)

    async def test_incompatible_learnset_context(self) -> None:
        with self.assertRaises(IncompatibleGameContextError):
            await self.client.learnset_for_pokemon(P_SHARED, version_id=V_A, version_group_id=VG_OTHER)

    async def test_compare_and_evolutions_and_matchups(self) -> None:
        compared = await self.client.compare_versions(V_A, V_B, location_area_id=AREA)
        membership = {row["pokemon_id"]: row["membership"] for row in compared.rows}
        self.assertEqual(membership[P_SHARED], "both")
        evos = await self.client.evolutions_from_species(S_BRANCH)
        self.assertEqual(len(evos.rows), 2)
        matchup = await self.client.type_effectiveness(T_ELECTRIC, P_DUAL)
        self.assertEqual(matchup.rows[0]["factor"], 4.0)
        self.assertTrue(matchup.data_complete)
        coverage = await self.client.offensive_coverage(P_SHARED, P_DUAL, version_group_id=VG_AB)
        self.assertEqual(coverage.query_id, "matchups.offensive_coverage_by_learnset")
        self.assertTrue(all(row["advantage"] for row in coverage.rows))


if __name__ == "__main__":
    unittest.main()
