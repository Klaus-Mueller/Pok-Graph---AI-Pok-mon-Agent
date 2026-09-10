from __future__ import annotations

import unittest
from types import SimpleNamespace

from pokegraph_ingest.writes.moves import move_props


def _named(name: str, resource_id: int) -> SimpleNamespace:
    return SimpleNamespace(name=name, url=f"https://pokeapi.co/api/v2/resource/{resource_id}/")


def _effect_entry(lang: str, effect: str, short_effect: str) -> SimpleNamespace:
    return SimpleNamespace(
        language=_named(lang, 9 if lang == "en" else 5),
        effect=effect,
        short_effect=short_effect,
    )


def _base_move(**overrides: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "id": 1,
        "name": "pound",
        "power": 40,
        "accuracy": 100,
        "pp": 35,
        "priority": 0,
        "type": _named("normal", 1),
        "damage_class": _named("physical", 2),
        "effect_chance": None,
        "effect_entries": [],
        "target": _named("selected-pokemon", 10),
        "meta": None,
        "contest_type": None,
        "contest_effect": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class MovePropsTests(unittest.TestCase):
    def test_thunderbolt_like_move(self) -> None:
        move = _base_move(
            id=85,
            name="thunderbolt",
            power=90,
            accuracy=100,
            pp=15,
            type=_named("electric", 13),
            damage_class=_named("special", 3),
            effect_chance=10,
            effect_entries=[
                _effect_entry(
                    "en",
                    "Inflicts regular damage.  Has a 10% chance to paralyze the target.",
                    "Has a 10% chance to paralyze the target.",
                ),
            ],
            meta=SimpleNamespace(
                ailment=_named("paralysis", 1),
                ailment_chance=10,
                flinch_chance=0,
                stat_chance=0,
                drain=0,
                healing=0,
                min_hits=None,
                max_hits=None,
                min_turns=None,
                max_turns=None,
            ),
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

    def test_status_move_null_power_and_accuracy(self) -> None:
        move = _base_move(
            id=86,
            name="thunder-wave",
            power=None,
            accuracy=90,
            pp=20,
            type=_named("electric", 13),
            damage_class=_named("status", 1),
        )
        props = move_props(move)
        self.assertIsNone(props["power"])
        self.assertEqual(props["accuracy"], 90)
        self.assertEqual(props["damage_class"], "status")
        self.assertEqual(props["effect"], "")
        self.assertEqual(props["short_effect"], "")
        self.assertIsNone(props["flinch_chance"])

    def test_missing_type_yields_null_type_id(self) -> None:
        move = _base_move(type=None, damage_class=_named("physical", 2))
        props = move_props(move)
        self.assertEqual(props["type"], "")
        self.assertIsNone(props["type_id"])
        self.assertEqual(props["damage_class"], "physical")

    def test_headbutt_meta_and_english_short_effect(self) -> None:
        move = _base_move(
            id=29,
            name="headbutt",
            power=70,
            accuracy=100,
            pp=15,
            type=_named("normal", 1),
            damage_class=_named("physical", 2),
            effect_chance=30,
            effect_entries=[
                _effect_entry("fr", "Inflige des dégats.", "A une chance d'apeurer."),
                _effect_entry(
                    "en",
                    "Inflicts regular damage.  Has a chance to make the target flinch.",
                    "Has a chance to make the target flinch.",
                ),
            ],
            target=_named("selected-pokemon", 10),
            meta=SimpleNamespace(
                ailment=_named("none", 0),
                ailment_chance=0,
                flinch_chance=30,
                stat_chance=0,
                drain=0,
                healing=0,
                min_hits=None,
                max_hits=None,
                min_turns=None,
                max_turns=None,
            ),
            contest_type=_named("tough", 5),
            contest_effect=SimpleNamespace(url="https://pokeapi.co/api/v2/contest-effect/9/"),
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

    def test_missing_english_effect_entries(self) -> None:
        move = _base_move(
            effect_entries=[
                _effect_entry("fr", "Effet français.", "Court français."),
            ],
        )
        props = move_props(move)
        self.assertEqual(props["effect"], "")
        self.assertEqual(props["short_effect"], "")


if __name__ == "__main__":
    unittest.main()
