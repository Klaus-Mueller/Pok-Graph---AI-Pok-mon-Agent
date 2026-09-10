// query: find_species_by_name
// answers: Which PokemonSpecies ids match this name (exact first, then prefix)?
// does_not: Resolve a Pokémon form; use find_pokemon_by_name for Pokemon.id.
// required: $name (string)
// optional: $skip (int), $limit (int)
// returns: species_id, species_name, match_rank
// order: match_rank, species_id
// limit: coalesce($limit, 50)

MATCH (s:PokemonSpecies)
WHERE $name IS NOT NULL AND $name <> ''
  AND (
    toLower(s.name) = toLower($name)
    OR toLower(s.name) STARTS WITH toLower($name)
  )
RETURN s.id AS species_id,
       s.name AS species_name,
       CASE WHEN toLower(s.name) = toLower($name) THEN 0 ELSE 1 END AS match_rank
ORDER BY match_rank, species_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
