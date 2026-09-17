from __future__ import annotations

import copy
import asyncio
import importlib.util
import json
import unittest
import tempfile
from types import SimpleNamespace
from dataclasses import replace
from pathlib import Path

from pokegraph.sources.battles import BattleEncounter, counts, normalize, parse_party, validate_battle
from pokegraph_ingest.battles import read_inputs, verify_fixture, run
from pokegraph_ingest.writes.battles import graph_rows

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'data/corpora/red-green-blue-first-battle'


class BattleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = read_inputs(CORPUS)
        cls.catalog = json.loads((CORPUS / 'entity-mappings.json').read_text())
        cls.battles = normalize(cls.chunks, cls.catalog)

    def test_counts_roundtrip_and_reviewed_fixture(self):
        self.assertEqual(counts(self.battles), {'Trainer':1,'BattleEncounter':16,'BattleVariant':48,'TrainerPokemon':198,'KNOWS_MOVE':702})
        verify_fixture(CORPUS, self.battles)
        loaded = [BattleEncounter.from_dict(json.loads(s)) for s in (CORPUS/'battles.jsonl').read_text().splitlines()]
        self.assertEqual(loaded, self.battles)

    def test_psychic_and_historical_types_survive(self):
        champion = next(b for b in self.battles if b.game_version.id == 44 and b.battle_order == 8)
        alakazam = champion.variants[0].members[1]
        self.assertEqual([m.move.name for m in alakazam.moves], ['psybeam','psychic','reflect','recover'])
        second = next(b for b in self.battles if b.battle_order == 2)
        self.assertEqual(second.variants[0].members[0].moves[0].observed_type_name, 'Normal')
        self.assertEqual(second.variants[0].members[0].moves[1].move.name, 'sand-attack')
        self.assertTrue(any(m.move.name == 'solar-beam' for b in self.battles for v in b.variants for p in v.members for m in p.moves))

    def test_reject_footer_invalid_pair_and_missing_moves(self):
        original = next(c for c in self.chunks if c.get('player_starter') == 'bulbasaur')
        for text in (original['text']+'\nRetrieved from footer', original['text'].replace('Scratch\nNormal', 'Scratch\nBogus'), original['text'].replace('\nScratch\nNormal\nGrowl\nNormal','')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_party({**original, 'text':text})

    def test_collector_bounds_last_section(self):
        spec = importlib.util.spec_from_file_location('collector', CORPUS/'collect.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        html = '<h2><span id="Last">Last</span></h2><p>Team</p><div class="printfooter">Bad footer</div>'
        self.assertEqual(module.plain(module.section(html,'Last')), 'Team')
        self.assertFalse(any('Retrieved from' in c['text'] for c in self.chunks))

    def test_missing_and_ambiguous_canonical_references(self):
        for key in ('pokemon','species','moves','versions'):
            for duplicate in (False,True):
                catalog = copy.deepcopy(self.catalog)
                if duplicate:
                    catalog[key].append(catalog[key][0])
                else:
                    catalog[key] = []
                with self.subTest(key=key,duplicate=duplicate), self.assertRaises(ValueError):
                    normalize(self.chunks,catalog)

    def test_species_is_resolved_through_edge_not_equal_id(self):
        catalog = copy.deepcopy(self.catalog)
        catalog['pokemon'][0]['species'] = []
        with self.assertRaisesRegex(ValueError,'relationship'):
            normalize(self.chunks,catalog)

    def test_missing_or_duplicate_starter_is_rejected(self):
        chunks = copy.deepcopy(self.chunks)
        parties = [c for c in chunks if c.get('battle_order') == 1 and 'player_starter' in c]
        parties[1]['player_starter'] = parties[0]['player_starter']
        with self.assertRaises(ValueError):
            normalize(chunks,self.catalog)

    def test_level_slot_and_ids_validated_on_loading(self):
        base = self.battles[0].to_dict()
        for key,value in [('level',0),('slot',2),('id','unstable'),('level',True)]:
            d = copy.deepcopy(base)
            d['variants'][0]['members'][0][key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                BattleEncounter.from_dict(d)

    def test_no_shared_members_across_starters_or_versions(self):
        ids = [p.id for b in self.battles for v in b.variants for p in v.members]
        self.assertEqual(len(ids),len(set(ids)))
        for b in self.battles:
            self.assertEqual(b.version_group.id,28)
            rows = graph_rows(b)
            self.assertNotIn('Pokemon',rows['nodes'])
            self.assertNotIn(('BattleEncounter','HAS_MEMBER','TrainerPokemon'),rows['edges'])

    def test_progression_and_locations_preserve_unknown(self):
        first = self.battles[0]
        self.assertFalse(first.victory_required_for_progression)
        self.assertIsNone(first.is_optional)
        for b in self.battles:
            if b.battle_order in (1, 6):
                building, city = (("Professor Oak's Laboratory", 'pallet-town')
                                  if b.battle_order == 1 else ('Silph Co.', 'saffron-city'))
                self.assertEqual(b.location_name, building)
                self.assertEqual(b.location.name, city)
                self.assertEqual(b.location_mapping_status, 'resolved')
                edges = graph_rows(b)['edges'][('BattleEncounter', 'AT_LOCATION', 'Location')]
                self.assertEqual(len(edges), 1)
        fifth = next(b for b in self.battles if b.battle_order == 5)
        self.assertEqual(fifth.progression_status,'unknown')
        self.assertIsNone(fifth.victory_required_for_progression)
        third = next(b for b in self.battles if b.battle_order == 3)
        self.assertIn('even after other battles',third.skip_condition_text)

    def test_no_source_or_move_nodes(self):
        for b in self.battles:
            rows = graph_rows(b)
            self.assertEqual(set(rows['nodes']), {'Trainer','BattleEncounter','BattleVariant','TrainerPokemon'})
            self.assertFalse(any(rel in ('HAS_SOURCE','USES_MOVE','HAS_MOVE') for _,rel,_ in rows['edges']))
            self.assertNotIn('evidence', json.dumps(b.to_dict()))
            self.assertNotIn('source_url', json.dumps(b.to_dict()))
            moves = rows['edges'][('TrainerPokemon','KNOWS_MOVE','Move')]
            self.assertTrue(all(set(m['props']) == {'id','slot','observed_type_name'} for m in moves))

    def test_stable_keys_on_level_correction(self):
        b = self.battles[0]
        v,p = b.variants[0],b.variants[0].members[0]
        changed = replace(b,variants=[replace(v,members=[replace(p,level=6)]),*b.variants[1:]])
        validate_battle(changed)
        self.assertEqual(graph_rows(b)['edges'], graph_rows(changed)['edges'])

    def test_check_rejects_payload_drift_without_mutating_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('chunks.jsonl','sources.json','entity-mappings.json','battle-fixture.json','questions.jsonl','battles.jsonl'):
                (root/name).write_bytes((CORPUS/name).read_bytes())
            records = [b.to_dict() for b in self.battles]
            records[0]['variants'][0]['members'][0]['level'] = 6
            changed = ''.join(json.dumps(r)+'\n' for r in records)
            (root/'battles.jsonl').write_text(changed)
            with self.assertRaisesRegex(ValueError,'differs'):
                asyncio.run(run(SimpleNamespace(corpus=root,refresh_mappings=False,write=False,check=True)))
            self.assertEqual((root/'battles.jsonl').read_text(),changed)
            self.assertFalse((root/'battle-validation-report.json').exists())


if __name__ == '__main__':
    unittest.main()
