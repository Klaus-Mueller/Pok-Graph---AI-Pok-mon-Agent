// query: list_versions_with_data
// answers: Which GameVersion nodes have at least one Encounter and/or an IN_VERSION_GROUP link?
// does_not: Claim the game catalog is complete, or that a game is playable end-to-end.
// required: (none)
// optional: $skip (int), $limit (int)
// returns: version_id, version_name, version_group_id, version_group_name, encounter_count
// order: version_id
// limit: coalesce($limit, 50)

MATCH (v:GameVersion)
OPTIONAL MATCH (e:Encounter)-[:IN_VERSION]->(v)
OPTIONAL MATCH (v)-[:IN_VERSION_GROUP]->(vg:VersionGroup)
WITH v, vg, count(DISTINCT e) AS encounter_count
WHERE encounter_count > 0 OR vg IS NOT NULL
RETURN v.id AS version_id,
       v.name AS version_name,
       vg.id AS version_group_id,
       vg.name AS version_group_name,
       encounter_count
ORDER BY version_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
