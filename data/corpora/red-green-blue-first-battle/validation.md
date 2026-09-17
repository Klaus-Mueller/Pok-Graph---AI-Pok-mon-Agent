# Simplified battle model verification

Current model: Trainer → BattleEncounter → BattleVariant → TrainerPokemon,
with direct TrainerPokemon-KNOWS_MOVE->Move relationships. Expected: 263 battle
nodes and 702 equipped-move relationships. Source properties, Source nodes and
TrainerMove nodes are not emitted by the battle pipeline. The existing PokéAPI
source model is unchanged.

## Local checks

- 13 battle tests passed, including source-free serialization, direct move edges,
  canonical references, parsing, stable IDs and unchanged-input validation.
- Broader local unit run: 45 tests, successful, one optional wheel test skipped.
- Generated payload and schema consistency checked: four battle constraints,
  22 constraints in the complete project schema. No trainer_move_id declaration.
- New dataset rebuilt from the original chunks and saved canonical mapping snapshot.

## Server test

The simplified-model integration run passed in 151 seconds. It loaded all sixteen
versioned battles in a transaction, repeated two loads, checked 702 direct move
relationships and no legacy battle relationships, queried teams in both games,
rejected conflicting references, compared canonical properties and rolled back.
No persistent battle data was loaded. A second integration run passed in 146 seconds, including all ten checks in the
post-ingestion verification query against the populated model before rollback.

## Repeatable steps

Run from the repository root. Configure the Neo4j credentials in .env for server
commands. Do not print or commit credentials.

```sh
# Local preparation and checks; no database mutation.
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.battles
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.battles --check
PYTHONPATH=src .venv/bin/python -m unittest tests.test_battles -v

# Integration against configured Neo4j; all test writes roll back.
PYTHONPATH=src POKEGRAPH_BATTLE_INTEGRATION=1 .venv/bin/python -m unittest tests.integration.test_battle_ingest -v

# Persistent ingestion, followed by read-only integrity checks.
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.battles --write
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.battles --verify-server
```

Expected final status: server_verified. The count checks are 1 Trainer, 16 battles,
48 variants, 198 members and 702 KNOWS_MOVE relationships. Legacy-model/source
checks and malformed/duplicate move-slot checks must return zero.

The original 255-second test report described the previous TrainerMove/Source
model and is superseded by these results. Professor Oak's Laboratory and Silph Co.
now map to their containing cities (pallet-town and saffron-city); progression remains partial/unknown as
listed in battle-validation-report.json.
