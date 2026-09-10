# Discovery

IDs and stored coverage. These queries do not assert that a game, area, or Pokémon is complete.

| File | Question |
| --- | --- |
| [`list_versions_with_data.cypher`](list_versions_with_data.cypher) | Which games have encounter and/or version-group links? |
| [`list_version_groups_with_data.cypher`](list_version_groups_with_data.cypher) | Which version groups have learnset rows? |
| [`resolve_version_group.cypher`](resolve_version_group.cypher) | What version group belongs to this game? |
| [`list_regions.cypher`](list_regions.cypher) | Which regions are stored? |
| [`list_locations.cypher`](list_locations.cypher) | Which locations are stored? |
| [`list_location_areas.cypher`](list_location_areas.cypher) | Which areas are stored (optionally with encounters in a game)? |
| [`find_pokemon_by_name.cypher`](find_pokemon_by_name.cypher) | Resolve a Pokémon name to `pokemon_id` |
| [`find_species_by_name.cypher`](find_species_by_name.cypher) | Resolve a species name to `species_id` |
| [`find_move_by_name.cypher`](find_move_by_name.cypher) | Resolve a move name to `move_id` |
| [`find_location_area_by_name.cypher`](find_location_area_by_name.cypher) | Resolve an area name to `location_area_id` |
| [`dataset_fingerprint.cypher`](dataset_fingerprint.cypher) | Counts and latest learnset retrieval time |
