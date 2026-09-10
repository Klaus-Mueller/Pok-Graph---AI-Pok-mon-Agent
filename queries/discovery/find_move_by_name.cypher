// query: find_move_by_name
// answers: Which Move ids match this name (exact first, then prefix)?
// does_not: Say whether any Pokémon learns the move.
// required: $name (string)
// optional: $skip (int), $limit (int)
// returns: move_id, move_name, match_rank
// order: match_rank, move_id
// limit: coalesce($limit, 50)

MATCH (m:Move)
WHERE $name IS NOT NULL AND $name <> ''
  AND (
    toLower(m.name) = toLower($name)
    OR toLower(m.name) STARTS WITH toLower($name)
  )
RETURN m.id AS move_id,
       m.name AS move_name,
       CASE WHEN toLower(m.name) = toLower($name) THEN 0 ELSE 1 END AS match_rank
ORDER BY match_rank, move_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
