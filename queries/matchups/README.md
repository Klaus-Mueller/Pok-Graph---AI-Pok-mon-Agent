# Matchups

Type effectiveness from stored `DAMAGE_TO` edges and Pokémon/move types. **Not historically versioned.** Several ingested games do not make these charts generation-correct. These queries do not take `$version_id`.

Missing `DAMAGE_TO` is neutral (`1.0`) only when the attacking type already has at least one outgoing `DAMAGE_TO`. Otherwise `factor` is null and `data_complete` is `false`.

Dual-type defenders multiply per-type factors. Immunity (`0.0`) zeroes the product.

“Advantage” means combined factor > 1. It is not a win prediction.

| File | Question |
| --- | --- |
| [`defensive_profile.cypher`](defensive_profile.cypher) | How does each stored attacking type hit this Pokémon? |
| [`type_effectiveness.cypher`](type_effectiveness.cypher) | What is the combined factor of one attacking type vs this Pokémon? |
| [`offensive_coverage_by_types.cypher`](offensive_coverage_by_types.cypher) | How do this Pokémon's types hit a defender? |
| [`offensive_coverage_by_learnset.cypher`](offensive_coverage_by_learnset.cypher) | How do this Pokémon's learnable moves hit a defender in a version group? |
