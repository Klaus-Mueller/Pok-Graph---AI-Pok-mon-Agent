// query: list_locations
// answers: Which Location nodes are stored, with their region when linked?
// does_not: Claim a location has encounters in any game.
// required: (none)
// optional: $region_id (int), $location_id (int), $skip (int), $limit (int)
// returns: location_id, location_name, region_id, region_name
// order: location_id
// limit: coalesce($limit, 50)

MATCH (l:Location)
OPTIONAL MATCH (l)-[:IN_REGION]->(r:Region)
WITH l, r
WHERE ($location_id IS NULL OR l.id = $location_id)
  AND ($region_id IS NULL OR r.id = $region_id)
RETURN l.id AS location_id,
       l.name AS location_name,
       r.id AS region_id,
       r.name AS region_name
ORDER BY location_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
