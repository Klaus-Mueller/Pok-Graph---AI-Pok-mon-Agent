from __future__ import annotations

import unittest
from types import SimpleNamespace

from pokegraph_ingest.writes.moves import move_props


def _named(name: str, resource_id: int) -> SimpleNamespace:
    return SimpleNamespace(name=name, url=f"https://pokeapi.co/api/v2/resource/{resource_id}/")


class MovePropsTests(unittest.TestCase):
    def test_thunderbolt_like_move(self) -> None:
        move = SimpleNamespace(
            id=85,
            name="thunderbolt",
            power=90,
            accuracy=100,
            pp=15,
            priority=0,
            type=_named("electric", 13),
            damage_class=_named("special", 3),
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

    def test_status_move_null_power_and_accuracy(self) -> None:
        move = SimpleNamespace(
            id=86,
            name="thunder-wave",
            power=None,
            accuracy=90,
            pp=20,
            priority=0,
            type=_named("electric", 13),
            damage_class=_named("status", 1),
        )
        props = move_props(move)
        self.assertIsNone(props["power"])
        self.assertEqual(props["accuracy"], 90)
        self.assertEqual(props["damage_class"], "status")

    def test_missing_type_yields_null_type_id(self) -> None:
        move = SimpleNamespace(
            id=1,
            name="pound",
            power=40,
            accuracy=100,
            pp=35,
            priority=0,
            type=None,
            damage_class=_named("physical", 2),
        )
        props = move_props(move)
        self.assertEqual(props["type"], "")
        self.assertIsNone(props["type_id"])
        self.assertEqual(props["damage_class"], "physical")


if __name__ == "__main__":
    unittest.main()
