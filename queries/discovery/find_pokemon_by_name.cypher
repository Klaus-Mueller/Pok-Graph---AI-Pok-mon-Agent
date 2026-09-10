// query: find_pokemon_by_name
// answers: Which Pokemon ids match this name (exact first, then prefix)?
// does_not: Rank popularity or disambiguate forms beyond stored name/id.
// required: $name (string)
// optional: $skip (int), $limit (int)
// returns: pokemon_id, pokemon_name, species_id, match_rank
// order: match_rank, pokemon_id
// limit: coalesce($limit, 50)

MATCH (p:Pokemon)
WHERE $name IS NOT NULL AND $name <> ''
  AND (
    toLower(p.name) = toLower($name)
    OR toLower(p.name) STARTS WITH toLower($name)
  )
OPTIONAL MATCH (p)-[:SPECIES]->(s:PokemonSpecies)
RETURN p.id AS pokemon_id,
       p.name AS pokemon_name,
       s.id AS species_id,
       CASE WHEN toLower(p.name) = toLower($name) THEN 0 ELSE 1 END AS match_rank
ORDER BY match_rank, pokemon_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
