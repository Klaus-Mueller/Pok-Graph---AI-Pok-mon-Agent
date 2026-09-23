// query: context_for_battle
// answers: Where does this trainer battle occur, and what progression facts are recorded?
// does_not: Infer missing progression requirements or equate a building with its containing city.
// required: $trainer_id (string), $version_id (int), $battle_key (string)
// returns: battle_id, battle_key, battle_order, battle_name, location_name, location_id, canonical_location_name, progression_status, is_optional, victory_required_for_progression, progression_notes, available_after_text, available_until_text, skip_condition_text
MATCH (:Trainer {id:$trainer_id})-[:HAS_BATTLE]->(b:BattleEncounter {battle_key:$battle_key})-[:IN_GAME_VERSION]->(:GameVersion {id:$version_id})
OPTIONAL MATCH (b)-[:AT_LOCATION]->(l:Location)
RETURN b.id AS battle_id,b.battle_key AS battle_key,b.battle_order AS battle_order,
       b.name AS battle_name,b.location_name AS location_name,l.id AS location_id,
       l.name AS canonical_location_name,b.progression_status AS progression_status,
       b.is_optional AS is_optional,b.victory_required_for_progression AS victory_required_for_progression,
       b.progression_notes AS progression_notes,b.available_after_text AS available_after_text,
       b.available_until_text AS available_until_text,b.skip_condition_text AS skip_condition_text
