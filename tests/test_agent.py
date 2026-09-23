from pathlib import Path
from types import SimpleNamespace
import unittest

from pokegraph.agent import BattleQuestionAgent
from pokegraph.graph.registry import QueryRegistry


class FakeGraph:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    async def execute(self, query_id, **params):
        self.calls.append((query_id, params))
        return SimpleNamespace(query_id=query_id, rows=self.rows)

    async def open(self):
        return None

    async def close(self):
        return None


class BattleQuestionAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_asks_for_game_starter_and_encounter(self):
        graph = FakeGraph()
        agent = BattleQuestionAgent(graph)
        result = await agent.ask("What is Blue's team?")
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertIn('game_version', result['missing_information'])
        self.assertEqual(graph.calls, [])
        result = await agent.ask("What is Blue's second team in Japanese Red?")
        self.assertIn('player_starter', result['missing_information'])
        result = await agent.ask("Which Pokemon have type advantage on Route 22 in Japanese Red if I chose Bulbasaur?")
        self.assertIn('battle_key', result['missing_information'])
        self.assertEqual(graph.calls, [])

    async def test_team_question_routes_to_read_query_and_returns_evidence(self):
        graph = FakeGraph([
            {'member_id':'m1','pokemon_name':'squirtle','level':8,'member_slot':1,'move_name':'tackle','move_slot':1},
            {'member_id':'m1','pokemon_name':'squirtle','level':8,'member_slot':1,'move_name':'tail-whip','move_slot':2},
        ])
        result = await BattleQuestionAgent(graph).ask(
            'What is Blue team in the second optional battle in Japanese Red if I chose Bulbasaur?')
        self.assertEqual(result['status'], 'answered')
        self.assertIn('Squirtle (Lv. 8)', result['answer'])
        self.assertIn('Tackle, Tail-Whip', result['answer'])
        self.assertEqual(graph.calls[0][0], 'battles.team_for_battle')
        self.assertEqual(graph.calls[0][1]['version_id'], 44)
        self.assertEqual(graph.calls[0][1]['starter_species_id'], 1)
        self.assertEqual(result['evidence'][0]['rows'], graph.rows)

    async def test_q14_defaults_only_to_route22_and_states_limitations(self):
        graph = FakeGraph([{'pokemon_name':'pikachu','members_covered':1,'matchups':[]}])
        result = await BattleQuestionAgent(graph).ask(
            'Which Pokemon have a type advantage against Blue in the optional second Route 22 battle in Japanese Green if I chose Charmander?')
        self.assertEqual(result['status'], 'answered')
        query, params = graph.calls[0]
        self.assertEqual(query, 'battles.regional_candidates_for_battle')
        self.assertEqual(params['version_id'], 45)
        self.assertEqual(params['starter_species_id'], 4)
        self.assertEqual(params['accessible_location_names'], 'kanto-route-22')
        self.assertTrue(result['assumptions'])
        self.assertIn('Generation I chart accuracy', result['answer'])

    async def test_empty_or_broad_location_is_never_silently_expanded(self):
        graph = FakeGraph()
        agent = BattleQuestionAgent(graph)
        result = await agent.ask('Which Pokemon have an advantage against Blue second optional battle in Japanese Red if I chose Squirtle?')
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertEqual(graph.calls, [])
        result = await agent.ask('Which Pokemon have an advantage against Blue second optional Route 22 battle in Japanese Red if I chose Squirtle?', accessible_location_names=[])
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertEqual(graph.calls, [])

    async def test_route22_ambiguous_or_nonpilot_battle_is_not_guessed(self):
        graph = FakeGraph()
        agent = BattleQuestionAgent(graph)
        result = await agent.ask('Which Pokemon have an advantage against Blue on Route 22 in Japanese Red if I chose Bulbasaur?')
        self.assertIn('battle_key', result['missing_information'])
        result = await agent.ask('Which Pokemon counter Blue on Route 22 in Japanese Red in the seventh battle if I chose Bulbasaur?')
        self.assertIn('optional second', result['answer'])
        self.assertEqual(graph.calls, [])

    async def test_outcome_uses_local_text_and_citation(self):
        graph = FakeGraph([{'victory_required_for_progression':False,'progression_notes':'The story progresses either way.'}])
        result = await BattleQuestionAgent(graph).ask('Do I have to win the first battle in Japanese Red to continue?')
        self.assertEqual(result['status'], 'answered')
        self.assertIn('not required', result['answer'])
        self.assertEqual(result['evidence'][0]['query_id'], 'battles.context_for_battle')
        self.assertEqual(graph.calls[0][1]['battle_key'], 'first')

    async def test_unknown_outcome_preserves_insufficient_evidence(self):
        graph = FakeGraph([{'victory_required_for_progression':None,'progression_notes':None}])
        result = await BattleQuestionAgent(graph).ask('Do I have to win the sixth battle in Japanese Red?')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertIn('does not establish', result['answer'])

    async def test_location_question_routes_to_battle_context_query(self):
        graph = FakeGraph([{'battle_name':'first battle','location_name':"Professor Oak's Laboratory",'canonical_location_name':'pallet-town','progression_status':'partial','progression_notes':'Winning is not mandatory.'}])
        result = await BattleQuestionAgent(graph).ask('Where does the first battle happen in Japanese Red?')
        self.assertEqual(graph.calls[0][0], 'battles.context_for_battle')
        self.assertIn('Professor Oak', result['answer'])
        self.assertIn('Pallet Town', result['answer'])
        self.assertIn('Winning is not mandatory', result['answer'])

    async def test_route22_encounter_question_uses_only_selected_location(self):
        graph = FakeGraph([{'pokemon_name':'rattata'}, {'pokemon_name':'spearow'}])
        result = await BattleQuestionAgent(graph).ask('Which Pokémon can I encounter on Route 22 in Japanese Green?')
        self.assertEqual(graph.calls[0][0], 'encounters.pokemon_in_region')
        self.assertEqual(graph.calls[0][1]['accessible_location_names'], 'kanto-route-22')
        self.assertEqual(graph.calls[0][1]['version_id'], 45)
        self.assertIn('Rattata, Spearow', result['answer'])

    async def test_unsupported_questions_ask_instead_of_guess(self):
        graph = FakeGraph()
        result = await BattleQuestionAgent(graph).ask('What should I catch to guarantee I win?')
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertEqual(graph.calls, [])

    def test_predefined_queries_are_registered_and_parameters_validated(self):
        registry = QueryRegistry.load()
        for query in ('battles.team_for_battle','battles.regional_candidates_for_battle','encounters.pokemon_in_region'):
            self.assertIn(query, registry.specs)
        spec = registry.get('battles.regional_candidates_for_battle')
        params = {p.name:p.type for p in spec.params}
        self.assertEqual(params['accessible_location_names'], 'string')
        with self.assertRaises(Exception):
            registry.bind('battles.regional_candidates_for_battle', {'unexpected':'MATCH (n)'} )
