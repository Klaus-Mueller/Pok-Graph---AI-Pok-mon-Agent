// query: regional_candidates_for_battle
// answers: Which explicitly allowed location encounter candidates have hypothetical type advantages against this team?
// does_not: Check moves, progression, damage, victory, or historical type-chart accuracy.
// required: $accessible_location_names (list[str]), $trainer_id (str), $version_id (int), $battle_key (str), $starter_species_id (int)
// optional: $skip (int), $limit (int)
// returns: battle_id, variant_id, region_name, pokemon_id, pokemon_name, locations, members_covered, team_size, matchups, data_complete, availability_scope, progression_checked, moves_checked, mechanics_basis
MATCH (:Trainer {id:$trainer_id})-[:HAS_BATTLE]->(b:BattleEncounter {battle_key:$battle_key})-[:IN_GAME_VERSION]->(:GameVersion {id:$version_id})
MATCH (b)-[:AT_LOCATION]->(:Location)-[:IN_REGION]->(region:Region)
MATCH (b)-[:HAS_VARIANT]->(v:BattleVariant)-[:WHEN_PLAYER_CHOSE]->(:PokemonSpecies {id:$starter_species_id})
MATCH (v)-[:HAS_MEMBER]->(member:TrainerPokemon)
WITH b,v,region,collect(DISTINCT member) AS team
MATCH (p:Pokemon)-[:HAS_ENCOUNTER]->(e:Encounter)-[:IN_VERSION]->(:GameVersion {id:$version_id})
MATCH (e)-[:AT_LOCATION_AREA]->(:LocationArea)-[:PART_OF_LOCATION]->(l:Location)-[:IN_REGION]->(region)
WHERE l.name IN $accessible_location_names
WITH DISTINCT b,v,region,team,p,l
ORDER BY l.id
WITH b,v,region,team,p,collect({id:l.id,name:l.name}) AS locations
UNWIND team AS member
MATCH (member)-[:INSTANCE_OF]->(def:Pokemon)
OPTIONAL MATCH (p)-[:HAS_TYPE]->(atk:Type)
WITH b,v,region,team,p,locations,member,def,atk,
     CASE WHEN size(coalesce(member.observed_type_names,[])) > 0
          THEN member.observed_type_names ELSE [null] END AS defender_types
UNWIND defender_types AS type_name
OPTIONAL MATCH (dt:Type {name:toLower(type_name)})
OPTIONAL MATCH (atk)-[damage:DAMAGE_TO]->(dt)
WITH b,v,region,team,p,locations,member,def,atk,
     CASE WHEN atk IS NULL OR dt IS NULL THEN null
          WHEN damage IS NOT NULL THEN damage.factor
          WHEN EXISTS { MATCH (atk)-[:DAMAGE_TO]->() } THEN 1.0
          ELSE null END AS part
WITH b,v,region,team,p,locations,member,def,atk,collect({factor:part}) AS parts
WITH b,v,region,team,p,locations,member,def,atk,
     reduce(f=1.0, x IN parts | CASE WHEN f IS NULL OR x.factor IS NULL THEN null ELSE f*x.factor END) AS factor
ORDER BY member.slot,atk.id
WITH b,v,region,team,p,locations,member,def,
     collect({attacking_type:atk.name,factor:factor}) AS type_options
WITH b,v,region,team,p,locations,member,
     {member_id:member.id,pokemon_id:def.id,pokemon_name:def.name,slot:member.slot,
      level:member.level,defender_types:member.observed_type_names,type_options:type_options,
      advantage:any(x IN type_options WHERE coalesce(x.factor > 1.0,false)),
      data_complete:all(x IN type_options WHERE x.factor IS NOT NULL)} AS matchup
ORDER BY member.slot
WITH b,v,region,team,p,locations,collect(matchup) AS matchups
RETURN b.id AS battle_id,v.id AS variant_id,region.name AS region_name,
       p.id AS pokemon_id,p.name AS pokemon_name,locations,
       size([m IN matchups WHERE m.advantage]) AS members_covered,size(team) AS team_size,
       matchups,all(m IN matchups WHERE m.data_complete) AS data_complete,
       'explicit_locations' AS availability_scope,false AS progression_checked,false AS moves_checked,
       'stored_chart_and_candidate_types_not_generation_verified' AS mechanics_basis
ORDER BY members_covered DESC,pokemon_id
SKIP coalesce($skip,0) LIMIT coalesce($limit,50)
