"""Prepare the Blue corpus; graph mutation requires the explicit --write option."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pokegraph.config import Neo4jSettings
from pokegraph.graph.connection import GraphConnection, create_driver
from pokegraph.sources.battles import (
    ALIASES, LOCATION_NAMES, BattleEncounter, canonical_name, counts, normalize,
    parse_party, require, validate_dataset,
)

DEFAULT_CORPUS = Path('data/corpora/red-green-blue-first-battle')
logger = logging.getLogger('pokegraph_ingest.battles')


async def fetch_catalog(chunks: list[dict]) -> dict:
    logger.info('Refreshing canonical references from Neo4j (read-only)')
    parties = [parse_party(c) for c in chunks if 'player_starter' in c]
    pokemon_names = sorted({canonical_name(p['name']) for party in parties for p in party['members']})
    move_names = sorted({canonical_name(m['name']) for party in parties for p in party['members'] for m in p['moves']})
    queries = {
        'pokemon': ('MATCH (p:Pokemon) WHERE p.name IN $names OPTIONAL MATCH (p)-[:SPECIES]->(s:PokemonSpecies) RETURN p.id AS id,p.name AS name,p.is_default AS is_default,collect(DISTINCT s{.id,.name}) AS species ORDER BY id', pokemon_names),
        'species': ('MATCH (s:PokemonSpecies) WHERE s.name IN $names RETURN s.id AS id,s.name AS name ORDER BY id', sorted(set(pokemon_names) | {'bulbasaur','charmander','squirtle'})),
        'moves': ('MATCH (m:Move) WHERE m.name IN $names RETURN m.id AS id,m.name AS name ORDER BY id', move_names),
        'locations': ('MATCH (l:Location) RETURN l.id AS id,l.name AS name ORDER BY id', []),
        'versions': ('''MATCH (v:GameVersion) WHERE v.id IN [44,45]
            OPTIONAL MATCH (v)-[:IN_VERSION_GROUP]->(vg:VersionGroup)
            WITH v,collect(DISTINCT vg{.id,.name}) AS groups
            OPTIONAL MATCH (e:Encounter)-[:IN_VERSION]->(v)
            WITH v,groups,count(DISTINCT e) AS encounter_count
            OPTIONAL MATCH (v)-[:IN_VERSION_GROUP]->(:VersionGroup)<-[:IN_VERSION_GROUP]-(le:LearnsetEntry)
            RETURN v.id AS id,v.name AS name,groups,encounter_count,count(DISTINCT le) AS learnset_count ORDER BY id''', []),
    }
    async with GraphConnection.from_environment() as graph:
        async def fetch(name, query, names):
            started = time.perf_counter()
            logger.info('Catalog lookup started: %s', name)
            rows = await graph.execute_read(query, {'names': names})
            logger.info('Catalog lookup completed: %s records=%d elapsed=%.2fs', name, len(rows), time.perf_counter() - started)
            return rows
        values = await asyncio.gather(*(fetch(name, query, names) for name, (query, names) in queries.items()))
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'method': 'neo4j_read_only',
            'aliases': ALIASES, **{key: [dict(r) for r in rows] for key, rows in zip(queries, values)}}


def read_inputs(root: Path):
    chunks = [json.loads(line) for line in (root / 'chunks.jsonl').read_text().splitlines() if line.strip()]
    return chunks


def verify_fixture(root: Path, battles: list[BattleEncounter]) -> None:
    fixture = json.loads((root / 'battle-fixture.json').read_text())
    for b in battles:
        if b.battle_order != 1:
            continue
        require(b.location_name == fixture['location'] and b.victory_required_for_progression == fixture['victory_required_for_progression'], 'First-battle fixture context mismatch')
        for v in b.variants:
            original = next(vv for vv in fixture['variants'] if vv['player_starter'] == v.starter.name)
            actual = [{'slot': p.slot, 'species': p.species.name, 'level': p.level, 'moves': [m.move.name for m in p.moves]} for p in v.members]
            expected = [{k: p[k] for k in ('slot','species','level','moves')} for p in original['members']]
            require(actual == expected, 'First-battle fixture team mismatch')


def validation_report(battles: list[BattleEncounter], catalog: dict, chunks: list[dict], root: Path) -> dict:
    ids = {c['id'] for c in chunks}
    for line in (root / 'questions.jsonl').read_text().splitlines():
        q = json.loads(line)
        require(set(q.get('evidence_chunk_ids', [])) <= ids, f"Missing question evidence: {q['id']}")
    return {
        'status': 'prepared_not_ingested', 'counts': counts(battles),
        'question_count': len((root / 'questions.jsonl').read_text().splitlines()),
        'canonical_checked_at': catalog['checked_at'], 'canonical_check_method': catalog['method'],
        'version_coverage': catalog['versions'],
        'unresolved_locations': sorted({b.location_name for b in battles if b.location is None}),
        'location_mapping_policy': LOCATION_NAMES,
        'partial_progression_orders': sorted({b.battle_order for b in battles if b.progression_status == 'partial'}),
        'unknown_progression_orders': sorted({b.battle_order for b in battles if b.progression_status == 'unknown'}),
        'manual_normalizations': ALIASES, 'extraction': 'deterministic line parser; no inferred facts',
        'source_cleanup': 'collector ends at printfooter; source snapshots and chunk IDs preserved',
        'checks': ['first_battle_fixture', 'question_evidence', 'eight_battles_two_versions_three_starters', 'canonical_references', 'typed_payload_roundtrip'],
    }


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


async def run(args) -> dict:
    started = time.perf_counter()
    root = args.corpus
    mode = 'write' if args.write else 'verify-server' if getattr(args, 'verify_server', False) else 'check' if args.check else 'prepare'
    logger.info('Battle pipeline started: mode=%s corpus=%s', mode, root)
    chunks = read_inputs(root)
    logger.info('Loaded %d chunks', len(chunks))
    if args.refresh_mappings or args.write:
        catalog = await fetch_catalog(chunks)
    else:
        logger.info('Loading canonical references from local entity-mappings.json')
        catalog = json.loads((root / 'entity-mappings.json').read_text())
    logger.info('Normalizing battle records and validating fixture, references and question coverage')
    battles = normalize(chunks, catalog)
    verify_fixture(root, battles)
    for b in battles:
        require(BattleEncounter.from_dict(b.to_dict()) == b, 'Payload roundtrip mismatch')
    report = validation_report(battles, catalog, chunks, root)
    logger.info('Validation passed: counts=%s questions=%d', report['counts'], report['question_count'])
    if report['unresolved_locations']:
        logger.info('Unresolved locations retained as text: %s', ', '.join(report['unresolved_locations']))
    if getattr(args, 'verify_server', False):
        logger.info('Running read-only server verification')
        from pokegraph.graph.catalog import load_cypher
        async with GraphConnection.from_environment() as graph:
            rows = await graph.execute_read(load_cypher('battles/verify_ingestion.cypher'), {'battle_ids': [b.id for b in battles]})
        checks = [dict(r) for r in rows]
        for check in checks:
            logger.info('Server check: %s actual=%s expected=%s', check['check'], check['actual'], check['expected'])
        require(all(r['actual'] == r['expected'] for r in checks), 'Server verification failed: ' + json.dumps(checks))
        logger.info('Server verification completed: elapsed=%.2fs', time.perf_counter() - started)
        return {'status': 'server_verified', 'checks': checks}
    if args.check:
        logger.info('Comparing saved battles.jsonl with reconstructed records')
        stored = [BattleEncounter.from_dict(json.loads(line)) for line in (root / 'battles.jsonl').read_text().splitlines()]
        require(stored == battles, 'Stored dataset differs from source reconstruction')
    if args.write:
        logger.info('Checking reviewed battles.jsonl before database writes')
        # Require the reviewed file to equal a fresh reconstruction. Never ingest
        # a stale or manually corrupted payload after merely trusting its IDs.
        stored = [BattleEncounter.from_dict(json.loads(line)) for line in (root / 'battles.jsonl').read_text().splitlines()]
        validate_dataset(stored)
        require(stored == battles, 'Dataset differs from current sources/catalog; prepare and review again')
        from pokegraph_ingest.writes.battles import apply_battle_schema, write_battles
        settings = Neo4jSettings.from_environment()
        logger.info('Opening Neo4j write session')
        async with create_driver(settings) as driver:
            async with driver.session(database=settings.database) as session:
                logger.info('Applying battle uniqueness constraints')
                await apply_battle_schema(session)
                logger.info('Battle schema ready; starting preflight and ingestion')
                await write_battles(session, battles)
        report['status'] = 'ingested'
    elif not args.check:
        logger.info('Saving entity-mappings.json and battles.jsonl locally')
        dump(root / 'entity-mappings.json', catalog)
        (root / 'battles.jsonl').write_text(''.join(json.dumps(b.to_dict(), ensure_ascii=False) + '\n' for b in battles))
    if not args.check:
        dump(root / 'battle-validation-report.json', report)
        logger.info('Saved battle-validation-report.json')
    logger.info('Battle pipeline completed: mode=%s status=%s elapsed=%.2fs', mode, report['status'], time.perf_counter() - started)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--refresh-mappings', action='store_true', help='Read canonical references from Neo4j')
    parser.add_argument('--log-level', choices=('DEBUG', 'INFO', 'WARNING', 'ERROR'), default='INFO', help='Progress logging level on stderr (default: INFO)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Validate without changing files or graph')
    mode.add_argument('--write', action='store_true', help='Ingest the reviewed dataset into configured Neo4j')
    mode.add_argument('--verify-server', action='store_true', help='Read-only counts and integrity checks after ingestion')
    args = parser.parse_args()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z'))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(args.log_level)
    logger.propagate = False
    try:
        report = asyncio.run(run(args))
    except Exception as exc:
        # Do not log driver exception payloads, connection settings or credentials.
        logger.error('Battle pipeline failed: error_type=%s; see preceding progress logs for the failed stage', type(exc).__name__)
        raise SystemExit(1) from None
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
