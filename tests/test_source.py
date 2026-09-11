from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from pokegraph.sources.cache import DiskCache
from pokegraph.sources.convert import english_effect, normalize_move, normalize_pokemon
from pokegraph.sources.models import SOURCE_VERSION_UNAVAILABLE, Provenance
from pokegraph.sources.serde import pokemon_from_dict, pokemon_to_dict


def _named(name: str, resource_id: int) -> SimpleNamespace:
    return SimpleNamespace(name=name, url=f"https://pokeapi.co/api/v2/resource/{resource_id}/")


class ConvertTests(unittest.TestCase):
    def test_normalize_pokemon_ids_from_urls(self) -> None:
        raw = SimpleNamespace(
            id=25,
            name="pikachu",
            base_experience=112,
            height=4,
            weight=60,
            is_default=True,
            species=_named("pikachu", 25),
            types=[SimpleNamespace(type=_named("electric", 13), slot=1)],
            abilities=[SimpleNamespace(ability=_named("static", 9), slot=1, is_hidden=False)],
            moves=[
                SimpleNamespace(
                    move=_named("thunderbolt", 85),
                    version_group_details=[
                        SimpleNamespace(
                            version_group=_named("heartgold-soulsilver", 10),
                            move_learn_method=_named("level-up", 1),
                            level_learned_at=26,
                            order=1,
                        )
                    ],
                )
            ],
        )
        model = normalize_pokemon(
            raw,
            Provenance(
                source_url="https://pokeapi.co/api/v2/pokemon/25/",
                retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        )
        self.assertEqual(model.types[0].type.id, 13)
        self.assertEqual(model.moves[0].version_group_details[0].version_group.id, 10)

    def test_english_effect_prefers_en(self) -> None:
        raw = SimpleNamespace(
            effect_entries=[
                SimpleNamespace(language=_named("fr", 5), effect="fr", short_effect="fr-s"),
                SimpleNamespace(language=_named("en", 9), effect="en-long", short_effect="en-short"),
            ]
        )
        self.assertEqual(english_effect(raw), ("en-long", "en-short"))

    def test_normalize_move_provenance(self) -> None:
        raw = SimpleNamespace(
            id=85,
            name="thunderbolt",
            power=90,
            accuracy=100,
            pp=15,
            priority=0,
            type=_named("electric", 13),
            damage_class=_named("special", 3),
            effect_chance=10,
            effect_entries=[
                SimpleNamespace(language=_named("en", 9), effect="zap", short_effect="paralyze"),
            ],
            target=_named("selected-pokemon", 10),
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
            contest_type=None,
            contest_effect=None,
        )
        move = normalize_move(
            raw,
            Provenance(
                source_url="https://pokeapi.co/api/v2/move/85/",
                retrieved_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                source_version=SOURCE_VERSION_UNAVAILABLE,
            ),
        )
        self.assertEqual(move.short_effect, "paralyze")
        self.assertEqual(move.provenance.source_version, "unavailable")


class DiskCacheTests(unittest.TestCase):
    def test_hit_preserves_retrieved_at(self) -> None:
        with TemporaryDirectory() as tmp:
            cache = DiskCache(Path(tmp))
            retrieved = datetime(2026, 3, 4, 5, 6, tzinfo=timezone.utc)
            pokemon = normalize_pokemon(
                SimpleNamespace(
                    id=25,
                    name="pikachu",
                    base_experience=112,
                    height=4,
                    weight=60,
                    is_default=True,
                    species=_named("pikachu", 25),
                    types=[],
                    abilities=[],
                    moves=[],
                ),
                Provenance(
                    source_url="https://pokeapi.co/api/v2/pokemon/25/",
                    retrieved_at=retrieved,
                ),
            )
            payload = pokemon_to_dict(pokemon)
            cache.put(
                "pokemon",
                "pikachu",
                payload,
                retrieved_at=retrieved,
                source_url=pokemon.provenance.source_url,
                source_version=pokemon.provenance.source_version,
                adapter_version="0.1.0",
                payload_hash="abc",
            )
            record = cache.get("pokemon", "pikachu")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.retrieved_at, retrieved)
            restored = pokemon_from_dict(record.data)
            self.assertEqual(restored.provenance.retrieved_at, retrieved)

    def test_expired_entry_is_a_miss(self) -> None:
        with TemporaryDirectory() as tmp:
            cache = DiskCache(Path(tmp), ttl_s=1)
            old = datetime(2020, 1, 1, tzinfo=timezone.utc)
            cache.put(
                "pokemon",
                25,
                {"id": 25},
                retrieved_at=old,
                source_url="https://pokeapi.co/api/v2/pokemon/25/",
                source_version="unavailable",
                adapter_version="0.1.0",
                payload_hash=None,
            )
            self.assertIsNone(cache.get("pokemon", 25))


if __name__ == "__main__":
    unittest.main()
