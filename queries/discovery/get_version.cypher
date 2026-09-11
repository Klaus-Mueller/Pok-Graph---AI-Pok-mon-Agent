// query: get_version
// answers: Does this GameVersion id exist?
// does_not: Resolve its VersionGroup or list encounters.
// required: $version_id (int)
// optional: (none)
// returns: version_id

MATCH (v:GameVersion {id: $version_id})
RETURN v.id AS version_id
