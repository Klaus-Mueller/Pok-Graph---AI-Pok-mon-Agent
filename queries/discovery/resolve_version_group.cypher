// query: resolve_version_group
// answers: Which VersionGroup is linked to this GameVersion?
// does_not: Infer a group when the relationship is missing, or accept an incoherent game/group pair.
// required: $version_id (int)
// optional: $version_group_id (int) — when set, the row is returned only if it matches the linked group
// returns: version_id, version_name, version_group_id, version_group_name
// order: version_id
// limit: at most one row per game (zero if missing or incoherent)

MATCH (v:GameVersion {id: $version_id})-[:IN_VERSION_GROUP]->(vg:VersionGroup)
WHERE $version_group_id IS NULL OR vg.id = $version_group_id
RETURN v.id AS version_id,
       v.name AS version_name,
       vg.id AS version_group_id,
       vg.name AS version_group_name
ORDER BY version_id
