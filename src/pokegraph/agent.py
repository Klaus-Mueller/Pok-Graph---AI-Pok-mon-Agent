"""Small deterministic tool router for the Red/Green Blue battle pilot.

Language generation is intentionally omitted: the service selects reviewed
read-only Cypher tools, asks for missing parameters, and returns evidence.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from pokegraph.graph.client import PokeGraphClient

STARTERS = {'bulbasaur': 1, 'charmander': 4, 'squirtle': 7}
BATTLES = {
    'first': ('first', 'first battle'),
    'second-optional': ('second', 'second-optional', 'second optional', 'optional second', 'second battle'),
    'third': ('third', 'third battle'), 'fourth': ('fourth', 'fourth battle'),
    'fifth': ('fifth', 'fifth battle'), 'sixth': ('sixth', 'sixth battle'),
    'seventh': ('seventh', 'seventh battle'),
    'eighth-champion': ('champion', 'eighth', 'eighth battle', 'champion battle'),
}
def _game(question: str, supplied: int | None) -> int | None:
    if supplied is not None:
        return supplied if supplied in (44, 45) else None
    q = question.lower().replace('_', '-')
    if 'green-jp' in q or 'green-japan' in q or 'japanese green' in q or 'green (japanese)' in q:
        return 45
    if 'red-jp' in q or 'red-japan' in q or 'japanese red' in q or 'red (japanese)' in q:
        return 44
    return None


def _starter(question: str, supplied: str | None) -> str | None:
    if supplied:
        normalized = supplied.strip().lower()
        return normalized if normalized in STARTERS else None
    q = question.lower()
    matches = [name for name in STARTERS if re.search(rf'\b(?:{name})\b', q)]
    return matches[0] if len(matches) == 1 else None


def _battle(question: str, supplied: str | None, intent: str) -> str | None:
    if supplied:
        return supplied if supplied in BATTLES else None
    q = question.lower()
    # Route 22 has two encounters, so infer only when the user identifies the optional fight.
    if 'route 22' in q and intent == 'regional' and any(x in q for x in ('optional', 'second')):
        return 'second-optional'
    matches = [key for key, aliases in BATTLES.items() if any(alias in q for alias in aliases)]
    if 'route 22' in q and intent == 'regional' and matches and matches[0] == 'second-optional':
        return None
    return matches[0] if len(matches) == 1 else None


def _intent(question: str) -> str:
    q = ''.join(ch for ch in unicodedata.normalize('NFKD', question.lower()) if not unicodedata.combining(ch))
    if any(word in q for word in ('where is', 'where does', 'where do', 'location')) and 'battle' in q:
        return 'location'
    if re.search(r'\b(advantage|counter)\b', q) or any(word in q for word in ('strong against', 'type matchup', 'type advantage')):
        return 'regional' if 'route 22' in q or 'location' in q or 'catch' in q else 'matchup'
    if any(word in q for word in ('team', 'uses', 'use in', 'battle roster', 'pokemon does blue')):
        return 'team'
    if any(word in q for word in ('mandatory', 'have to win', 'need to win', 'lose', 'black out', 'continue the story')):
        return 'outcome'
    if 'route 22' in q and 'advantage' not in q and any(word in q for word in ('which pokemon', 'what pokemon', 'encounter')):
        return 'encounters'
    if 'pokemon' in q and any(word in q for word in ('available', 'encounter', 'catch')):
        return 'regional'
    return 'unsupported'


def _clarify(message: str, missing: list[str]) -> dict[str, Any]:
    return {'status': 'needs_clarification', 'answer': message, 'evidence': [], 'assumptions': [], 'missing_information': missing, 'tool_calls': []}


class BattleQuestionAgent:
    """Routes a bounded question set to predefined Neo4j query tools."""
    def __init__(self, client: PokeGraphClient):
        self.client = client

    async def ask(self, question: str, *, game_version_id: int | None = None,
                  battle_key: str | None = None, player_starter: str | None = None,
                  accessible_location_names: list[str] | None = None) -> dict[str, Any]:
        if not question.strip():
            return _clarify('Please provide a Pokémon question.', ['question'])
        intent = _intent(question)
        if intent == 'unsupported':
            return _clarify('This pilot can answer Blue battle team, Route 22 type-comparison, and first-battle outcome questions. Which one are you asking?', ['supported question type'])

        version = _game(question, game_version_id)
        if version is None:
            return _clarify('Which game do you mean: Japanese Red or Japanese Green?', ['game_version'])
        starter = _starter(question, player_starter)
        battle = _battle(question, battle_key, intent)
        if intent in ('team', 'regional', 'matchup', 'location', 'outcome') and battle is None:
            options = ' (first, second-optional, third, fourth, fifth, sixth, seventh, eighth-champion)' 
            return _clarify('Which Blue encounter do you mean?' + options, ['battle_key'])
        if intent in ('team', 'regional', 'matchup') and starter is None:
            return _clarify('Which Pokémon did you initially choose: Bulbasaur, Charmander, or Squirtle?', ['player_starter'])
        if intent == 'matchup':
            return _clarify('The pilot compares regional candidates for the optional Route 22 encounter only. Is that the battle you mean?', ['battle_key=second-optional', 'accessible locations'])

        if intent == 'team':
            params = {'trainer_id': 'trainer:blue', 'version_id': version,
                      'battle_key': battle, 'starter_species_id': STARTERS[starter], 'skip': 0, 'limit': 100}
            page = await self.client.execute('battles.team_for_battle', **params)
            if not page.rows:
                return {'status':'insufficient_evidence','answer':'No matching team is present in the selected game/battle/starter scope.', 'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':[]}], 'assumptions':[], 'missing_information':['matching ingested battle variant'], 'tool_calls':[page.query_id]}
            members = {}
            for row in page.rows:
                item = members.setdefault(row['member_id'], {'pokemon':row['pokemon_name'],'level':row['level'],'slot':row['member_slot'],'moves':[]})
                move = row.get('move_name')
                if move and move not in item['moves']:
                    item['moves'].append(move)
            team = [members[k] for k in sorted(members, key=lambda k: members[k]['slot'])]
            lines = [f"{m['slot']}. {m['pokemon'].title()} (Lv. {m['level']})" + (f" — {', '.join(move.title() for move in m['moves'])}" if m['moves'] else '') for m in team]
            return {'status':'answered','answer':f"Blue's {battle.replace('-', ' ')} team in {'Japanese Red' if version == 44 else 'Japanese Green'}, if you initially chose {starter.title()}:\n"+'\n'.join(lines), 'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':page.rows}], 'assumptions':[], 'missing_information':[], 'tool_calls':[page.query_id]}

        if intent == 'outcome':
            params = {'trainer_id':'trainer:blue','version_id':version,'battle_key':battle}
            page = await self.client.execute('battles.context_for_battle', **params)
            if not page.rows:
                return {'status':'insufficient_evidence','answer':'No matching battle context is stored for this game and encounter.','evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':[]}],'assumptions':[],'missing_information':['battle outcome/progression data'],'tool_calls':[page.query_id]}
            row = page.rows[0]
            required = row.get('victory_required_for_progression')
            note = row.get('progression_notes')
            if required is True:
                answer = 'Yes. The stored battle data says victory is required to progress.'
                missing = []
            elif required is False:
                answer = 'No. The stored battle data says victory is not required to progress.'
                missing = []
            else:
                answer = 'The stored battle data does not establish whether victory is required.'
                missing = ['whether victory is required for progression']
            if note:
                answer += ' ' + note
            return {'status':'answered' if not missing else 'insufficient_evidence','answer':answer,'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':page.rows}],'assumptions':[],'missing_information':missing,'tool_calls':[page.query_id]}

        if intent == 'location':
            params = {'trainer_id':'trainer:blue','version_id':version,'battle_key':battle}
            page = await self.client.execute('battles.context_for_battle', **params)
            if not page.rows:
                return {'status':'insufficient_evidence','answer':'No matching battle context is stored for this game and encounter.','evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':[]}],'assumptions':[],'missing_information':['battle location/context data'],'tool_calls':[page.query_id]}
            row = page.rows[0]
            place = row.get('location_name') or 'Location not recorded'
            city = row.get('canonical_location_name')
            answer = f"Blue's {row.get('battle_name') or battle} takes place at {place}"
            if city and city.lower() not in place.lower():
                answer += f", in {city.replace('-', ' ').title()}"
            answer += '.'
            note = row.get('progression_notes')
            if note:
                answer += ' ' + note
            missing = [] if row.get('progression_status') not in ('unknown', None) else ['battle progression details']
            return {'status':'answered' if not missing else 'insufficient_evidence','answer':answer,'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':page.rows}],'assumptions':[],'missing_information':missing,'tool_calls':[page.query_id]}

        if intent == 'encounters':
            names = accessible_location_names
            if names is None and 'route 22' in question.lower():
                names = ['kanto-route-22']
            if not names:
                return _clarify('Which encounter locations should I search? For Route 22, use kanto-route-22.', ['accessible_location_names'])
            if any('|' in name for name in names):
                return _clarify('Pass locations as separate values; a location name cannot contain the query separator.', ['accessible_location_names'])
            params = {'region_name':'kanto','version_id':version,'accessible_location_names':'|'.join(names),'skip':0,'limit':100}
            page = await self.client.execute('encounters.pokemon_in_region', **params)
            names_found = [row['pokemon_name'].title() for row in page.rows]
            answer = ('Recorded encounter Pokémon: ' + ', '.join(names_found) + '.' if names_found else 'No recorded encounters matched those game and location filters.')
            answer += ' This reports database encounter records; it does not check story progression or capture prerequisites.'
            return {'status':'answered' if names_found else 'insufficient_evidence','answer':answer,'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':page.rows}],'assumptions':['Only the explicitly named locations were searched.'],'missing_information':[] if names_found else ['matching encounter records'],'tool_calls':[page.query_id]}

        if battle != 'second-optional':
            return _clarify('Regional type comparison is currently implemented for Blue’s optional second Route 22 battle only.', ['battle_key=second-optional'])
        locations = accessible_location_names
        assumptions = []
        if locations is None and 'route 22' in question.lower():
            locations = ['kanto-route-22']
            assumptions.append('Candidate Pokémon are limited to recorded encounters at Kanto Route 22.')
        if not locations:
            return _clarify('Which encounter locations should count as accessible? For this question, try kanto-route-22.', ['accessible_location_names'])
        if any('|' in loc for loc in locations):
            return _clarify('Pass locations as separate values; a location name cannot contain the query separator.', ['accessible_location_names'])
        params = {'trainer_id': 'trainer:blue', 'version_id': version,
                  'battle_key': battle, 'starter_species_id': STARTERS[starter], 'skip': 0,
                  'limit': 100, 'accessible_location_names': '|'.join(locations)}
        page = await self.client.execute('battles.regional_candidates_for_battle', **params)
        if not page.rows:
            return {'status':'insufficient_evidence','answer':'No regional candidates were returned for those game, battle, starter, and location filters.', 'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':[]}], 'assumptions':assumptions, 'missing_information':['matching encounter and battle graph data'], 'tool_calls':[page.query_id]}
        supported = [r for r in page.rows if r['members_covered'] > 0]
        names = ', '.join(r['pokemon_name'].title() for r in supported[:10])
        answer = ('Potential type-based candidates: '+names+'.' if names else 'The stored chart did not identify a supported type advantage among the returned candidates.')
        answer += ' This compares Pokémon types against Blue’s team; it does not verify available moves, Generation I chart accuracy, capture prerequisites, or a winning strategy.'
        return {'status':'answered','answer':answer,'evidence':[{'kind':'graph','query_id':page.query_id,'parameters':params,'rows':page.rows}], 'assumptions':assumptions, 'missing_information':['candidate move availability','Generation I type-chart verification','battle/progression feasibility'], 'tool_calls':[page.query_id]}
