"""Read-only agent questions against the ingested battle pilot."""
import os
import unittest

from pokegraph import PokeGraphClient
from pokegraph.agent import BattleQuestionAgent


@unittest.skipUnless(os.getenv('POKEGRAPH_AGENT_INTEGRATION') == '1', 'Opt in with POKEGRAPH_AGENT_INTEGRATION=1; queries are read-only')
class AgentQueryIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_question_routing_and_evidence(self):
        async with PokeGraphClient.from_environment() as client:
            agent = BattleQuestionAgent(client)
            clarified = await agent.ask('What is Blue\'s first team?')
            self.assertEqual(clarified['status'], 'needs_clarification')
            self.assertEqual(clarified['tool_calls'], [])

            team = await agent.ask('What team does Blue use in the first battle in Japanese Red if I chose Bulbasaur?')
            self.assertEqual(team['status'], 'answered')
            self.assertIn('Charmander', team['answer'])
            self.assertEqual(team['evidence'][0]['query_id'], 'battles.team_for_battle')
            self.assertTrue(team['evidence'][0]['rows'])

            location = await agent.ask('Where does the first battle happen in Japanese Red?')
            self.assertIn('Professor Oak', location['answer'])
            self.assertEqual(location['evidence'][0]['query_id'], 'battles.context_for_battle')

            encounters = await agent.ask('Which Pokemon can I encounter on Route 22 in Japanese Red?')
            self.assertEqual(encounters['evidence'][0]['query_id'], 'encounters.pokemon_in_region')
            self.assertTrue(all(all(e['location_name'] == 'kanto-route-22' for e in p['encounters']) for p in encounters['evidence'][0]['rows']))

            matchup = await agent.ask('Which Pokemon have a type advantage against Blue in the optional second Route 22 battle in Japanese Green if I chose Charmander?')
            self.assertEqual(matchup['status'], 'answered')
            self.assertEqual(matchup['evidence'][0]['query_id'], 'battles.regional_candidates_for_battle')
            self.assertTrue(all({location['name'] for location in p['locations']} == {'kanto-route-22'} for p in matchup['evidence'][0]['rows']))
            self.assertNotIn('lapras', {p['pokemon_name'] for p in matchup['evidence'][0]['rows']})
            self.assertIn('Generation I chart accuracy', matchup['answer'])

            outcome = await agent.ask('Do I have to win the first battle in Japanese Red to continue?')
            self.assertEqual(outcome['status'], 'answered')
            self.assertIn('not required', outcome['answer'])
            self.assertEqual(outcome['evidence'][0]['query_id'], 'battles.context_for_battle')

            unsupported = await agent.ask('What should I catch to guarantee I beat Blue?')
            self.assertEqual(unsupported['status'], 'needs_clarification')
            self.assertEqual(unsupported['tool_calls'], [])
