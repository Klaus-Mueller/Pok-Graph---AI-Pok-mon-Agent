# Learnsets

Learnable moves for a `VersionGroup`. Every result includes `learnset_entry_id`, `source_url`, and `retrieved_at`.

`level_learned_at = 0` is not “available from the start of the game”. Separate rows by `learn_method_id`.

Resolve `$version_group_id` from a game with `discovery/resolve_version_group.cypher` before calling these queries. Do not filter learnsets by `$version_id` directly.

| File | Question |
| --- | --- |
| [`learnset_for_pokemon.cypher`](learnset_for_pokemon.cypher) | Which moves does this Pokémon learn in this version group? |
| [`who_learns_move.cypher`](who_learns_move.cypher) | Which Pokémon learn this move in this version group? |
