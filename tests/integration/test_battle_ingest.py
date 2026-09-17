"""Explicit opt-in; all battle writes are in a transaction that is rolled back."""
from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from pathlib import Path

from pokegraph.config import Neo4jSettings
from pokegraph.graph.connection import create_driver
from pokegraph.sources.battles import BattleEncounter
from pokegraph_ingest.writes.battles import graph_rows, write_battle

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'data/corpora/red-green-blue-first-battle'


@unittest.skipUnless(os.getenv('POKEGRAPH_BATTLE_INTEGRATION') == '1', 'Opt in with POKEGRAPH_BATTLE_INTEGRATION=1; writes are rolled back')
class BattleIngestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_ingestion_queries_repetition_and_rollback(self):
        battles = [BattleEncounter.from_dict(json.loads(s)) for s in (CORPUS/'battles.jsonl').read_text().splitlines()]
        settings = Neo4jSettings.from_environment()
        all_nodes = {}
        for b in battles:
            for label, nodes in graph_rows(b)['nodes'].items():
                all_nodes.setdefault(label,set()).update(n['id'] for n in nodes)
        async with create_driver(settings) as driver:
            async with driver.session(database=settings.database) as session:
                before = {}
                for label, ids in all_nodes.items():
                    result = await session.run(f'MATCH (n:{label}) WHERE n.id IN $ids RETURN n.id AS id,properties(n) AS props ORDER BY id',ids=sorted(ids))
                    before[label] = await result.data()
                tx = await session.begin_transaction()
                try:
                    # Observe canonical properties, then ensure they never change.
                    result = await tx.run('MATCH (n) WHERE n:Pokemon OR n:Move OR n:GameVersion RETURN labels(n) AS labels,n.id AS id,properties(n) AS props ORDER BY id,labels')
                    canonical_before = await result.data()
                    for b in battles:
                        await write_battle(tx,b)
                    # Repeat a small and a full six-member team.
                    await write_battle(tx,battles[0])
                    await write_battle(tx,battles[-1])
                    for label, ids in all_nodes.items():
                        result = await tx.run(f'MATCH (n:{label}) WHERE n.id IN $ids RETURN count(n) AS count',ids=sorted(ids))
                        self.assertEqual((await result.single())['count'],len(ids),label)
                    result = await tx.run('MATCH (p:TrainerPokemon)-[r:KNOWS_MOVE]->(:Move) WHERE p.id IN $ids RETURN count(r) AS count', ids=sorted(all_nodes['TrainerPokemon']))
                    self.assertEqual((await result.single())['count'],702)
                    result = await tx.run('MATCH (n) WHERE n.id IN $ids OPTIONAL MATCH (n)-[r:HAS_SOURCE|HAS_MOVE|USES_MOVE]->() RETURN count(r) AS count',ids=sorted(set().union(*all_nodes.values())))
                    self.assertEqual((await result.single())['count'],0)
                    result = await tx.run((ROOT/'queries/battles/verify_ingestion.cypher').read_text(), battle_ids=[b.id for b in battles])
                    for check in await result.data():
                        self.assertEqual(check['actual'],check['expected'],check['check'])
                    def query(name):
                        return (ROOT/'queries/battles'/name).read_text()
                    for version in (44,45):
                        result = await tx.run(query('list_battles.cypher'),trainer_id='trainer:blue',version_id=version,skip=0,limit=50)
                        listing = await result.data()
                        self.assertEqual([b['battle_order'] for b in listing],list(range(1,9)))
                        self.assertIsNone(listing[0]['is_optional'])
                        for starter, opponent in ((1,'charmander'),(4,'squirtle'),(7,'bulbasaur')):
                            result = await tx.run(query('team_for_battle.cypher'),trainer_id='trainer:blue',version_id=version,battle_key='first',starter_species_id=starter,skip=0,limit=50)
                            team = await result.data()
                            self.assertEqual(len(team),2)
                            self.assertEqual({p['pokemon_name'] for p in team},{opponent})
                            self.assertEqual([p['move_slot'] for p in team], [1, 2])
                    result = await tx.run(query('version_context.cypher'),battle_id=battles[0].id)
                    self.assertEqual((await result.single())['version_group_id'],28)
                    # Reject a changed canonical target rather than retaining both edges.
                    b = battles[0]
                    v,p,m = b.variants[0],b.variants[0].members[0],b.variants[0].members[0].moves[0]
                    changed = replace(m,move=p.moves[1].move)
                    bad = replace(b,variants=[replace(v,members=[replace(p,moves=[changed,*p.moves[1:]])]),*b.variants[1:]])
                    with self.assertRaisesRegex(ValueError,'explicit reconciliation'):
                        await write_battle(tx,bad)
                    bad = replace(b,version_group=replace(b.version_group,id=9999999))
                    with self.assertRaisesRegex(ValueError,'VersionGroup'):
                        await write_battle(tx,bad)
                    result = await tx.run('MATCH (n) WHERE n:Pokemon OR n:Move OR n:GameVersion RETURN labels(n) AS labels,n.id AS id,properties(n) AS props ORDER BY id,labels')
                    self.assertEqual(await result.data(),canonical_before)
                finally:
                    await tx.rollback()
                # No persistent battle changes.
                for label, ids in all_nodes.items():
                    result = await session.run(f'MATCH (n:{label}) WHERE n.id IN $ids RETURN n.id AS id,properties(n) AS props ORDER BY id',ids=sorted(ids))
                    self.assertEqual(await result.data(),before[label])


if __name__ == '__main__':
    unittest.main()
