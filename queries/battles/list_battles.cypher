// query: list_battles
// answers: Which catalogued battles exist for a trainer in this exact game?
// does_not: Treat battle_order as a mandatory progression sequence.
// required: $trainer_id (string), $version_id (int)
// optional: $skip (int) = 0, $limit (int) = 50
// returns: battle_id, battle_key, battle_order, battle_name, version_id, location_name, location_id, location_mapping_status, progression_status, is_optional, victory_required_for_progression, progression_notes
MATCH (:Trainer {id:$trainer_id})-[:HAS_BATTLE]->(b:BattleEncounter)-[:IN_GAME_VERSION]->(v:GameVersion {id:$version_id})
OPTIONAL MATCH (b)-[:AT_LOCATION]->(l:Location)
RETURN b.id AS battle_id, b.battle_key AS battle_key, b.battle_order AS battle_order,
       b.name AS battle_name, v.id AS version_id, b.location_name AS location_name,
       l.id AS location_id, b.location_mapping_status AS location_mapping_status,
       b.progression_status AS progression_status, b.is_optional AS is_optional,
       b.victory_required_for_progression AS victory_required_for_progression,
       b.progression_notes AS progression_notes
ORDER BY battle_order, battle_id
SKIP $skip LIMIT $limit
