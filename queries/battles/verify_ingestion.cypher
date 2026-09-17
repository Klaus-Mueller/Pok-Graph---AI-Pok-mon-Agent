// Read-only checks scoped to the prepared battle IDs; existing PokéAPI Source data is unrelated.
MATCH (t:Trainer {id:'trainer:blue'})
RETURN 'Trainer' AS check, count(t) AS actual, 1 AS expected
UNION ALL
MATCH (b:BattleEncounter) WHERE b.id IN $battle_ids
RETURN 'BattleEncounter' AS check,count(b) AS actual,16 AS expected
UNION ALL
MATCH (b:BattleEncounter)-[:HAS_VARIANT]->(v:BattleVariant) WHERE b.id IN $battle_ids
RETURN 'BattleVariant' AS check,count(DISTINCT v) AS actual,48 AS expected
UNION ALL
MATCH (b:BattleEncounter)-[:HAS_VARIANT]->(:BattleVariant)-[:HAS_MEMBER]->(p:TrainerPokemon) WHERE b.id IN $battle_ids
RETURN 'TrainerPokemon' AS check,count(DISTINCT p) AS actual,198 AS expected
UNION ALL
MATCH (b:BattleEncounter)-[:HAS_VARIANT]->(:BattleVariant)-[:HAS_MEMBER]->(p:TrainerPokemon)-[r:KNOWS_MOVE]->(:Move) WHERE b.id IN $battle_ids
RETURN 'KNOWS_MOVE' AS check,count(DISTINCT r) AS actual,702 AS expected
UNION ALL
MATCH (n) WHERE n.id='trainer:blue' OR any(id IN $battle_ids WHERE n.id=id OR n.id STARTS WITH id+':')
MATCH (n)-[r:HAS_SOURCE|HAS_MOVE|USES_MOVE]->()
RETURN 'Legacy relationships' AS check,count(r) AS actual,0 AS expected
UNION ALL
MATCH (n:TrainerMove) WHERE any(id IN $battle_ids WHERE n.id STARTS WITH id+':')
RETURN 'Legacy TrainerMove nodes' AS check,count(n) AS actual,0 AS expected
UNION ALL
MATCH (n) WHERE n.id='trainer:blue' OR any(id IN $battle_ids WHERE n.id=id OR n.id STARTS WITH id+':')
WITH n WHERE any(k IN keys(n) WHERE k STARTS WITH 'source_' OR k STARTS WITH 'evidence' OR k IN ['attribution','license_url','retrieved_at'])
RETURN 'Source properties on battle nodes' AS check,count(n) AS actual,0 AS expected
UNION ALL
MATCH (b:BattleEncounter)-[:HAS_VARIANT]->(:BattleVariant)-[:HAS_MEMBER]->(p:TrainerPokemon)-[r:KNOWS_MOVE]->(m) WHERE b.id IN $battle_ids
WITH p,r,m WHERE NOT m:Move OR r.slot IS NULL OR NOT r.slot IN [1,2,3,4] OR r.id IS NULL OR r.id <> p.id+':move:'+toString(r.slot) OR any(k IN keys(r) WHERE NOT k IN ['id','slot','observed_type_name'])
RETURN 'Invalid equipped move properties' AS check,count(r) AS actual,0 AS expected
UNION ALL
MATCH (b:BattleEncounter)-[:HAS_VARIANT]->(:BattleVariant)-[:HAS_MEMBER]->(p:TrainerPokemon)-[r:KNOWS_MOVE]->(:Move) WHERE b.id IN $battle_ids
WITH p,r.slot AS slot,count(r) AS copies WHERE copies <> 1
RETURN 'Duplicate move slots' AS check,count(*) AS actual,0 AS expected
