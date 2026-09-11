# PokéGraph Cypher catalog (KLA-120)

Reusable, parameterized Cypher queries for the ingested PokéAPI graph. Files are API-independent and can be run in Neo4j Browser or `neo4j-cli query`. HeartGold/SoulSilver appear only in [`examples/`](examples/) and integration tests — never in reusable `.cypher` bodies.

The catalog answers questions the current graph can support with stable columns and evidence IDs. Call it from `PokeGraphClient` in [`src/pokegraph/`](../src/pokegraph/), or browse and Try it out in the OpenAPI UI (`python -m pokegraph_api`, then [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)).

## Parameter domains

Do not mix these. A game id is not a version-group id.

| Context | Parameter | Node |
| --- | --- | --- |
| Recorded encounters / availability | `$version_id` | `GameVersion` |
| Learnable moves | `$version_group_id` | `VersionGroup` |
| Geography | `$region_id`, `$location_id`, `$location_area_id` | `Region` / `Location` / `LocationArea` |
| Pokémon / species | `$pokemon_id`, `$species_id` | `Pokemon` / `PokemonSpecies` |

When the caller has a game and needs a learnset, resolve the group first (`discovery/resolve_version_group.cypher`). If both `$version_id` and `$version_group_id` are supplied and `GameVersion-[:IN_VERSION_GROUP]->VersionGroup` does not exist, the query returns **zero rows**. It does not guess the group.

## File conventions

Each `.cypher` file starts with a `//` header:

- `answers` — question the query is allowed to answer
- `does_not` — claims the result must not be stretched into
- `required` / `optional` — parameters
- `returns` — stable column names (IDs first)
- `order` / `limit` — deterministic listing

Optional listing parameters:

| Parameter | Default | Notes |
| --- | --- | --- |
| `$skip` | `0` | Pass `null` to use the default |
| `$limit` | `50` | Pass `null` to use the default |

Unbound parameters error in Neo4j. Callers must pass every mentioned parameter; use `null` for unused optionals.

Main queries look up nodes by `id` (existing uniqueness constraints). Name lookup is discovery-only and may LabelScan until a read index is justified by `EXPLAIN` in [`examples/plans.md`](examples/plans.md).

## Catalog

| Block | Directory | Main result |
| --- | --- | --- |
| Discovery | [`discovery/`](discovery/) | IDs and stored coverage |
| Encounters | [`encounters/`](encounters/) | Pokémon, version, area, method, levels, chance, conditions |
| Learnsets | [`learnsets/`](learnsets/) | Move, method, level, provenance |
| Evolutions | [`evolutions/`](evolutions/) | `EVOLVES_TO` conditions (alternatives preserved) |
| Matchups | [`matchups/`](matchups/) | Combined type factors and offensive coverage |

`CAN_LEARN` is not in this catalog: it drops method, version group, and level.

## Contract limits

### Encounters

Rows always include `encounter_id` and walk `Encounter-[:IN_VERSION]->GameVersion`. `AVAILABLE_IN_VERSION` and `CAN_BE_FOUND_IN` are ingest shortcuts, not evidence.

Absence of a row means the graph has no matching encounter record. It does **not** prove the Pokémon is unobtainable.

Level filters use interval overlap: a search for levels 10–20 includes an encounter that occurs at 15–25.

### Learnsets

Rows always include `learnset_entry_id` and walk `LearnsetEntry-[:IN_VERSION_GROUP]->VersionGroup`.

`level_learned_at = 0` does **not** mean the move is available at the start of the game. That value is stored for machine / tutor / egg (and similar) methods. Filter on `learn_method_id` / `learn_method_name`.

`LearnsetEntry` carries `source_url`, `source_version`, and `retrieved_at`. Encounter, evolution, and type evidence expose the same columns when present. Older rows stay null until they are re-ingested; the catalog does not invent a collection date.

### Evolutions

Query `PokemonSpecies` by `$species_id`, not a Pokémon form. Each `EVOLVES_TO.id` is one condition; branching alternatives are separate rows.

`EVOLVES_TO.version_group` is a PokéAPI **name string**, not a `VersionGroup` node. If it is null, do not claim the evolution is (or is not) available in a given game.

### Matchups

Type nodes, `DAMAGE_TO`, and move typing are **not historically versioned**. Loading several games does not make these charts generation-correct.

- A missing `DAMAGE_TO` edge is treated as neutral (`1.0`) only after the attacking type has at least one outgoing `DAMAGE_TO` (enriched).
- Otherwise `factor` is null and `data_complete` is `false`.
- Dual-type defenders multiply per-type factors. Immunity (`0.0`) zeroes the result.
- Classes: `immune` (0), `resist` (<1), `neutral` (1), `weak` (>1), `unknown` (incomplete).
- “Advantage” means offensive coverage (combined factor > 1) by type or learnable move. It is not a win prediction.
- Matchup queries do not take `$version_id`.

To assert generation-specific effectiveness, the model and ingest must be extended.

## Deferred (not in this catalog)

These KLA-120 items stay out of scope until curated data exists. The ingest does not create `Trainer`, `TrainerPokemon`, or `Progression`.

| Future query | Dependency |
| --- | --- |
| Pokémon reachable before a milestone in a given game | Progression and access rules |
| A trainer’s team in a specific battle | Battle model, `Trainer`, `TrainerPokemon` |
| Coverage against that team under progression | Both of the above, plus compatible battle rules |

Do not stub these queries against empty labels.

## Examples and tests

- [`examples/parameters.json`](examples/parameters.json) — IDs chosen after checking live coverage (HG/SS preferred).
- [`examples/expected-results.json`](examples/expected-results.json) — recorded rows plus a dataset fingerprint.
- [`examples/plans.md`](examples/plans.md) — `EXPLAIN` of the main queries. Extra indexes only if a plan shows a hot LabelScan.

Fixture integration tests use reserved negative IDs and roll back:

```bash
PYTHONPATH=src python -m unittest tests.integration.test_queries tests.integration.test_client -v
```

Read-only live checks (requires a populated database):

```bash
POKEGRAPH_LIVE_QUERY_TESTS=1 PYTHONPATH=src python -m unittest tests.integration.live_test_queries tests.integration.live_test_client -v
```

Refresh example artifacts:

```bash
PYTHONPATH=src python -m tests.integration.record_examples
```
