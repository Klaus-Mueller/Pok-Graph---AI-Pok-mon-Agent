// query: team_for_battle
// answers: Which Pokemon and equipped moves does this starter-conditioned team contain?
// does_not: Infer learnset legality, damage or player access from trainer loadouts.
// required: $trainer_id (string), $version_id (int), $battle_key (string), $starter_species_id (int)
// optional: $skip (int) = 0, $limit (int) = 50
// returns: battle_id, variant_id, member_id, pokemon_id, pokemon_name, level, member_slot, equipped_move_id, move_id, move_name, move_slot, observed_type_name
MATCH (:Trainer {id:$trainer_id})-[:HAS_BATTLE]->(b:BattleEncounter {battle_key:$battle_key})-[:IN_GAME_VERSION]->(:GameVersion {id:$version_id})
MATCH (b)-[:HAS_VARIANT]->(v:BattleVariant)-[:WHEN_PLAYER_CHOSE]->(:PokemonSpecies {id:$starter_species_id})
MATCH (v)-[:HAS_MEMBER]->(p:TrainerPokemon)-[:INSTANCE_OF]->(canonical:Pokemon)
MATCH (p)-[m:KNOWS_MOVE]->(move:Move)
RETURN b.id AS battle_id,v.id AS variant_id,p.id AS member_id,
       canonical.id AS pokemon_id,canonical.name AS pokemon_name,p.level AS level,
       p.slot AS member_slot,m.id AS equipped_move_id,move.id AS move_id,
       move.name AS move_name,m.slot AS move_slot,m.observed_type_name AS observed_type_name
ORDER BY member_slot,move_slot
SKIP $skip LIMIT $limit
