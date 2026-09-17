// query: version_context
// answers: Which exact VersionGroup and recorded data coverage support this battle?
// does_not: Substitute another game when Japanese-version coverage is missing.
// required: $battle_id (str)
// returns: battle_id, version_id, version_name, version_group_id, version_group_name, encounter_count, learnset_count
MATCH (b:BattleEncounter {id:$battle_id})-[:IN_GAME_VERSION]->(v:GameVersion)
OPTIONAL MATCH (v)-[:IN_VERSION_GROUP]->(vg:VersionGroup)
OPTIONAL MATCH (e:Encounter)-[:IN_VERSION]->(v)
WITH b,v,vg,count(DISTINCT e) AS encounter_count
OPTIONAL MATCH (le:LearnsetEntry)-[:IN_VERSION_GROUP]->(vg)
RETURN b.id AS battle_id,v.id AS version_id,v.name AS version_name,
       vg.id AS version_group_id,vg.name AS version_group_name,
       encounter_count,count(DISTINCT le) AS learnset_count
