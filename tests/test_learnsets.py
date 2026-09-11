from __future__ import annotations

import unittest

from pokegraph.sources.models import PokemonMoveEntry, VersionGroupDetail
from pokegraph_ingest.writes.learnsets import _learnset_entry_id, learnset_entry_rows
from pokegraph_ingest.writes.pokemon import relationship_rows

from tests.model_fixtures import detail, named, pokemon_with_moves, provenance


class LearnsetEntryRowsTests(unittest.TestCase):
    def test_multiple_methods_and_version_groups(self) -> None:
        pokemon = pokemon_with_moves(
            [
                PokemonMoveEntry(
                    move=named("thunderbolt", 85),
                    version_group_details=(
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("level-up", 1),
                            level=26,
                            order=1,
                        ),
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("machine", 4),
                            level=0,
                            order=None,
                        ),
                        detail(
                            version_group=("red-blue", 1),
                            method=("level-up", 1),
                            level=26,
                            order=2,
                        ),
                    ),
                ),
                PokemonMoveEntry(
                    move=named("quick-attack", 98),
                    version_group_details=(
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("level-up", 1),
                            level=13,
                            order=1,
                        ),
                    ),
                ),
            ]
        )
        rows = learnset_entry_rows(pokemon)

        self.assertEqual(len(rows), 4)
        ids = {row["id"] for row in rows}
        self.assertEqual(len(ids), 4)

        tb_machine = next(r for r in rows if r["learn_method_name"] == "machine")
        self.assertEqual(tb_machine["move_name"], "thunderbolt")
        self.assertEqual(tb_machine["version_group_name"], "heartgold-soulsilver")
        self.assertEqual(tb_machine["level_learned_at"], 0)
        self.assertIsNone(tb_machine["order"])
        self.assertEqual(tb_machine["source_url"], "https://pokeapi.co/api/v2/pokemon/25/")
        self.assertEqual(tb_machine["source_version"], "unavailable")
        self.assertEqual(tb_machine["retrieved_at"], pokemon.provenance.retrieved_at.isoformat())

        levels = sorted(
            r["level_learned_at"]
            for r in rows
            if r["move_name"] == "thunderbolt" and r["learn_method_name"] == "level-up"
        )
        self.assertEqual(levels, [26, 26])

        orders = {
            (r["version_group_name"], r["order"])
            for r in rows
            if r["move_name"] == "thunderbolt" and r["learn_method_name"] == "level-up"
        }
        self.assertEqual(orders, {("heartgold-soulsilver", 1), ("red-blue", 2)})

    def test_different_levels_produce_distinct_ids(self) -> None:
        pokemon = pokemon_with_moves(
            [
                PokemonMoveEntry(
                    move=named("thunder-shock", 84),
                    version_group_details=(
                        detail(version_group=("red-blue", 1), method=("level-up", 1), level=1, order=1),
                        detail(version_group=("red-blue", 1), method=("level-up", 1), level=9, order=2),
                    ),
                ),
            ]
        )
        rows = learnset_entry_rows(pokemon)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["id"], rows[1]["id"])
        self.assertEqual(
            rows[0]["id"],
            _learnset_entry_id(25, 84, 1, 1, rows[0]["level_learned_at"], rows[0]["order"]),
        )

    def test_reextraction_is_stable(self) -> None:
        pokemon = pokemon_with_moves(
            [
                PokemonMoveEntry(
                    move=named("thunderbolt", 85),
                    version_group_details=(
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("machine", 4),
                            level=0,
                            order=None,
                        ),
                    ),
                ),
            ],
            provenance=provenance(),
        )
        first = learnset_entry_rows(pokemon)
        second = learnset_entry_rows(pokemon)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["id"], "25:85:10:4:0:")

    def test_skips_incomplete_details(self) -> None:
        pokemon = pokemon_with_moves(
            [
                PokemonMoveEntry(
                    move=named("splash", 150),
                    version_group_details=(
                        VersionGroupDetail(
                            version_group=named("x-y", None, url=""),
                            move_learn_method=named("level-up", 1),
                            level_learned_at=1,
                            order=1,
                        ),
                    ),
                ),
            ]
        )
        self.assertEqual(learnset_entry_rows(pokemon), [])


class CanLearnSimplificationTests(unittest.TestCase):
    def test_can_learn_is_unique_per_move(self) -> None:
        pokemon = pokemon_with_moves(
            [
                PokemonMoveEntry(
                    move=named("thunderbolt", 85),
                    version_group_details=(
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("level-up", 1),
                            level=26,
                            order=1,
                        ),
                        detail(
                            version_group=("heartgold-soulsilver", 10),
                            method=("machine", 4),
                            level=0,
                            order=None,
                        ),
                    ),
                ),
            ]
        )
        _types, _abilities, moves = relationship_rows(pokemon)
        self.assertEqual(moves, [{"id": 85, "name": "thunderbolt"}])


if __name__ == "__main__":
    unittest.main()
