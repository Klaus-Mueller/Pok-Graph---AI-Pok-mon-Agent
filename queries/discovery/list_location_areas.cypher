// query: list_location_areas
// answers: Which LocationArea nodes are stored, optionally only those with an encounter in a game?
// does_not: List every in-game map; only stored areas (and recorded encounters when $version_id is set).
// required: (none)
// optional: $region_id (int), $location_id (int), $location_area_id (int), $version_id (int), $skip (int), $limit (int)
// returns: location_area_id, location_area_name, location_id, location_name, region_id, region_name
// order: location_area_id
// limit: coalesce($limit, 50)

MATCH (la:LocationArea)
OPTIONAL MATCH (la)-[:PART_OF_LOCATION]->(l:Location)
OPTIONAL MATCH (l)-[:IN_REGION]->(r:Region)
WITH la, l, r
WHERE ($location_area_id IS NULL OR la.id = $location_area_id)
  AND ($location_id IS NULL OR l.id = $location_id)
  AND ($region_id IS NULL OR r.id = $region_id)
  AND (
    $version_id IS NULL OR EXISTS {
      MATCH (e:Encounter)-[:AT_LOCATION_AREA]->(la)
      MATCH (e)-[:IN_VERSION]->(:GameVersion {id: $version_id})
    }
  )
RETURN la.id AS location_area_id,
       la.name AS location_area_name,
       l.id AS location_id,
       l.name AS location_name,
       r.id AS region_id,
       r.name AS region_name
ORDER BY location_area_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
