// query: find_location_area_by_name
// answers: Which LocationArea ids match this name (exact first, then prefix)?
// does_not: Claim the area has encounters in a given game.
// required: $name (string)
// optional: $skip (int), $limit (int)
// returns: location_area_id, location_area_name, location_id, region_id, match_rank
// order: match_rank, location_area_id
// limit: coalesce($limit, 50)

MATCH (la:LocationArea)
WHERE $name IS NOT NULL AND $name <> ''
  AND (
    toLower(la.name) = toLower($name)
    OR toLower(la.name) STARTS WITH toLower($name)
  )
OPTIONAL MATCH (la)-[:PART_OF_LOCATION]->(l:Location)
OPTIONAL MATCH (l)-[:IN_REGION]->(r:Region)
RETURN la.id AS location_area_id,
       la.name AS location_area_name,
       l.id AS location_id,
       r.id AS region_id,
       CASE WHEN toLower(la.name) = toLower($name) THEN 0 ELSE 1 END AS match_rank
ORDER BY match_rank, location_area_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
