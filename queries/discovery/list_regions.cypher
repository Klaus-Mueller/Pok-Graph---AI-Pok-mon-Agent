// query: list_regions
// answers: Which Region nodes are stored (optionally one id)?
// does_not: Claim geographic coverage for a game.
// required: (none)
// optional: $region_id (int), $skip (int), $limit (int)
// returns: region_id, region_name
// order: region_id
// limit: coalesce($limit, 50)

MATCH (r:Region)
WHERE $region_id IS NULL OR r.id = $region_id
RETURN r.id AS region_id,
       r.name AS region_name
ORDER BY region_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
