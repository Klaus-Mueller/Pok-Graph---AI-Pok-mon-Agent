// query: pokemon_in_area
// answers: Which recorded Encounter rows exist for this LocationArea and GameVersion?
// does_not: Prove a Pokémon is unobtainable here, or use AVAILABLE_IN_VERSION as evidence.
// required: $location_area_id (int), $version_id (int)
// optional: $method_id (int), $min_level (int), $max_level (int), $skip (int), $limit (int)
// returns: encounter_id, pokemon_id, pokemon_name, version_id, version_name, location_area_id, location_area_name, location_id, location_name, region_id, region_name, method_id, method_name, min_level, max_level, chance, condition_values, source_url, source_version, retrieved_at
// order: pokemon_id, location_area_id, method_id, min_level, encounter_id
// limit: coalesce($limit, 50)

MATCH (e:Encounter)-[:IN_VERSION]->(v:GameVersion {id: $version_id})
MATCH (e)-[:AT_LOCATION_AREA]->(la:LocationArea {id: $location_area_id})
MATCH (p:Pokemon)-[:HAS_ENCOUNTER]->(e)
MATCH (e)-[:USES_METHOD]->(m:EncounterMethod)
WHERE ($method_id IS NULL OR m.id = $method_id)
  AND ($min_level IS NULL OR e.max_level >= $min_level)
  AND ($max_level IS NULL OR e.min_level <= $max_level)
OPTIONAL MATCH (la)-[:PART_OF_LOCATION]->(l:Location)
OPTIONAL MATCH (l)-[:IN_REGION]->(r:Region)
RETURN e.id AS encounter_id,
       p.id AS pokemon_id,
       p.name AS pokemon_name,
       v.id AS version_id,
       v.name AS version_name,
       la.id AS location_area_id,
       la.name AS location_area_name,
       l.id AS location_id,
       l.name AS location_name,
       r.id AS region_id,
       r.name AS region_name,
       m.id AS method_id,
       m.name AS method_name,
       e.min_level AS min_level,
       e.max_level AS max_level,
       e.chance AS chance,
       e.condition_values AS condition_values,
       e.source_url AS source_url,
       e.source_version AS source_version,
       e.retrieved_at AS retrieved_at
ORDER BY pokemon_id, location_area_id, method_id, min_level, encounter_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
