// query: get_version_group
// answers: Does this VersionGroup id exist?
// does_not: List learnsets in the group.
// required: $version_group_id (int)
// optional: (none)
// returns: version_group_id

MATCH (vg:VersionGroup {id: $version_group_id})
RETURN vg.id AS version_group_id
