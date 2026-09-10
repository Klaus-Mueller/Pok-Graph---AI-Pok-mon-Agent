// query: list_version_groups_with_data
// answers: Which VersionGroup nodes have at least one LearnsetEntry?
// does_not: Claim every game in the group is ingested, or that the learnset is complete.
// required: (none)
// optional: $skip (int), $limit (int)
// returns: version_group_id, version_group_name, learnset_entry_count, region_ids
// order: version_group_id
// limit: coalesce($limit, 50)

MATCH (e:LearnsetEntry)-[:IN_VERSION_GROUP]->(vg:VersionGroup)
WITH vg, count(e) AS learnset_entry_count
OPTIONAL MATCH (vg)-[:IN_REGION]->(r:Region)
WITH vg, learnset_entry_count, r
ORDER BY vg.id, r.id
WITH vg, learnset_entry_count, collect(r.id) AS region_ids
RETURN vg.id AS version_group_id,
       vg.name AS version_group_name,
       learnset_entry_count,
       region_ids
ORDER BY version_group_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
