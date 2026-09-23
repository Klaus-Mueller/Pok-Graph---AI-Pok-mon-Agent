// query: pokemon_in_region
// answers: Which Pokemon have recorded encounters in the allowed locations, region, and game version?
// does_not: Check progression, capture prerequisites, or completeness of encounter coverage.
// required: $accessible_location_names (string), $region_name (string), $version_id (int)
// optional: $skip (int), $limit (int)
// returns: pokemon_id, pokemon_name, encounters, availability_scope, progression_checked
MATCH (p:Pokemon)-[:HAS_ENCOUNTER]->(e:Encounter)-[:IN_VERSION]->(:GameVersion {id:$version_id})
MATCH (e)-[:AT_LOCATION_AREA]->(a:LocationArea)-[:PART_OF_LOCATION]->(l:Location)-[:IN_REGION]->(:Region {name:$region_name})
WHERE l.name IN split($accessible_location_names, '|')
OPTIONAL MATCH (e)-[:USES_METHOD]->(method:EncounterMethod)
WITH DISTINCT p, e, a, l, method
ORDER BY p.id, l.id, a.id, e.id, method.id
WITH p, collect({encounter_id:e.id, location_id:l.id, location_name:l.name,
    location_area_id:a.id, location_area_name:a.name, method:method.name,
    min_level:e.min_level, max_level:e.max_level, conditions:e.condition_values}) AS encounters
RETURN p.id AS pokemon_id, p.name AS pokemon_name, encounters,
       'explicit_locations' AS availability_scope, false AS progression_checked
ORDER BY pokemon_id
SKIP coalesce($skip,0) LIMIT coalesce($limit,50)
