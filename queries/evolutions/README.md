# Evolutions

Query `PokemonSpecies` by `$species_id`. Each `EVOLVES_TO.id` is one condition; alternatives are separate rows.

`EVOLVES_TO.version_group` is a PokéAPI name string, not a `VersionGroup` node. If it is null, do not claim historical availability in a game.

| File | Question |
| --- | --- |
| [`evolutions_from_species.cypher`](evolutions_from_species.cypher) | What does this species evolve into, and under which conditions? |
| [`evolutions_to_species.cypher`](evolutions_to_species.cypher) | Which species evolve into this one, and under which conditions? |
| [`evolution_chain.cypher`](evolution_chain.cypher) | Which `EVOLVES_TO` edges share this species' evolution chain? |
