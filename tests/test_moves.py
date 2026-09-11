from __future__ import annotations

import unittest

from pokegraph_ingest.writes.moves import move_props

from tests.model_fixtures import base_move, named


class MovePropsTests(unittest.TestCase):
    def test_thunderbolt_like_move(self) -> None:
        move = base_move(
            id=85,
            name="thunderbolt",
            power=90,
            accuracy=100,
            pp=15,
            type=named("electric", 13),
            damage_class="special",
            effect_chance=10,
            effect="Inflicts regular damage.  Has a 10% chance to paralyze the target.",
            short_effect="Has a 10% chance to paralyze the target.",
            ailment="paralysis",
            ailment_chance=10,
            flinch_chance=0,
            stat_chance=0,
            drain=0,
            healing=0,
        )
        props = move_props(move)
        self.assertEqual(props["id"], 85)
        self.assertEqual(props["name"], "thunderbolt")
        self.assertEqual(props["power"], 90)
        self.assertEqual(props["accuracy"], 100)
        self.assertEqual(props["pp"], 15)
        self.assertEqual(props["priority"], 0)
        self.assertEqual(props["type"], "electric")
        self.assertEqual(props["type_id"], 13)
        self.assertEqual(props["damage_class"], "special")
        self.assertEqual(props["effect_chance"], 10)
        self.assertEqual(props["ailment"], "paralysis")
        self.assertEqual(props["ailment_chance"], 10)
        self.assertEqual(props["source_url"], move.provenance.source_url)
        self.assertEqual(props["source_version"], "unavailable")

    def test_status_move_null_power_and_accuracy(self) -> None:
        move = base_move(
            id=86,
            name="thunder-wave",
            power=None,
            accuracy=90,
            pp=20,
            type=named("electric", 13),
            damage_class="status",
        )
        props = move_props(move)
        self.assertIsNone(props["power"])
        self.assertEqual(props["accuracy"], 90)
        self.assertEqual(props["damage_class"], "status")
        self.assertEqual(props["effect"], "")
        self.assertEqual(props["short_effect"], "")
        self.assertIsNone(props["flinch_chance"])

    def test_missing_type_yields_null_type_id(self) -> None:
        move = base_move(type=None, damage_class="physical")
        props = move_props(move)
        self.assertEqual(props["type"], "")
        self.assertIsNone(props["type_id"])
        self.assertEqual(props["damage_class"], "physical")

    def test_headbutt_meta_and_english_short_effect(self) -> None:
        move = base_move(
            id=29,
            name="headbutt",
            power=70,
            accuracy=100,
            pp=15,
            type=named("normal", 1),
            damage_class="physical",
            effect_chance=30,
            effect="Inflicts regular damage.  Has a chance to make the target flinch.",
            short_effect="Has a chance to make the target flinch.",
            target="selected-pokemon",
            ailment="none",
            ailment_chance=0,
            flinch_chance=30,
            stat_chance=0,
            drain=0,
            healing=0,
            contest_type="tough",
            contest_effect_id=9,
        )
        props = move_props(move)
        self.assertEqual(props["type"], "normal")
        self.assertEqual(props["damage_class"], "physical")
        self.assertEqual(props["contest_type"], "tough")
        self.assertEqual(props["contest_effect_id"], 9)
        self.assertEqual(props["flinch_chance"], 30)
        self.assertEqual(props["effect_chance"], 30)
        self.assertEqual(props["target"], "selected-pokemon")
        self.assertEqual(props["short_effect"], "Has a chance to make the target flinch.")
        self.assertIn("flinch", props["effect"])


if __name__ == "__main__":
    unittest.main()
