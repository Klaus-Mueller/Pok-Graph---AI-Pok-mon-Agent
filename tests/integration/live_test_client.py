from __future__ import annotations

import json
import os
import unittest

from pokegraph import PokeGraphClient
from tests.integration.query_lib import QUERIES_DIR

LIVE_ENABLED = os.getenv("POKEGRAPH_LIVE_QUERY_TESTS") == "1"
PARAMETERS_PATH = QUERIES_DIR / "examples" / "parameters.json"


@unittest.skipUnless(LIVE_ENABLED, "Set POKEGRAPH_LIVE_QUERY_TESTS=1 to run live read-only checks")
class LiveClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        try:
            self.client = PokeGraphClient.from_environment()
            await self.client.open()
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"Neo4j is not reachable: {exc}") from exc
        if PARAMETERS_PATH.exists():
            self.params = json.loads(PARAMETERS_PATH.read_text(encoding="utf-8"))
        else:
            self.params = {}

    async def asyncTearDown(self) -> None:
        if getattr(self, "client", None) is not None:
            await self.client.close()

    async def test_two_version_groups_via_client(self) -> None:
        groups = await self.client.list_version_groups(limit=50)
        self.assertGreaterEqual(len({row["version_group_id"] for row in groups.rows}), 1)
        fingerprint = await self.client.dataset_fingerprint()
        self.assertEqual(len(fingerprint.rows), 1)
        self.assertGreater(fingerprint.rows[0]["game_version_count"], 0)

    async def test_domain_methods_match_recorded_ids(self) -> None:
        params = self.params
        if not params:
            self.skipTest("queries/examples/parameters.json is missing; run record_examples")

        resolved = await self.client.resolve_version_group(
            params["version_id"],
            version_group_id=params["version_group_id"],
        )
        self.assertEqual(resolved.context.version_group_id, params["version_group_id"])

        encounters = await self.client.locations_of_pokemon(
            params["pokemon_id"],
            params["version_id"],
            limit=10,
        )
        if encounters.rows:
            self.assertEqual(encounters.rows[0]["version_id"], params["version_id"])
            self.assertIn("encounter_id", encounters.rows[0])

        learnset = await self.client.learnset_for_pokemon(
            params["pokemon_id"],
            version_id=params["version_id"],
            limit=10,
        )
        self.assertEqual(learnset.context.version_group_id, params["version_group_id"])
        if learnset.rows:
            self.assertIn("source_url", learnset.rows[0])

        other = await self.client.list_version_groups(limit=50)
        other_ids = {row["version_group_id"] for row in other.rows} - {params["version_group_id"]}
        self.assertTrue(other_ids, "expected more than one version group in the live database")
        other_learnset = await self.client.learnset_for_pokemon(
            params["pokemon_id"],
            version_group_id=next(iter(other_ids)),
            limit=5,
        )
        self.assertIsInstance(other_learnset.rows, list)


if __name__ == "__main__":
    unittest.main()
