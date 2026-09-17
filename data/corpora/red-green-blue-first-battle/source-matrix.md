# Bulbapedia × PokéAPI source matrix

Research-only source coverage. The current battle ingestion excludes Source nodes, HAS_SOURCE edges and provenance properties; sources.json remains offline. Equipped moves use direct KNOWS_MOVE relationships, not TrainerMove nodes.

This matrix defines which source owns each field needed to answer questions about Blue's battles in Japanese Red and Green. It describes the current corpus and graph model; it is not a claim that every field has already been ingested.

| Field or domain | Bulbapedia | PokéAPI / existing Neo4j | Authoritative source for this corpus | Current status and gap |
| --- | --- | --- | --- | --- |
| Corpus scope key (`red-jp`, `green-jp`) | Supplies the article's Red/Green/Japanese Blue context | Does not use these project keys directly | Project mapping, validated against Neo4j | Resolved in `battle-fixture.json` |
| `GameVersion` identity and ID | Names the game context in prose | Canonical version vocabulary and IDs | PokéAPI-backed Neo4j | `red-jp` → `red-japan`/44; `green-jp` → `green-japan`/45 |
| `VersionGroup` and version membership | Context only | Canonical version-group model and relationships | PokéAPI-backed Neo4j | Both versions link to `red-green-japan`/28; live-read verification and coverage counts are in `entity-mappings.json` |
| Pokémon/species identity, canonical name and national ID | Team tables and links identify the species used by Blue | Canonical Pokémon/species nodes and IDs | PokéAPI-backed Neo4j for identity; Bulbapedia for the battle occurrence | Existing species nodes should be referenced, never duplicated |
| Trainer identity (`Blue`) and aliases | Names the rival and localized/article aliases | No trainer roster model for this battle corpus | Bulbapedia | `trainer:blue` is prepared; additional aliases remain unmodeled |
| Battle order, title and trigger | Section anchors, labels and progression notes | No equivalent battle chronology | Bulbapedia | Extracted for all eight sections; progression normalization remains |
| Battle location | Section heading and surrounding prose | Canonical Location catalog | Bulbapedia for the text; graph for the ID once matched | Seven locations mapped; Professor Oak's Laboratory maps to pallet-town and Silph Co. to saffron-city at containing-city granularity, with building names preserved |
| Victory requirement / optionality | Explicit progression statements (for example, the first battle is not required) | No story-progression source | Bulbapedia | First-battle outcome is captured; all other progression gates need review |
| Team membership, slot and level | Battle tables are the source of the actual opponent roster | No trainer-team equivalent in PokéAPI | Bulbapedia | 198 TrainerPokemon records prepared across both versions, with validated Pokemon/species references |
| Equipped moves in a battle | Battle tables list the moves Blue uses | PokéAPI can identify moves, but not this trainer's equipped set | Bulbapedia for the roster; PokéAPI for move identity | Store battle-specific move edges/records; do not overwrite learnsets |
| Abilities and held items in Generation I battles | Not reliably present in the extracted team tables | Modern PokéAPI fields do not establish historical trainer loadouts | Neither source currently sufficient | Keep explicitly unknown unless a Generation I-specific source is added |
| Player's available party, captures and pre-battle moves | May provide narrative/progression evidence, but not a complete legal-state model in this slice | Encounter, move and learnset endpoints provide canonical options, not the player's reachable state | Combined, with Bulbapedia for gates and PokéAPI for canonical data | Missing for strategy answers; must be modeled per battle/version |
| Move/species canonical metadata | Links and names can be normalized from the article | Types, moves, learnsets and encounter records | PokéAPI-backed Neo4j | Use graph canonical nodes and retain Bulbapedia evidence links |
| Type effectiveness and battle mechanics | May describe strategy, but is not the canonical mechanics dataset here | Current graph matchup data is not Generation I-specific | Neither current source alone | Add/validate a Generation I rule table before claiming “advantage” |
| Source citation, revision and license | Page URL, revision, retrieval and CC BY-NC-SA 2.5 notice | PokéAPI/graph provenance for imported canonical records | Each source for its own material | Detailed Bulbapedia provenance remains in `sources.json`; chunk payload stays lean |
| Embeddings, retrieval ranking and answer quality | Not supplied | Not supplied | Project pipeline | Outside the source corpus; handled by later RAG/indexing work |

## Fields currently absent from both sources

The current Red/Green battle slice cannot establish the player's exact pre-battle team and moves, a complete progression-gated list of legal counters, Generation I damage calculation details, or a universally “best” strategy. Those require additional game-specific mechanics/progression sources and an explicit definition of “advantage.”

## Modeling rule

Keep canonical `Pokemon`, `PokemonSpecies`, `Move`, `GameVersion` and `VersionGroup` data from the existing graph. Add battle-specific facts as relationships or records keyed by battle, version and trainer (for example, `BattleEncounter` and `TrainerPokemon`). Bulbapedia evidence should support those records; it should not replace canonical PokéAPI entities.
