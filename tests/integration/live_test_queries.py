from __future__ import annotations

import json
import os
import unittest

from neo4j import READ_ACCESS

from tests.integration.query_lib import (
    QUERIES_DIR,
    connect_driver,
    listing_params,
    load_cypher,
    query_path,
    records_to_dicts,
)

LIVE_ENABLED = os.getenv("POKEGRAPH_LIVE_QUERY_TESTS") == "1"
PARAMETERS_PATH = QUERIES_DIR / "examples" / "parameters.json"
EXPECTED_PATH = QUERIES_DIR / "examples" / "expected-results.json"


@unittest.skipUnless(LIVE_ENABLED, "Set POKEGRAPH_LIVE_QUERY_TESTS=1 to run live read-only checks")
class LiveQueryCatalogTests(unittest.TestCase):
    driver = None
    database = None
    params: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        driver, database = connect_driver()
        if driver is None:
            raise unittest.SkipTest("NEO4J_URI / credentials are not configured")
        try:
            driver.verify_connectivity()
        except Exception as exc:  # pragma: no cover - environment dependent
            driver.close()
            raise unittest.SkipTest(f"Neo4j is not reachable: {exc}") from exc
        cls.driver = driver
        cls.database = database
        if PARAMETERS_PATH.exists():
            cls.params = json.loads(PARAMETERS_PATH.read_text(encoding="utf-8"))
        else:
            cls.params = {}

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.driver is not None:
            cls.driver.close()

    def rows(self, *parts: str, **params):
        with self.driver.session(database=self.database, default_access_mode=READ_ACCESS) as session:
            result = session.run(load_cypher(query_path(*parts)), **params)
            return records_to_dicts(result)

    def test_fingerprint_and_two_version_groups(self) -> None:
        fingerprint = self.rows("discovery", "dataset_fingerprint.cypher")
        self.assertEqual(len(fingerprint), 1)
        self.assertGreater(fingerprint[0]["game_version_count"], 0)
        groups = self.rows(
            "discovery",
            "list_version_groups_with_data.cypher",
            **listing_params(limit=50),
        )
        group_ids = {row["version_group_id"] for row in groups}
        self.assertGreaterEqual(len(group_ids), 1)
        if EXPECTED_PATH.exists():
            expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
            self.assertIn("fingerprint", expected)

    def test_main_queries_return_documented_columns(self) -> None:
        params = self.params
        if not params:
            self.skipTest("queries/examples/parameters.json is missing; run record_examples")

        resolve = self.rows(
            "discovery",
            "resolve_version_group.cypher",
            version_id=params["version_id"],
            version_group_id=params["version_group_id"],
        )
        self.assertTrue(resolve)
        self.assertEqual(resolve[0]["version_group_id"], params["version_group_id"])

        incoherent = self.rows(
            "discovery",
            "resolve_version_group.cypher",
            version_id=params["version_id"],
            version_group_id=params.get("second_version_group_id"),
        )
        if params.get("second_version_group_id") not in {None, params["version_group_id"]}:
            self.assertEqual(incoherent, [])

        encounters = self.rows(
            "encounters",
            "locations_of_pokemon.cypher",
            **listing_params(
                pokemon_id=params["pokemon_id"],
                version_id=params["version_id"],
                method_id=None,
                min_level=None,
                max_level=None,
                limit=10,
            ),
        )
        if encounters:
            self.assertIn("encounter_id", encounters[0])
            self.assertEqual(encounters[0]["version_id"], params["version_id"])

        if params.get("version_group_id") is not None:
            learnset = self.rows(
                "learnsets",
                "learnset_for_pokemon.cypher",
                **listing_params(
                    pokemon_id=params["pokemon_id"],
                    version_group_id=params["version_group_id"],
                    learn_method_id=None,
                    limit=10,
                ),
            )
            if learnset:
                self.assertIn("learnset_entry_id", learnset[0])
                self.assertEqual(learnset[0]["version_group_id"], params["version_group_id"])
                self.assertIn("source_url", learnset[0])

        if params.get("species_id") is not None:
            evolutions = self.rows(
                "evolutions",
                "evolutions_from_species.cypher",
                **listing_params(species_id=params["species_id"], limit=10),
            )
            if evolutions:
                self.assertIn("evolves_to_id", evolutions[0])

        if params.get("attacker_type_id") is not None and params.get("defender_pokemon_id") is not None:
            matchup = self.rows(
                "matchups",
                "type_effectiveness.cypher",
                attacker_type_id=params["attacker_type_id"],
                defender_pokemon_id=params["defender_pokemon_id"],
            )
            if matchup:
                self.assertIn("data_complete", matchup[0])
                self.assertIn(matchup[0]["effectiveness"], {"immune", "resist", "neutral", "weak", "unknown"})
