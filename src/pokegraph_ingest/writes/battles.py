"""Atomic per-battle writes; canonical nodes must already exist."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
import logging
import time

from pokegraph.sources.battles import BattleEncounter, require, validate_battle, validate_dataset
from ..battle_schema import BATTLE_CONSTRAINTS
CANONICAL_LABELS = {'Pokemon', 'PokemonSpecies', 'Move', 'GameVersion', 'VersionGroup', 'Location'}
logger = logging.getLogger('pokegraph_ingest.battles.writer')


async def apply_battle_schema(session) -> None:
    for query in BATTLE_CONSTRAINTS:
        await (await session.run(query)).consume()


def graph_rows(b: BattleEncounter) -> dict:
    validate_battle(b)
    nodes, edges, refs = defaultdict(list), defaultdict(list), defaultdict(dict)

    def edge(fl, fi, rel, tl, ti, props=None):
        edges[(fl, rel, tl)].append({'from_id': fi, 'to_id': ti, 'props': props or {}})

    def reference(label, ref):
        refs[label][ref.id] = {'id': ref.id, 'name': ref.name}

    def node(label, entity, props):
        nodes[label].append({'id': entity.id, 'props': props})

    node('Trainer', b.trainer, {'name': b.trainer.name})
    props = {k: v for k, v in asdict(b).items() if k not in ('id','trainer','game_version','version_group','location','variants','evidence')}
    node('BattleEncounter', b, props)
    reference('GameVersion', b.game_version)
    edge('Trainer', b.trainer.id, 'HAS_BATTLE', 'BattleEncounter', b.id)
    edge('BattleEncounter', b.id, 'IN_GAME_VERSION', 'GameVersion', b.game_version.id)
    if b.version_group:
        reference('VersionGroup', b.version_group)
    if b.location:
        reference('Location', b.location)
        edge('BattleEncounter', b.id, 'AT_LOCATION', 'Location', b.location.id)
    pairs = set()
    for v in b.variants:
        node('BattleVariant', v, {'variant_key': v.variant_key, 'reward_amount': v.reward_amount})
        reference('PokemonSpecies', v.starter)
        edge('BattleEncounter', b.id, 'HAS_VARIANT', 'BattleVariant', v.id)
        edge('BattleVariant', v.id, 'WHEN_PLAYER_CHOSE', 'PokemonSpecies', v.starter.id)
        for p in v.members:
            node('TrainerPokemon', p, {'slot': p.slot, 'level': p.level, 'observed_type_names': p.observed_type_names})
            reference('Pokemon', p.pokemon)
            reference('PokemonSpecies', p.species)
            pairs.add((p.pokemon.id, p.species.id))
            edge('BattleVariant', v.id, 'HAS_MEMBER', 'TrainerPokemon', p.id)
            edge('TrainerPokemon', p.id, 'INSTANCE_OF', 'Pokemon', p.pokemon.id)
            for m in p.moves:
                reference('Move', m.move)
                edge('TrainerPokemon', p.id, 'KNOWS_MOVE', 'Move', m.move.id, {'id': m.id, 'slot': m.slot, 'observed_type_name': m.observed_type_name})
    return {'nodes': dict(nodes), 'edges': dict(edges), 'refs': {k: list(v.values()) for k,v in refs.items()}, 'species_pairs': [{'pokemon': p, 'species': s} for p,s in sorted(pairs)]}


async def preflight(tx, b: BattleEncounter, rows: dict) -> None:
    for label, refs in rows['refs'].items():
        require(label in CANONICAL_LABELS, 'Unexpected reference label')
        result = await tx.run(f'UNWIND $rows AS row OPTIONAL MATCH (n:{label} {{id:row.id}}) WITH row,collect(n.name) AS names WHERE names <> [row.name] RETURN row.id AS id', rows=refs)
        require(not await result.data(), f'Missing/ambiguous {label} ID/name; refusing incomplete ingest')
    result = await tx.run('''UNWIND $rows AS row
        MATCH (p:Pokemon {id:row.pokemon})
        OPTIONAL MATCH (p)-[:SPECIES]->(s:PokemonSpecies)
        WITH row,p,collect(s.id) AS ids
        WHERE ids <> [row.species] OR p.is_default IS NULL OR p.is_default <> true
        RETURN row.pokemon AS id''', rows=rows['species_pairs'])
    require(not await result.data(), 'Pokemon/species/default-form mismatch')
    result = await tx.run('''MATCH (v:GameVersion {id:$id})
        OPTIONAL MATCH (v)-[:IN_VERSION_GROUP]->(g:VersionGroup)
        RETURN collect(g.id) AS ids''', id=b.game_version.id)
    record = await result.single()
    require(record is not None and record['ids'] == ([b.version_group.id] if b.version_group else []), 'VersionGroup relationship changed')


async def check_existing_structure(tx, b: BattleEncounter, rows: dict) -> None:
    # Existing extra children or different canonical targets require explicit
    # reconciliation. A repeat of the same import is safe; a changed team cannot
    # accumulate stale edges or orphaned members silently.
    result = await tx.run("""MATCH (b:BattleEncounter {id:$id})
        MATCH (b)-[:HAS_VARIANT|HAS_MEMBER*0..2]->(n)
        OPTIONAL MATCH (n)-[r:HAS_MOVE|HAS_SOURCE]->()
        RETURN count(r) AS old_edges""", id=b.id)
    require((await result.single())['old_edges'] == 0, 'Legacy battle model found; remove the old battle import before loading the new model')
    expected_children = {r['id'] for label, ns in rows['nodes'].items() if label not in ('Trainer',) for r in ns}
    result = await tx.run('''MATCH (b:BattleEncounter {id:$id})
        MATCH (b)-[:HAS_VARIANT|HAS_MEMBER*0..2]->(n)
        RETURN DISTINCT n.id AS id''', id=b.id)
    require({r['id'] for r in await result.data()} <= expected_children, 'Existing team has extra children; explicit reconciliation required')
    # Trainer can own many battles; only check the incoming parent of this battle.
    for (fl, rel, tl), es in rows['edges'].items():
        if rel == 'HAS_BATTLE':
            result = await tx.run('MATCH (p)-[:HAS_BATTLE]->(b:BattleEncounter {id:$id}) RETURN p.id AS id', id=b.id)
            parents = [r['id'] for r in await result.data()]
            require(parents in ([], [b.trainer.id]), 'Existing battle has conflicting trainer')
            continue
        if rel == 'KNOWS_MOVE':
            expected = {(e['from_id'], e['to_id'], e['props']['id'], e['props']['slot']) for e in es}
            result = await tx.run('MATCH (p:TrainerPokemon)-[r:KNOWS_MOVE]->(m) WHERE p.id IN $ids RETURN p.id AS p,m.id AS m,r.id AS id,r.slot AS slot,labels(m) AS labels', ids=list({e['from_id'] for e in es}))
            seen = []
            for r in await result.data():
                item = (r['p'], r['m'], r['id'], r['slot'])
                require(item in expected and 'Move' in r['labels'], 'Existing equipped move differs; explicit reconciliation required')
                seen.append(item)
            require(len(seen) == len(set(seen)), 'Duplicate equipped move relationship')
            continue
        allowed = {(e['from_id'], e['to_id']) for e in es}
        result = await tx.run(f'MATCH (a:{fl})-[r:{rel}]->(z) WHERE a.id IN $ids RETURN a.id AS a,z.id AS z,labels(z) AS labels', ids=list({e['from_id'] for e in es}))
        seen = []
        for r in await result.data():
            require((r['a'], r['z']) in allowed and tl in r['labels'], 'Existing relationship differs; explicit reconciliation required')
            seen.append((r['a'], r['z']))
        require(len(seen) == len(set(seen)), 'Existing duplicate relationship')
        if rel in ('HAS_VARIANT','HAS_MEMBER','HAS_MOVE'):
            result = await tx.run(f'MATCH (p)-[:{rel}]->(n:{tl}) WHERE n.id IN $ids RETURN p.id AS p,n.id AS n', ids=[e['to_id'] for e in es])
            require(all((r['p'], r['n']) in allowed for r in await result.data()), 'Child belongs to a different parent')
    if b.location is None:
        result = await tx.run('MATCH (:BattleEncounter {id:$id})-[:AT_LOCATION]->(l) RETURN l.id AS id', id=b.id)
        require(not await result.data(), 'Location removal requires explicit reconciliation')


async def write_battle(tx, battle: BattleEncounter) -> dict[str, int]:
    """Call in one managed transaction. Any failed check rolls back the battle."""
    rows = graph_rows(battle)
    await preflight(tx, battle, rows)
    await check_existing_structure(tx, battle, rows)
    for label, ns in rows['nodes'].items():
        logger.debug('Transaction batch: battle=%s label=%s records=%d', battle.id, label, len(ns))
        result = await tx.run(f'UNWIND $rows AS row MERGE (n:{label} {{id:row.id}}) SET n += row.props RETURN count(n) AS count', rows=ns)
        require((await result.single())['count'] == len(ns), 'Node write count mismatch')
    for (fl, rel, tl), es in rows['edges'].items():
        logger.debug('Transaction batch: battle=%s relationship=%s records=%d', battle.id, rel, len(es))
        key = ' {id:row.props.id}' if rel == 'KNOWS_MOVE' else ''
        result = await tx.run(f'''UNWIND $rows AS row
            MATCH (a:{fl} {{id:row.from_id}}), (z:{tl} {{id:row.to_id}})
            MERGE (a)-[r:{rel}{key}]->(z) SET r += row.props
            RETURN count(r) AS count''', rows=es)
        require((await result.single())['count'] == len(es), 'Relationship write count mismatch')
    return {label: len(ns) for label, ns in rows['nodes'].items()}


async def write_battles(session, battles: list[BattleEncounter]) -> None:
    validate_dataset(battles)
    # Preflight the entire input before the first mutation, then recheck inside
    # each write transaction to catch catalog changes during the import.
    total = len(battles)
    committed = 0
    started = time.perf_counter()
    stage = 'preflight'
    battle_id = None
    try:
        for index, b in enumerate(battles, 1):
            battle_id = b.id
            step = time.perf_counter()
            logger.info('Preflight [%d/%d] started: %s', index, total, b.id)
            rows = graph_rows(b)
            await session.execute_read(preflight, b, rows)
            await session.execute_read(check_existing_structure, b, rows)
            logger.info('Preflight [%d/%d] passed: %s elapsed=%.2fs', index, total, b.id, time.perf_counter() - step)
        stage = 'write'
        for index, b in enumerate(battles, 1):
            battle_id = b.id
            step = time.perf_counter()
            logger.info('Writing [%d/%d]: %s', index, total, b.id)
            await session.execute_write(write_battle, b)
            # Log success only after the managed transaction has committed;
            # transaction callback retries must not produce false commit events.
            committed += 1
            logger.info('Committed [%d/%d]: %s elapsed=%.2fs', committed, total, b.id, time.perf_counter() - step)
    except Exception as exc:
        logger.error('Ingestion failed: stage=%s battle=%s committed=%d/%d error_type=%s elapsed=%.2fs', stage, battle_id, committed, total, type(exc).__name__, time.perf_counter() - started)
        raise
    logger.info('Ingestion completed: committed=%d/%d elapsed=%.2fs', committed, total, time.perf_counter() - started)
