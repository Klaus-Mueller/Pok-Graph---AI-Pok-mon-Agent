# pokegraph_ingest

PokéAPI → Neo4j ingestion for PokéGraph (KLA-119 MVP).

Fetches Pokémon from [PokéAPI](https://pokeapi.co/) through `PokeApiSource` (the only module that imports [PokeLance](https://github.com/FallenDeity/PokeLance)) and writes idempotent graph data with the official Neo4j Python driver.

## What it writes

### Nodes

| Label | Key | Notes |
| --- | --- | --- |
| `Pokemon` | `id` | Stats / size / default form |
| `PokemonSpecies` | `id` | Legendary/mythical, generation |
| `Type` | `id` | Plus `DAMAGE_TO` edges for counters |
| `Ability` | `id` | Stub from Pokémon abilities |
| `Move` | `id` | Enriched from `/move/{id}`: power/accuracy/pp/priority, type, damage_class, English effect text, structured meta (flinch/ailment/drain/…), contest fields |
| `GameVersion` | `id` | From encounter version details |
| `VersionGroup` | `id` | Hierarchy from versions |
| `Region` | `id` | From locations / version groups |
| `Location` | `id` | Parent of location areas |
| `LocationArea` | `id` | Encounter sites |
| `Encounter` | `id` (synthetic) | Nested PokéAPI encounter records |
| `EncounterMethod` | `id` | walk, surf, gift, … |
| `EvolutionChain` | `id` | Chain container |
| `Item` | `id` | Evolution item stubs |
| `Source` | `id` | Provenance (`pokeapi`) |
| `LearnsetEntry` | `id` (synthetic) | One row per move / version-group / method / level / order |
| `MoveLearnMethod` | `id` | level-up, machine, tutor, … |

Synthetic Encounter id:

`{pokemon_id}:{location_area_id}:{version_id}:{method_id}:{min_level}:{max_level}:{chance}:{conditions}`

Synthetic LearnsetEntry id:

`{pokemon_id}:{move_id}:{version_group_id}:{learn_method_id}:{level}:{order}`

### Relationships

| Relationship | Meaning |
| --- | --- |
| `SPECIES` | Pokemon → PokemonSpecies |
| `HAS_TYPE` / `HAS_ABILITY` | Pokemon → Type / Ability; also Move → Type after enrichment |
| `CAN_LEARN` | Simplified Pokemon → Move (no level/method/version props) |
| `HAS_LEARNSET_ENTRY` | Pokemon → LearnsetEntry |
| `TEACHES` | LearnsetEntry → Move |
| `IN_VERSION_GROUP` | LearnsetEntry → VersionGroup (also GameVersion hierarchy) |
| `BY_LEARN_METHOD` | LearnsetEntry → MoveLearnMethod |
| `HAS_ENCOUNTER` | Pokemon → Encounter |
| `AT_LOCATION_AREA` / `IN_VERSION` / `USES_METHOD` | Encounter context |
| `AVAILABLE_IN_VERSION` / `CAN_BE_FOUND_IN` | Query shortcuts from encounters |
| `PART_OF_LOCATION` | LocationArea → Location |
| `IN_REGION` | Location → Region; VersionGroup → Region |
| `IN_VERSION_GROUP` | GameVersion → VersionGroup |
| `IN_EVOLUTION_CHAIN` | PokemonSpecies → EvolutionChain |
| `EVOLVES_TO` | Species evolution (trigger, level, …); keyed by relationship `id` |
| `REQUIRES_ITEM` | Species → Item when evolution needs an item |
| `DAMAGE_TO` | Type → Type with `factor` (`2.0` / `0.5` / `0.0`) |
| `HAS_SOURCE` | Pokemon / Species → Source |

`CAN_LEARN` remains for simple “can this Pokémon learn this move?” queries. Detailed learn-by-method / version / level data lives only on `LearnsetEntry`.

Relationship writes use `CALL … IN TRANSACTIONS` so large lists commit in batches.

### Deferred (not from PokéAPI)

`Trainer`, `TrainerPokemon`, and `Progression` require curated project datasets. This ingest does not create them.

## Indexes and constraints

Ingest MERGEs look up nodes (and `EVOLVES_TO`) **only by `id`**. Uniqueness constraints are the complete ingest index set: each constraint owns a backing RANGE index that Neo4j uses for `MERGE` / unique seeks.

| Constraint | Entity | Covers MERGE path |
| --- | --- | --- |
| `pokemon_id` … `source_id` (15 node constraints) | Node labels | `MERGE (:Label {id})` in `writes/` |
| `learnset_entry_id` | `LearnsetEntry` | Detailed move learn records |
| `move_learn_method_id` | `MoveLearnMethod` | level-up / machine / … |
| `evolves_to_id` | `EVOLVES_TO` relationship | `MERGE ()-[r:EVOLVES_TO {id}]->()` |

Schema apply also runs a one-shot cleanup:

```cypher
MATCH ()-[r:CAN_LEARN]->()
REMOVE r.level, r.method, r.version_group
```

Re-ingest Pokémon from PokéAPI to populate `LearnsetEntry` (legacy `CAN_LEARN` detail props may already have been overwritten).

There are **no** non-unique `name` indexes for ingestion: `name` is only `SET` after an `id` MERGE, never used as a lookup key. Extra property indexes would add write overhead without helping current ingest plans.

### Verification

Startup (`pokegraph-ingest`) applies constraints idempotently (`IF NOT EXISTS`), then asserts every expected constraint’s backing index is `ONLINE`.

Inspect without ingesting:

```bash
PYTHONPATH=src python -m pokegraph_ingest.schema
# or after editable install:
pokegraph-schema
```

Exit code `0` = all expected uniqueness constraints present and ONLINE; non-zero = missing or not ready.

### EXPLAIN baseline (Aura, Cypher 5 / runtime 2026.07)

Representative plans after schema apply:

- Pokemon core MERGE → `MergeUniqueNode` on `Pokemon(id)` and `PokemonSpecies(id)`
- Encounter batch → `NodeUniqueIndexSeek(Locking)` on `Pokemon(id)` plus `MergeUniqueNode` on `Encounter` / `LocationArea` / `GameVersion` / `EncounterMethod`
- `EVOLVES_TO` MERGE → `DirectedRelationshipUniqueIndexSeek(Locking)` on `EVOLVES_TO(id)` plus species `MergeUniqueNode`

No LabelScan on identity keys. No additional ingest indexes warranted from this PROFILE.

### Ingest duration note

`POKEGRAPH_POKEMON_NAMES=pikachu` on a warm Aura DB: **~2m 03s** wall clock (1 ok / 0 fail). Time is dominated by PokéAPI hierarchy enrichment for ~40 location areas, not by Neo4j unique seeks.

### Agent read indexes (deferred)

Catalog `EXPLAIN` plans are recorded in [`queries/examples/plans.md`](../../queries/examples/plans.md). Identity seeks already use uniqueness constraints; name lookup still LabelScans. Add indexes only after the agent exists and those shapes prove expensive:

1. Collect top queries + `PROFILE` / DB-hit metrics.
2. Index exact-match filters and frequent traversal endpoints that still LabelScan.
3. Consider full-text on `name` only if user-facing search appears.
4. Re-PROFILE and drop any index without measurable benefit.

Trade-off: uniqueness indexes keep MERGE correct and fast; speculative read indexes slow writes and are out of scope until query evidence exists.

## Setup

From the repository root:

1. Copy `.env.example` to `.env` and set `NEO4J_PASSWORD`.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# or: pip install -e ".[ingest]"
```

## Run from the command line

### Module entry point

```bash
PYTHONPATH=src python -m pokegraph_ingest.ingest
```

With the project venv:

```bash
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.ingest
```

### Console scripts (editable install)

After `pip install -e .`:

```bash
pokegraph-ingest    # full ingest (applies + verifies schema first)
pokegraph-schema    # apply + verify constraints/indexes only
```

By default the pipeline loads the full PokéAPI catalog (~1351 entries). Each Pokémon triggers core + encounters + evolution + type enrichment calls, so a full run can take a long time. A live progress bar shows phase, rate, elapsed time, and ETA.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `NEO4J_URI` | yes | — | Aura / Neo4j bolt URI |
| `NEO4J_USERNAME` | yes | — | Database user |
| `NEO4J_PASSWORD` | yes | — | Database password |
| `NEO4J_DATABASE` | no | `neo4j` | Target database |
| `POKEGRAPH_POKEMON_NAMES` | no | *(unset = all)* | Comma-separated subset for short local runs |
| `POKEGRAPH_POKEAPI_POKEMON_LIST_URL` | no | full catalog URL | Catalog list endpoint |
| `POKEGRAPH_POKEAPI_CACHE_SIZE` | no | `2000` | In-memory PokeLance cache size |
| `POKEGRAPH_CACHE_DIR` | no | *(unset = no disk cache)* | Normalized source cache on disk |
| `POKEGRAPH_CACHE_TTL_S` | no | *(unset = no TTL)* | Disk-cache expiry in seconds |
| `NEO4J_READ_USERNAME` / `NEO4J_READ_PASSWORD` | no | write user | Optional read credential for `PokeGraphClient` |
| `POKEGRAPH_QUERY_TIMEOUT_S` | no | `30` | Catalog query timeout |
| `POKEGRAPH_MAX_PAGE_SIZE` | no | `200` | Maximum catalog `$limit` |

Example short run:

```bash
# in .env
POKEGRAPH_POKEMON_NAMES=pikachu,mareep,tyranitar
```

Leave `POKEGRAPH_POKEMON_NAMES` unset (or commented out) to ingest the full catalog.

## Learnset validation query

After ingesting Pikachu:

```cypher
MATCH (p:Pokemon {name: "pikachu"})
      -[:HAS_LEARNSET_ENTRY]->(e:LearnsetEntry)
      -[:TEACHES]->(m:Move {name: "thunderbolt"})
MATCH (e)-[:IN_VERSION_GROUP]->(vg:VersionGroup)
MATCH (e)-[:BY_LEARN_METHOD]->(lm:MoveLearnMethod)
RETURN vg.name, lm.name, e.level_learned_at, e.order
ORDER BY vg.name, lm.name, e.level_learned_at;
```

## Move enrichment validation query

```cypher
MATCH (m:Move {name: "thunderbolt"})
OPTIONAL MATCH (m)-[:HAS_TYPE]->(t:Type)
RETURN m.power, m.accuracy, m.pp, m.priority, m.type, m.damage_class, t.name AS type_node
```

```cypher
MATCH (m:Move {name: "headbutt"})
RETURN m.power, m.type, m.damage_class, m.contest_type,
       m.flinch_chance, m.short_effect
```

## Query catalog

Reusable parameterized Cypher (KLA-120) lives in [`queries/`](../../queries/). Trainer teams, Red, and progression stay out of that catalog until curated `Trainer` / `Progression` data exists.

## Testing the query API

The Python API is `PokeGraphClient`. Smoke it after ingest:

```bash
PYTHONPATH=src python examples/query_catalog.py --name pikachu --area pallet-town
PYTHONPATH=src python examples/query_catalog.py --name pikachu --version-id 15 --limit 10
```

### OpenAPI specification UI

Browse and execute the HTTP API in the browser, in the same style as the [Neo4j Aura API specification](https://neo4j.com/docs/aura/platform/api/specification/):

```bash
pip install -e ".[api]"
PYTHONPATH=src python -m pokegraph_api
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Expand an operation, click **Try it out**, fill parameters (HeartGold examples are prefilled), and **Execute**. `/` redirects to `/docs`; `/redoc` is the readable spec; `/openapi.json` is the raw contract.

The server uses the same `.env` Neo4j credentials as ingest. If the database is down, the spec page still loads and `/v1/health` reports `degraded`.

## Tests

```bash
PYTHONPATH=src python -m unittest tests.test_learnsets tests.test_moves tests.test_registry tests.test_client tests.test_source tests.test_packaging tests.test_api_spec -v
PYTHONPATH=src python -m unittest tests.integration.test_queries tests.integration.test_client -v
POKEGRAPH_LIVE_QUERY_TESTS=1 PYTHONPATH=src python -m unittest tests.integration.live_test_queries tests.integration.live_test_client -v
```

## Package layout

| Path | Role |
| --- | --- |
| [`../pokegraph/`](../pokegraph/) | Query client, shared Neo4j settings, `PokeApiSource` |
| [`config.py`](config.py) | Ingest settings on top of `Neo4jSettings` |
| [`schema.py`](schema.py) | Constraints, apply/verify, CLI, CAN_LEARN cleanup |
| [`resources.py`](resources.py) | Named-resource id/name helpers |
| [`cache.py`](cache.py) | Per-run enrichment dedupe cache |
| [`ingest.py`](ingest.py) | Orchestration + progress UI |
| [`writes/`](writes/) | Pokemon, learnsets, moves, encounters, evolution, types, source writers |

The local PokeLance checkout under `vendor/PokeLance` is ignored by Git.
