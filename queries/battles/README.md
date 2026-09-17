# Battle queries

The model uses TrainerPokemon-KNOWS_MOVE->Move, with relationship id, slot and
observed_type_name. No source data is returned or required.

- list_battles.cypher: trainer_id='trainer:blue', version_id=44 or 45, skip=0, limit=50.
- team_for_battle.cypher: same parameters plus battle_key='first' and
  starter_species_id=1,4 or 7. Returns one row per equipped move, ordered by member
  and move slot. Champion has at most 24 rows.
- version_context.cypher: battle_id='battle:blue:44:first', returns group and coverage.
- verify_ingestion.cypher: battle_ids is the list of the 16 prepared IDs. The CLI
  --verify-server supplies them and requires actual == expected for every row.

These are standalone Cypher queries, not registered API endpoints. Battle order
is not a prerequisite chain; equipped moves do not prove player learnset legality.
See the corpus README for rollback integration tests and persistent verification.

## Location-filtered type-only pilot

`../encounters/pokemon_in_region.cypher` takes `region_name='kanto'`,
`version_id=44` or `45`, `accessible_location_names=['kanto-route-22']`,
`skip=0`, `limit=200`. It returns one row per recorded
encounter Pokémon with encounter locations, methods, levels, and conditions.
Availability means recorded encounters in the explicitly allowed locations and selected region/version, not
confirmed access at the player's story point.

`regional_candidates_for_battle.cypher` takes `trainer_id='trainer:blue'`,
`version_id=44` or `45`, `battle_key='second-optional'`,
`starter_species_id=1`, `4`, or `7`,
`accessible_location_names=['kanto-route-22']`, `skip=0`, `limit=200`.
It derives the region from the battle location, restricts encounters to the supplied
canonical Location names, and ranks distinct candidates by
members covered, then Pokémon ID. Each candidate contains all opponent members
and all candidate attack-type factors, including immunities, neutral results,
and unknowns. Paginate through all candidates when requesting a full review;
filter `members_covered > 0` in the consumer for a shortlist.

Defender types come from the battle's observed types. Candidate types and the
stored DAMAGE_TO chart are not generation-verified. This follows the existing
sparse-chart convention: missing edges mean neutral only when the attacker has
chart relationships; an entirely missing chart remains unknown. This convention
assumes ingestion of a complete sparse chart, not merely a partial set of edges.
No moves or learnsets are used. A candidate type is a hypothetical attack type,
not proof of an equipped or learnable move. Results include `availability_scope`,
`progression_checked`, `moves_checked`, and `mechanics_basis` to state the limits.
Zero coverage with incomplete data is not proof that no advantage exists.

These queries are standalone, not API/QueryRegistry registrations. An empty
comparison can mean a missing battle variant, location/region link, or encounter
data; it must not be presented as proof that no Pokémon are available.

Read-only server tests (requires the ingested pilot):

```sh
PYTHONPATH=src POKEGRAPH_REGIONAL_INTEGRATION=1 .venv/bin/python -m unittest tests.integration.test_regional_battle_queries -v
```

`accessible_location_names` is required on both queries. It accepts multiple
canonical Location names; an empty list or entirely unknown names returns no
candidates, with no region-wide fallback. Unknown names in a mixed list contribute
no encounters. Duplicate names do not duplicate candidates. Existing filenames
are retained, but callers must now supply this parameter. q14 fixes it to
`['kanto-route-22']`. Results carry `availability_scope='explicit_locations'`.

Location access is supplied by the caller, not inferred from progression. This
filter does not enforce encounter method prerequisites or a level cap within an
allowed location; discovery still returns methods, level ranges, and conditions.
Move feasibility remains outside scope.
