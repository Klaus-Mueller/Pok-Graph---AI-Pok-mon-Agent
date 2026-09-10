// query: compare_versions
// answers: Which Pokémon have recorded encounters in both GameVersions, only A, or only B?
// does_not: Prove a Pokémon is exclusive or unobtainable; membership reflects stored Encounter rows only.
// required: $version_id_a (int), $version_id_b (int)
// optional: $location_area_id (int), $skip (int), $limit (int)
// returns: membership, pokemon_id, pokemon_name, encounter_ids_a, encounter_ids_b
// order: membership, pokemon_id
// limit: coalesce($limit, 50)

MATCH (p:Pokemon)-[:HAS_ENCOUNTER]->(e:Encounter)-[:IN_VERSION]->(v:GameVersion)
WHERE v.id IN [$version_id_a, $version_id_b]
  AND (
    $location_area_id IS NULL OR EXISTS {
      MATCH (e)-[:AT_LOCATION_AREA]->(:LocationArea {id: $location_area_id})
    }
  )
WITH p.id AS pokemon_id,
     p.name AS pokemon_name,
     collect(DISTINCT CASE WHEN v.id = $version_id_a THEN e.id END) AS raw_ids_a,
     collect(DISTINCT CASE WHEN v.id = $version_id_b THEN e.id END) AS raw_ids_b
WITH pokemon_id,
     pokemon_name,
     [id IN raw_ids_a WHERE id IS NOT NULL] AS encounter_ids_a,
     [id IN raw_ids_b WHERE id IS NOT NULL] AS encounter_ids_b
WITH pokemon_id,
     pokemon_name,
     encounter_ids_a,
     encounter_ids_b,
     CASE
       WHEN size(encounter_ids_a) > 0 AND size(encounter_ids_b) > 0 THEN 'both'
       WHEN size(encounter_ids_a) > 0 THEN 'only_a'
       ELSE 'only_b'
     END AS membership
RETURN membership,
       pokemon_id,
       pokemon_name,
       encounter_ids_a,
       encounter_ids_b
ORDER BY membership, pokemon_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
