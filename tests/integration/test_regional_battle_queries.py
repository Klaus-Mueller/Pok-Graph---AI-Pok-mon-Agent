"""Read-only checks against the ingested Red/Green pilot; no graph writes."""
import os
from pathlib import Path
import unittest

from pokegraph.graph.connection import GraphConnection

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.getenv('POKEGRAPH_REGIONAL_INTEGRATION') == '1', 'Opt in to read-only Neo4j tests')
class RegionalBattleQueries(unittest.IsolatedAsyncioTestCase):
    async def test_regional_candidates_and_type_factors(self):
        async with GraphConnection.from_environment() as graph:
            async def query(path, **params):
                return await graph.execute_read((ROOT / 'queries' / path).read_text(), params, timeout_s=60)

            chart = await graph.execute_read('MATCH (a:Type)-[r:DAMAGE_TO]->(d:Type) RETURN a.name AS a,d.name AS d,r.factor AS factor', {})
            factors = {(r['a'], r['d']): r['factor'] for r in chart}
            enriched = {r['a'] for r in chart}
            candidate_types = await graph.execute_read('MATCH (p:Pokemon)-[:HAS_TYPE]->(t:Type) RETURN p.id AS id,collect(t.name) AS types', {})
            types = {r['id']: r['types'] for r in candidate_types}
            for version in (44, 45):
                discovery = await query('encounters/pokemon_in_region.cypher', version_id=version, region_name='kanto', accessible_location_names=['kanto-route-22'], skip=0, limit=10000)
                ids = {r['pokemon_id'] for r in discovery}
                self.assertTrue(ids)
                self.assertEqual(len(ids), len(discovery))
                self.assertNotIn('lapras', {r['pokemon_name'] for r in discovery})
                for row in discovery:
                    self.assertEqual(row['availability_scope'], 'explicit_locations')
                    self.assertTrue(all(e['location_name'] == 'kanto-route-22' for e in row['encounters']))
                independent = await graph.execute_read('''MATCH (p:Pokemon)-[:HAS_ENCOUNTER]->(e:Encounter)-[:IN_VERSION]->(:GameVersion {id:$version})
                    MATCH (e)-[:AT_LOCATION_AREA]->(:LocationArea)-[:PART_OF_LOCATION]->(:Location {name:'kanto-route-22'})-[:IN_REGION]->(:Region {name:'kanto'})
                    RETURN DISTINCT p.id AS id''', {'version': version})
                self.assertEqual(ids, {r['id'] for r in independent})
                for starter in (1, 4, 7):
                    params = dict(version_id=version, trainer_id='trainer:blue', battle_key='second-optional', starter_species_id=starter, accessible_location_names=['kanto-route-22'], skip=0, limit=10000)
                    rows = await query('battles/regional_candidates_for_battle.cypher', **params)
                    self.assertEqual({r['pokemon_id'] for r in rows}, ids)
                    self.assertEqual(len(rows), len(ids))
                    self.assertEqual([(r['members_covered'], r['pokemon_id']) for r in rows], sorted([(r['members_covered'], r['pokemon_id']) for r in rows], key=lambda x: (-x[0], x[1])))
                    team = await query('battles/team_for_battle.cypher', **params)
                    members = {r['member_id'] for r in team}
                    self.assertEqual(len(members), 2)
                    for row in rows:
                        self.assertEqual(row['region_name'], 'kanto')
                        self.assertEqual(row['availability_scope'], 'explicit_locations')
                        self.assertEqual({l['name'] for l in row['locations']}, {'kanto-route-22'})
                        self.assertFalse(row['moves_checked'])
                        self.assertFalse(row['progression_checked'])
                        self.assertEqual(row['team_size'], 2)
                        self.assertEqual({m['member_id'] for m in row['matchups']}, members)
                        coverage = 0
                        for member in row['matchups']:
                            advantage = False
                            self.assertEqual({o['attacking_type'] for o in member['type_options']}, set(types[row['pokemon_id']]))
                            for option in member['type_options']:
                                attack = option['attacking_type']
                                expected = 1.0 if attack in enriched else None
                                for defense in member['defender_types']:
                                    if expected is not None:
                                        expected *= factors.get((attack, defense.lower()), 1.0)
                                self.assertEqual(option['factor'], expected)
                                advantage |= expected is not None and expected > 1
                            self.assertEqual(member['advantage'], advantage)
                            coverage += advantage
                        self.assertEqual(row['members_covered'], coverage)
                    page = await query('battles/regional_candidates_for_battle.cypher', **{**params, 'skip': 1, 'limit': 2})
                    self.assertEqual(page, rows[1:3])
            empty = await query('encounters/pokemon_in_region.cypher', version_id=44, region_name='nonexistent-test-region', accessible_location_names=['kanto-route-22'], skip=0, limit=50)
            self.assertEqual(empty, [])
            empty = await query('battles/regional_candidates_for_battle.cypher', **{**params, 'starter_species_id': -1})
            self.assertEqual(empty, [])

            for allowed in ([], ['nonexistent-test-location']):
                self.assertEqual(await query('encounters/pokemon_in_region.cypher', version_id=44, region_name='kanto', accessible_location_names=allowed, skip=0, limit=10000), [])
                self.assertEqual(await query('battles/regional_candidates_for_battle.cypher', **{**params, 'accessible_location_names': allowed}), [])
            # Multiple allowed locations are a union; duplicate names must not duplicate candidates.
            union = set()
            for allowed in (['kanto-route-22'], ['saffron-city']):
                rows = await query('encounters/pokemon_in_region.cypher', version_id=44, region_name='kanto', accessible_location_names=allowed, skip=0, limit=10000)
                union.update(r['pokemon_id'] for r in rows)
            allowed = ['kanto-route-22', 'saffron-city', 'kanto-route-22']
            combined = await query('encounters/pokemon_in_region.cypher', version_id=44, region_name='kanto', accessible_location_names=allowed, skip=0, limit=10000)
            self.assertEqual({r['pokemon_id'] for r in combined}, union)
            self.assertEqual(len(combined), len(union))
            compared = await query('battles/regional_candidates_for_battle.cypher', **{**params, 'version_id': 44, 'accessible_location_names': allowed})
            self.assertEqual({r['pokemon_id'] for r in compared}, union)
            self.assertEqual(len(compared), len(union))
