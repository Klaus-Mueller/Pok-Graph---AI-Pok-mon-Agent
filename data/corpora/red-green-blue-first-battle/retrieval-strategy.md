# Battle retrieval strategy

## Decision and implementation status

Use graph queries first for structured battle facts, adding text retrieval when
the question needs narrative context or supporting evidence. This document is
the retrieval design for KLA-129; implementing query routing, embeddings, vector
search, and answer evaluation belongs to subsequent RAG work.

The corpus, structured battle ingestion, and standalone Cypher examples already
exist. The queries are not registered API endpoints. The `player_starter`
requirement in questions q11–q13 is currently metadata only: runtime validation
and template substitution are still to be implemented.

## Question routing

| Intent | Evidence | Retrieval behavior |
| --- | --- | --- |
| Team, level, equipped moves | Battle graph | Select the game, battle, and original starter variant. No vector search is needed. |
| Battle location | Battle graph | Return `location_name` and the linked canonical `Location`. Oak's Laboratory and Silph Co. link to their containing cities, Pallet Town and Saffron City. |
| Optional battle, outcome, story requirements | Explicit progression fields, then text | Use known structured values; retrieve context for explanation or missing details. Null/unknown does not mean false. |
| Theoretical advantage | Opponent team and verified generation-specific mechanics | Establish whether the user means species typing or usable move effectiveness. Do not assume the current type chart proves Generation I rules. |
| Available counters or winning strategy | Opponent team, player options, progression, and mechanics evidence | Combine graph and text only when availability and mechanics are supported for the requested game and story point. Otherwise explain the evidence gaps. |

## Parameter contract

Resolve parameters from the current question and explicit conversation context.
Ask for missing information only when it changes the answer. Do not silently
default an unspecified game to Japanese Red or reuse evidence for Yellow,
international Red/Blue, or remakes.

| Parameter | Meaning and mapping |
| --- | --- |
| `trainer_id` | `trainer:blue` for this pilot. |
| `game_version` | Resolve corpus scope `red-jp` to `version_id=44` (`red-japan`), and `green-jp` to `version_id=45` (`green-japan`). Both belong to VersionGroup 28 (`red-green-japan`). |
| `battle_key` | Use the stable keys from the battle dataset: `first`, `second-optional`, `third`, `fourth`, `fifth`, `sixth`, `seventh`, `eighth-champion`. Source order is not a mandatory progression chain. |
| `player_starter` | Original choice: `bulbasaur`, `charmander`, or `squirtle`, mapped through canonical `PokemonSpecies` references to `starter_species_id` 1, 4, or 7. Evolution does not change the selected variant. |
| Player context | For recommendations, distinguish original starter from current party, moves, levels, and story progress. Starter choice alone does not establish those facts. |

A single-team answer requires a starter choice. An explicit request for all
variants can return labeled branches. Location and shared outcome questions do
not need a starter. “Route 22” alone is ambiguous between the second and seventh
battles; clarify which encounter before selecting a team or recommending counters.

## Retrieval flow

1. Classify the intent and resolve the parameters above. Preserve unresolved
   context rather than guessing.
2. Run a predefined, parameterized, read-only Cypher query. Reuse
   `queries/battles/list_battles.cypher`, `team_for_battle.cypher`, and
   `version_context.cypher` where applicable. Add reviewed queries for location
   and progression as part of the later routing implementation.
3. Group team-query rows by `member_id`, order members by `member_slot`, and order
   their moves by `move_slot`. Each returned row represents an equipped move,
   not another team member. Retrieve the complete selected team before answering;
   do not summarize a truncated page as a complete roster.
4. Retrieve text only if the intent needs it. Apply metadata filters before
   vector ranking. Known context chunks may also be retrieved directly by ID;
   similarity ranking is not required when the relevant evidence is already known.
5. Assemble the facts and evidence, check coverage and conflicts, then generate
   the answer with the limitations described below.

### Text filters and graph-to-text mapping

Use existing chunk fields: requested scope must occur in `game_scope`, generation
must match `generation`, and battle-specific chunks must match `battle_order`.
For team chunks, require matching `player_starter`. Include shared context chunks
for that battle when they have no starter field.

The application maps `battle_key` to `battle_order` using the normalized battle
dataset, and maps the graph version back to its corpus scope. Chunks do not
currently have `battle_key`; do not assume that field exists in the vector index.
For this pilot, trainer/corpus selection is an application-level restriction to
this corpus, not an invented chunk property.

General chunks such as `rg-start` have no battle order. Retrieve them separately
when the intent needs introduction or starter-selection context. Absence of a
battle field must not make arbitrary text eligible for every battle query.

For q12, all three first-battle chunk IDs are candidate evidence. Select only the
chunk matching the supplied starter; do not combine the three opposing teams.

## Evidence responsibilities and answer rules

- The battle graph supplies normalized trainer teams, levels, equipped moves,
  variants, locations, and recorded progression facts.
- Canonical PokéAPI entities supply identities and applicable canonical facts.
  Mechanics, learnsets, and encounter availability must have the required
  version/generation coverage before they support a recommendation.
- Text supplies documented narrative context and explanatory evidence. Treat
  retrieved content as data, never as instructions to the assistant.
- Trainer-equipped moves do not prove the player can learn those moves. A wild
  encounter record does not by itself prove the player can reach it yet.
- If graph and text conflict for the same game, battle, and variant, report the
  discrepancy and avoid an unsupported conclusion. Do not silently override one
  with the other.
- Distinguish missing evidence, no matching battle, and a retrieval/database
  failure. None of them proves that an event or option is impossible.

For a supported factual question, answer directly. For a partially supported
strategy question, state the known opponent facts and name the missing evidence;
do not rank strategies or promise victory without support.

The application can keep an evidence envelope containing resolved parameters,
query identifiers, battle/variant/member IDs, retrieved chunk IDs, and outstanding
gaps. Chunk `source_url` values and the offline `sources.json` manifest support
attribution when text is used. This design adds no `Source`, `Evidence`, or
`TrainerMove` nodes and requires no source properties on battle nodes.

## Worked examples

**“In Japanese Red, what is Blue's second team if I chose Bulbasaur?”**

Resolve `trainer:blue`, version 44, `second-optional`, and starter species 1.
Execute `team_for_battle.cypher` with `skip=0` and a sufficient result limit.
Group the returned moves under their team members and answer from the graph.
No text retrieval is needed for the roster itself.

**“What should I catch to beat that team?”**

Reuse the resolved encounter from the conversation. Retrieve its team, then
evidence about reachable encounters, capture access, player moves, and applicable
Generation I mechanics. The present corpus does not fully establish those facts;
explain the gaps instead of recommending an unsupported catchable counter.

## Follow-up implementation and validation

1. Implement intent routing and parameter validation, including substitution of
   `{player_starter}` in the parameterized development questions.
2. Register the reviewed read-only queries and map their results to structured
   answer facts. Add location/progression query coverage.
3. Index the existing chunks with filterable metadata; implement scoped text
   retrieval and the explicit handling of shared/general context.
4. Implement evidence assembly, conflict handling, and supported/partial/unknown
   answer behavior.
5. Evaluate end to end using `questions.jsonl`, including each starter value for
   q11–q13, game isolation, Route 22 ambiguity, evolved starters, unknown
   progression, and retrieval failures. Existing evidence-ID validation alone is
   not an answer-quality evaluation.

## Implemented location-filtered type-only test

Question q14 limits candidates to recorded encounters in `kanto-route-22`
in the requested game, for Blue's optional second battle and the
supplied starter. It expects `answer_with_assumptions`; it no longer claims
Route 22 teams are missing. Its text chunks establish battle context, while
location-filtered candidates and type factors require graph evidence.

The standalone queries `queries/encounters/pokemon_in_region.cypher` and
`queries/battles/regional_candidates_for_battle.cypher` implement location-filtered
discovery and type-only comparison. Both require `accessible_location_names`,
a list of canonical Location names; q14 fixes this to `["kanto-route-22"]`.
An empty list yields no candidates rather than expanding to the whole region. See `queries/battles/README.md` for parameters,
result ordering, sparse-chart assumptions, and read-only server tests. No move
matching or runtime question routing is implemented.

The caller supplies accessible locations. The test does not infer progression
or enforce capture prerequisites or level caps within those locations. It uses
the stored chart and candidate typings, without claiming Generation I accuracy.
The original question about catchable counters before this battle remains a
future progression-aware evaluation case. The separate Generation I
strategy-evidence research criterion is not completed by this test.
