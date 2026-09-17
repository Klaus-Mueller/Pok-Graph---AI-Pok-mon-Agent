"""Typed battle records. EquippedMove is a relationship payload, not a node."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

BATTLE_KEYS = ('first', 'second-optional', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth-champion')
TEAM_SIZES = (1, 2, 4, 4, 5, 5, 6, 6)
STARTERS = ('bulbasaur', 'charmander', 'squirtle')
VERSIONS = {'red-jp': (44, 'red-japan'), 'green-jp': (45, 'green-japan')}
TYPES = set('Normal Fire Water Electric Grass Ice Fighting Poison Ground Flying Psychic Bug Rock Ghost Dragon'.split())
ALIASES = {'Sand-Attack': 'sand-attack', 'PoisonPowder': 'poison-powder', 'SolarBeam': 'solar-beam'}
# Building names are retained in location_name; these two map to their containing cities.
LOCATION_NAMES = {
    "Professor Oak's Laboratory": 'pallet-town', 'Route 22': 'kanto-route-22',
    'Cerulean City': 'cerulean-city', 'S.S. Anne': 'ss-anne',
    'Pokémon Tower': 'pokemon-tower', 'Silph Co.': 'saffron-city', 'Indigo Plateau': 'indigo-plateau',
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def canonical_name(name: str) -> str:
    return ALIASES.get(name, name.lower().replace(' ', '-'))


@dataclass(frozen=True)
class Ref:
    id: int
    name: str


@dataclass(frozen=True)
class Trainer:
    id: str
    name: str


@dataclass(frozen=True)
class EquippedMove:
    id: str
    slot: int
    move: Ref
    observed_type_name: str


@dataclass(frozen=True)
class TrainerPokemon:
    id: str
    slot: int
    level: int
    pokemon: Ref
    species: Ref
    observed_type_names: list[str]
    moves: list[EquippedMove]


@dataclass(frozen=True)
class BattleVariant:
    id: str
    variant_key: str
    starter: Ref
    reward_amount: int
    members: list[TrainerPokemon]


@dataclass(frozen=True)
class BattleEncounter:
    id: str
    battle_key: str
    battle_order: int
    name: str
    trainer: Trainer
    game_version: Ref
    version_group: Ref | None
    location_name: str
    location: Ref | None
    location_mapping_status: str
    progression_status: str
    is_optional: bool | None
    victory_required_for_progression: bool | None
    available_after_text: str | None
    available_until_text: str | None
    skip_condition_text: str | None
    progression_notes: str | None
    variants: list[BattleVariant]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> BattleEncounter:
        d = dict(value)
        d['trainer'] = Trainer(**d['trainer'])
        for key in ('game_version', 'version_group', 'location'):
            d[key] = Ref(**d[key]) if d[key] else None
        variants = []
        for v in d['variants']:
            members = []
            for p in v['members']:
                moves = [EquippedMove(**{**m, 'move': Ref(**m['move'])}) for m in p['moves']]
                members.append(TrainerPokemon(**{**p, 'pokemon': Ref(**p['pokemon']), 'species': Ref(**p['species']), 'moves': moves}))
            variants.append(BattleVariant(**{**v, 'starter': Ref(**v['starter']), 'members': members}))
        d.update(variants=variants)
        result = cls(**d)
        validate_battle(result)
        return result


def parse_party(chunk: dict) -> dict:
    """Consume the actual line grammar; Psychic may be both move and type."""
    lines = chunk['text'].splitlines()
    starter = chunk['player_starter']
    require(starter in STARTERS, 'Unknown starter')
    require(len(lines) >= 7 and lines[:2] == [f'If the player chose {starter.capitalize()}:', 'Blue'], 'Party header/starter mismatch')
    require(lines[3:5] == ['Red, Green, and Blue', 'Reward:'], 'Unexpected game/reward header')
    require(bool(re.fullmatch(r'\$\d+', lines[5])), 'Invalid reward')
    require(lines[2] in LOCATION_NAMES, f'Unreviewed location: {lines[2]}')
    members, i = [], 6
    while i < len(lines):
        match = re.fullmatch(r'(.+) Lv\.(\d+)', lines[i])
        require(match is not None, f"{chunk['id']}: unexpected member/footer at {lines[i]!r}")
        name, level = match[1], int(match[2])
        i += 1
        require(i < len(lines) and lines[i] in ('Type:', 'Types:'), 'Missing species type label')
        count = 1 if lines[i] == 'Type:' else 2
        types = lines[i + 1:i + 1 + count]
        require(len(types) == count and set(types) <= TYPES, 'Invalid species types')
        i += count + 1
        moves = []
        while i < len(lines) and not re.fullmatch(r'.+ Lv\.\d+', lines[i]):
            require(i + 1 < len(lines) and lines[i + 1] in TYPES, f"{chunk['id']}: invalid move pair / footer: {lines[i]!r}")
            moves.append({'name': lines[i], 'type': lines[i + 1]})
            i += 2
        require(1 <= len(moves) <= 4, 'Expected 1..4 equipped moves')
        require(1 <= level <= 100, 'Invalid level')
        members.append({'name': name, 'level': level, 'types': types, 'moves': moves})
    require(1 <= len(members) <= 6, 'Expected 1..6 members')
    return {'location': lines[2], 'reward': int(lines[5][1:]), 'members': members}


def resolve(rows: list[dict], name: str) -> Ref:
    matches = [r for r in rows if r['name'] == name]
    require(len(matches) == 1, f'Canonical reference missing/ambiguous: {name}')
    r = matches[0]
    require(type(r['id']) is int and r['id'] > 0, f'Invalid canonical ID: {name}')
    return Ref(r['id'], r['name'])


def normalize(chunks: list[dict], catalog: dict) -> list[BattleEncounter]:
    require(len({c['id'] for c in chunks}) == len(chunks), 'Duplicate chunk ID')
    by_id = {c['id']: c for c in chunks}
    trainer = Trainer('trainer:blue', 'Blue')
    parties = [c for c in chunks if 'player_starter' in c]
    require(len(parties) == 24, 'Expected 24 party chunks')
    require({c['battle_order'] for c in parties} == set(range(1, 9)), 'Expected eight battles')
    result = []
    for order, key in enumerate(BATTLE_KEYS, 1):
        rows = [c for c in parties if c['battle_order'] == order]
        require(len(rows) == 3 and {c['player_starter'] for c in rows} == set(STARTERS), 'Missing/duplicate starter variant')
        require(len({c['battle_name'] for c in rows}) == 1, 'Battle names disagree')
        context_id = 'blue-first-outcome' if order == 1 else f'blue-{key}-context'
        context = by_id.get(context_id)
        parsed = {c['player_starter']: parse_party(c) for c in rows}
        require(len({p['location'] for p in parsed.values()}) == 1, 'Variant locations disagree')
        for scope, (version_id, version_name) in VERSIONS.items():
            version = resolve(catalog['versions'], version_name)
            require(version.id == version_id, 'Version ID mismatch')
            group_rows = next(v for v in catalog['versions'] if v['id'] == version_id)['groups']
            require(len(group_rows) <= 1, 'Ambiguous version group')
            group = Ref(**group_rows[0]) if group_rows else None
            bid = f'battle:blue:{version.id}:{key}'
            variants = []
            for starter in STARTERS:
                c = next(c for c in rows if c['player_starter'] == starter)
                require(c['game_scope'] == list(VERSIONS) and c['generation'] == 1, 'Unsupported game scope')
                party = parsed[starter]
                require(len(party['members']) == TEAM_SIZES[order - 1], 'Unexpected team size')
                starter_ref = resolve(catalog['species'], starter)
                vid = f'{bid}:starter:{starter_ref.id}'
                members = []
                for slot, p in enumerate(party['members'], 1):
                    pid = f'{vid}:member:{slot}'
                    pokemon = resolve(catalog['pokemon'], canonical_name(p['name']))
                    pr = next(r for r in catalog['pokemon'] if r['id'] == pokemon.id)
                    require(pr['is_default'] is True and len(pr['species']) == 1, 'Unresolved default Pokemon/species relationship')
                    species = Ref(**pr['species'][0])
                    require(species == resolve(catalog['species'], canonical_name(p['name'])), 'Pokemon species mismatch')
                    moves = [EquippedMove(f'{pid}:move:{i}', i, resolve(catalog['moves'], canonical_name(m['name'])), m['type']) for i, m in enumerate(p['moves'], 1)]
                    members.append(TrainerPokemon(pid, slot, p['level'], pokemon, species, p['types'], moves))
                variants.append(BattleVariant(vid, f'starter:{starter_ref.id}', starter_ref, party['reward'], members))
            location_name = parsed[STARTERS[0]]['location']
            target = LOCATION_NAMES[location_name]
            location = resolve(catalog['locations'], target) if target and any(l['name'] == target for l in catalog['locations']) else None
            progress = dict(is_optional=None, victory_required_for_progression=None, available_after_text=None, available_until_text=None, skip_condition_text=None, progression_notes=None)
            if context:
                progress['progression_notes'] = context['text']
                if order == 1:
                    require(context['text'] == 'Winning this battle is not mandatory. The player will not black out and the story will progress either way.', 'Review changed first-battle outcome')
                    progress['victory_required_for_progression'] = False
                elif order == 2:
                    require('(optional)' in context['battle_name'], 'Optional label missing')
                    progress.update(is_optional=True, available_until_text=context['text'])
                elif order in (3, 4):
                    progress['skip_condition_text'] = context['text']
                elif order == 7:
                    progress['available_after_text'] = context['text']
            result.append(BattleEncounter(bid, key, order, rows[0]['battle_name'], trainer, version, group, location_name, location, 'resolved' if location else 'unresolved', 'partial' if context else 'unknown', variants=variants, **progress))
    validate_dataset(result)
    return result


def validate_battle(b: BattleEncounter) -> None:
    require(type(b.battle_order) is int and 1 <= b.battle_order <= 8, 'Invalid battle order')
    require(b.battle_key == BATTLE_KEYS[b.battle_order - 1], 'Invalid battle key')
    require(b.trainer.id == 'trainer:blue' and b.trainer.name == 'Blue', 'Invalid trainer')
    require((b.game_version.id, b.game_version.name) in VERSIONS.values(), 'Invalid version')
    require(b.id == f'battle:blue:{b.game_version.id}:{b.battle_key}', 'Invalid battle ID')
    require(b.location_mapping_status == ('resolved' if b.location else 'unresolved'), 'Invalid location status')
    require(b.progression_status in ('unknown', 'partial', 'reviewed'), 'Invalid progression status')
    for value in (b.is_optional, b.victory_required_for_progression):
        require(value is None or type(value) is bool, 'Invalid optionality')
    require(len(b.variants) == 3 and {v.starter.name for v in b.variants} == set(STARTERS), 'Invalid starter coverage')
    entities: list[Any] = [b, b.trainer]
    for v in b.variants:
        require(v.variant_key == f'starter:{v.starter.id}' and v.id == f'{b.id}:{v.variant_key}', 'Invalid variant ID')
        require(type(v.reward_amount) is int and v.reward_amount >= 0, 'Invalid reward')
        require(len(v.members) == TEAM_SIZES[b.battle_order - 1], 'Invalid team size')
        entities.append(v)
        for slot, p in enumerate(v.members, 1):
            require(type(p.slot) is int and p.slot == slot and p.id == f'{v.id}:member:{slot}', 'Invalid member slot/ID')
            require(type(p.level) is int and 1 <= p.level <= 100, 'Invalid level')
            require(1 <= len(p.observed_type_names) <= 2 and set(p.observed_type_names) <= TYPES, 'Invalid observed types')
            require(1 <= len(p.moves) <= 4, 'Invalid move count')
            entities.append(p)
            for mslot, m in enumerate(p.moves, 1):
                require(type(m.slot) is int and m.slot == mslot and m.id == f'{p.id}:move:{mslot}', 'Invalid move slot/ID')
                require(m.observed_type_name in TYPES, 'Invalid move type')
                entities.append(m)
    require(len({e.id for e in entities}) == len(entities), 'Duplicate entity ID')
    refs = [b.game_version, b.version_group, b.location]
    for v in b.variants:
        refs.append(v.starter)
        for p in v.members:
            refs.extend([p.pokemon, p.species, *(m.move for m in p.moves)])
    for ref in refs:
        if ref is not None:
            require(type(ref.id) is int and ref.id > 0 and isinstance(ref.name, str) and bool(ref.name), 'Invalid canonical reference')


def validate_dataset(battles: list[BattleEncounter]) -> None:
    require(len(battles) == 16 and len({b.id for b in battles}) == 16, 'Expected 16 unique versioned battles')
    for b in battles:
        validate_battle(b)
    require({(b.game_version.id, b.battle_order) for b in battles} == {(v[0], o) for v in VERSIONS.values() for o in range(1, 9)}, 'Missing version/battle')


def counts(battles: list[BattleEncounter]) -> dict[str, int]:
    return {'Trainer': len({b.trainer.id for b in battles}), 'BattleEncounter': len(battles), 'BattleVariant': sum(len(b.variants) for b in battles), 'TrainerPokemon': sum(len(v.members) for b in battles for v in b.variants), 'KNOWS_MOVE': sum(len(p.moves) for b in battles for v in b.variants for p in v.members)}
