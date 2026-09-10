from __future__ import annotations

import unittest

from tests.integration.query_lib import (
    FIXTURE_PATH,
    connect_driver,
    listing_params,
    load_cypher,
    query_path,
    records_to_dicts,
)

V_A = -201
V_B = -202
V_OTHER = -203
VG_AB = -301
VG_OTHER = -302
AREA = -601
P_SHARED = -101
P_ONLY_A = -102
P_ONLY_B = -103
P_DUAL = -104
P_ATTACKER = -105
P_GROUND = -106
S_BRANCH = -111
S_WATER = -112
S_THUNDER = -113
T_ELECTRIC = -701
T_WATER = -702
T_GROUND = -704
T_UNENRICHED = -705
M_THUNDERBOLT = -801
LM_LEVEL = -911
LM_MACHINE = -912
EM_WALK = -901
E_SHARED_A = "-101:-601:-201:-901:15:25:30:"
E_SHARED_B = "-101:-601:-202:-901:15:25:30:"
E_ONLY_A = "-102:-601:-201:-901:5:10:20:"
E_ONLY_B = "-103:-601:-202:-901:5:10:20:"
LS_LEVEL = "-101:-801:-301:-911:26:1"
LS_MACHINE = "-101:-801:-301:-912:0:"


class QueryCatalogTests(unittest.TestCase):
    driver = None
    database = None

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

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.driver is not None:
            cls.driver.close()

    def setUp(self) -> None:
        self.session = self.driver.session(database=self.database)
        self.tx = self.session.begin_transaction()
        self.tx.run(load_cypher(FIXTURE_PATH)).consume()

    def tearDown(self) -> None:
        if getattr(self, "tx", None) is not None and not self.tx.closed():
            self.tx.rollback()
        if getattr(self, "session", None) is not None:
            self.session.close()

    def rows(self, *parts: str, **params):
        result = self.tx.run(load_cypher(query_path(*parts)), **params)
        return records_to_dicts(result)

    def test_resolve_version_group_and_reject_incoherent_pair(self) -> None:
        matched = self.rows(
            "discovery",
            "resolve_version_group.cypher",
            version_id=V_A,
            version_group_id=None,
        )
        self.assertEqual(
            matched,
            [
                {
                    "version_id": V_A,
                    "version_name": "fixture-version-a",
                    "version_group_id": VG_AB,
                    "version_group_name": "fixture-group-ab",
                }
            ],
        )
        coherent = self.rows(
            "discovery",
            "resolve_version_group.cypher",
            version_id=V_A,
            version_group_id=VG_AB,
        )
        self.assertEqual(len(coherent), 1)
        incoherent = self.rows(
            "discovery",
            "resolve_version_group.cypher",
            version_id=V_A,
            version_group_id=VG_OTHER,
        )
        self.assertEqual(incoherent, [])

    def test_find_pokemon_by_name_exact_then_prefix(self) -> None:
        exact = self.rows(
            "discovery",
            "find_pokemon_by_name.cypher",
            **listing_params(name="fixture-shared"),
        )
        self.assertEqual(exact[0]["pokemon_id"], P_SHARED)
        self.assertEqual(exact[0]["match_rank"], 0)
        prefix = self.rows(
            "discovery",
            "find_pokemon_by_name.cypher",
            **listing_params(name="fixture-only"),
        )
        self.assertEqual([row["pokemon_id"] for row in prefix], [P_ONLY_B, P_ONLY_A])
        self.assertTrue(all(row["match_rank"] == 1 for row in prefix))

    def test_list_location_areas_filters_by_version_encounters(self) -> None:
        in_a = self.rows(
            "discovery",
            "list_location_areas.cypher",
            **listing_params(
                region_id=None,
                location_id=None,
                location_area_id=None,
                version_id=V_A,
            ),
        )
        self.assertEqual([row["location_area_id"] for row in in_a], [AREA])
        in_other = self.rows(
            "discovery",
            "list_location_areas.cypher",
            **listing_params(
                region_id=None,
                location_id=None,
                location_area_id=None,
                version_id=V_OTHER,
            ),
        )
        self.assertEqual(in_other, [])

    def test_pokemon_in_area_level_overlap(self) -> None:
        overlapping = self.rows(
            "encounters",
            "pokemon_in_area.cypher",
            **listing_params(
                location_area_id=AREA,
                version_id=V_A,
                method_id=None,
                min_level=10,
                max_level=20,
            ),
        )
        self.assertEqual(
            [(row["pokemon_id"], row["encounter_id"]) for row in overlapping],
            [(P_ONLY_A, E_ONLY_A), (P_SHARED, E_SHARED_A)],
        )
        no_overlap = self.rows(
            "encounters",
            "pokemon_in_area.cypher",
            **listing_params(
                location_area_id=AREA,
                version_id=V_A,
                method_id=None,
                min_level=26,
                max_level=30,
            ),
        )
        self.assertEqual(no_overlap, [])

    def test_locations_of_pokemon_and_method_filter(self) -> None:
        rows = self.rows(
            "encounters",
            "locations_of_pokemon.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_id=V_A,
                method_id=EM_WALK,
                min_level=None,
                max_level=None,
            ),
        )
        self.assertEqual([row["encounter_id"] for row in rows], [E_SHARED_A])
        missing_method = self.rows(
            "encounters",
            "locations_of_pokemon.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_id=V_A,
                method_id=-999,
                min_level=None,
                max_level=None,
            ),
        )
        self.assertEqual(missing_method, [])

    def test_compare_versions_membership(self) -> None:
        rows = self.rows(
            "encounters",
            "compare_versions.cypher",
            **listing_params(
                version_id_a=V_A,
                version_id_b=V_B,
                location_area_id=AREA,
            ),
        )
        by_pokemon = {row["pokemon_id"]: row for row in rows}
        self.assertEqual(set(by_pokemon), {P_SHARED, P_ONLY_A, P_ONLY_B})
        self.assertEqual(by_pokemon[P_SHARED]["membership"], "both")
        self.assertEqual(set(by_pokemon[P_SHARED]["encounter_ids_a"]), {E_SHARED_A})
        self.assertEqual(set(by_pokemon[P_SHARED]["encounter_ids_b"]), {E_SHARED_B})
        self.assertEqual(by_pokemon[P_ONLY_A]["membership"], "only_a")
        self.assertEqual(by_pokemon[P_ONLY_B]["membership"], "only_b")

    def test_learnset_separates_level_up_from_machine(self) -> None:
        rows = self.rows(
            "learnsets",
            "learnset_for_pokemon.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_group_id=VG_AB,
                learn_method_id=None,
            ),
        )
        self.assertEqual(
            [(row["learnset_entry_id"], row["learn_method_id"], row["level_learned_at"]) for row in rows],
            [(LS_MACHINE, LM_MACHINE, 0), (LS_LEVEL, LM_LEVEL, 26)],
        )
        machine = next(row for row in rows if row["learn_method_id"] == LM_MACHINE)
        self.assertEqual(machine["source_url"], "https://pokeapi.co/api/v2/pokemon/-101/")
        self.assertEqual(machine["retrieved_at"], "2026-01-01T00:00:00+00:00")
        level_only = self.rows(
            "learnsets",
            "learnset_for_pokemon.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_group_id=VG_AB,
                learn_method_id=LM_LEVEL,
            ),
        )
        self.assertEqual([row["learnset_entry_id"] for row in level_only], [LS_LEVEL])
        wrong_group = self.rows(
            "learnsets",
            "learnset_for_pokemon.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_group_id=VG_OTHER,
                learn_method_id=None,
            ),
        )
        self.assertEqual(wrong_group, [])

    def test_who_learns_move(self) -> None:
        rows = self.rows(
            "learnsets",
            "who_learns_move.cypher",
            **listing_params(
                move_id=M_THUNDERBOLT,
                version_group_id=VG_AB,
                learn_method_id=None,
            ),
        )
        self.assertEqual([row["pokemon_id"] for row in rows], [P_SHARED, P_SHARED])
        self.assertEqual({row["learn_method_id"] for row in rows}, {LM_LEVEL, LM_MACHINE})

    def test_evolution_alternatives_preserved(self) -> None:
        from_rows = self.rows(
            "evolutions",
            "evolutions_from_species.cypher",
            **listing_params(species_id=S_BRANCH),
        )
        self.assertEqual(
            [(row["to_species_id"], row["item_name"], row["version_group"]) for row in from_rows],
            [(S_THUNDER, "thunder-stone", None), (S_WATER, "water-stone", None)],
        )
        self.assertEqual(len({row["evolves_to_id"] for row in from_rows}), 2)
        to_rows = self.rows(
            "evolutions",
            "evolutions_to_species.cypher",
            **listing_params(species_id=S_WATER),
        )
        self.assertEqual([row["from_species_id"] for row in to_rows], [S_BRANCH])
        chain = self.rows(
            "evolutions",
            "evolution_chain.cypher",
            **listing_params(species_id=S_WATER),
        )
        self.assertEqual(
            sorted(row["to_species_id"] for row in chain),
            sorted([S_WATER, S_THUNDER]),
        )

    def test_type_effectiveness_dual_type_immunity_and_incomplete(self) -> None:
        dual = self.rows(
            "matchups",
            "type_effectiveness.cypher",
            attacker_type_id=T_ELECTRIC,
            defender_pokemon_id=P_DUAL,
        )
        self.assertEqual(dual[0]["factor"], 4.0)
        self.assertEqual(dual[0]["effectiveness"], "weak")
        self.assertTrue(dual[0]["data_complete"])

        immune = self.rows(
            "matchups",
            "type_effectiveness.cypher",
            attacker_type_id=T_ELECTRIC,
            defender_pokemon_id=P_GROUND,
        )
        self.assertEqual(immune[0]["factor"], 0.0)
        self.assertEqual(immune[0]["effectiveness"], "immune")

        ground_vs_dual = self.rows(
            "matchups",
            "type_effectiveness.cypher",
            attacker_type_id=T_GROUND,
            defender_pokemon_id=P_DUAL,
        )
        self.assertEqual(ground_vs_dual[0]["factor"], 0.0)
        self.assertEqual(ground_vs_dual[0]["effectiveness"], "immune")

        missing_is_neutral = self.rows(
            "matchups",
            "type_effectiveness.cypher",
            attacker_type_id=T_WATER,
            defender_pokemon_id=P_DUAL,
        )
        self.assertEqual(missing_is_neutral[0]["factor"], 1.0)
        self.assertEqual(missing_is_neutral[0]["effectiveness"], "neutral")
        self.assertTrue(missing_is_neutral[0]["data_complete"])

        incomplete = self.rows(
            "matchups",
            "type_effectiveness.cypher",
            attacker_type_id=T_UNENRICHED,
            defender_pokemon_id=P_DUAL,
        )
        self.assertIsNone(incomplete[0]["factor"])
        self.assertEqual(incomplete[0]["effectiveness"], "unknown")
        self.assertFalse(incomplete[0]["data_complete"])

    def test_offensive_coverage_advantage_is_not_a_win(self) -> None:
        by_type = self.rows(
            "matchups",
            "offensive_coverage_by_types.cypher",
            **listing_params(pokemon_id=P_ATTACKER, defender_pokemon_id=P_DUAL),
        )
        self.assertEqual(by_type[0]["factor"], 4.0)
        self.assertTrue(by_type[0]["advantage"])

        by_move = self.rows(
            "matchups",
            "offensive_coverage_by_learnset.cypher",
            **listing_params(
                pokemon_id=P_SHARED,
                version_group_id=VG_AB,
                defender_pokemon_id=P_DUAL,
                learn_method_id=None,
            ),
        )
        self.assertEqual(len(by_move), 2)
        self.assertTrue(all(row["advantage"] for row in by_move))
        self.assertEqual({row["level_learned_at"] for row in by_move}, {0, 26})

        vs_ground = self.rows(
            "matchups",
            "offensive_coverage_by_types.cypher",
            **listing_params(pokemon_id=P_ATTACKER, defender_pokemon_id=P_GROUND),
        )
        self.assertEqual(vs_ground[0]["effectiveness"], "immune")
        self.assertFalse(vs_ground[0]["advantage"])
