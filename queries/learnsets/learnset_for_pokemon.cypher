// query: learnset_for_pokemon
// answers: Which LearnsetEntry rows exist for this Pokemon and VersionGroup?
// does_not: Treat level_learned_at = 0 as early-game access, or bind a learnset to a single GameVersion.
// required: $pokemon_id (int), $version_group_id (int)
// optional: $learn_method_id (int), $skip (int), $limit (int)
// returns: learnset_entry_id, pokemon_id, pokemon_name, move_id, move_name, version_group_id, version_group_name, learn_method_id, learn_method_name, level_learned_at, learn_order, source_url, source_version, retrieved_at
// order: learn_method_id, level_learned_at, move_id, learnset_entry_id
// limit: coalesce($limit, 50)

MATCH (p:Pokemon {id: $pokemon_id})-[:HAS_LEARNSET_ENTRY]->(e:LearnsetEntry)
MATCH (e)-[:IN_VERSION_GROUP]->(vg:VersionGroup {id: $version_group_id})
MATCH (e)-[:TEACHES]->(m:Move)
MATCH (e)-[:BY_LEARN_METHOD]->(lm:MoveLearnMethod)
WHERE $learn_method_id IS NULL OR lm.id = $learn_method_id
RETURN e.id AS learnset_entry_id,
       p.id AS pokemon_id,
       p.name AS pokemon_name,
       m.id AS move_id,
       m.name AS move_name,
       vg.id AS version_group_id,
       vg.name AS version_group_name,
       lm.id AS learn_method_id,
       lm.name AS learn_method_name,
       e.level_learned_at AS level_learned_at,
       e.order AS learn_order,
       e.source_url AS source_url,
       e.source_version AS source_version,
       e.retrieved_at AS retrieved_at
ORDER BY learn_method_id, level_learned_at, move_id, learnset_entry_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
