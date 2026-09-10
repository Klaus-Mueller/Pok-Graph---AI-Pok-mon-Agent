// query: offensive_coverage_by_learnset
// answers: How do this Pokémon's VersionGroup learnset moves hit the defender, by move type and learn method?
// does_not: Predict a win, treat level_learned_at = 0 as early access, or assert generation-specific charts. Advantage means factor > 1.
// required: $pokemon_id (int), $version_group_id (int), $defender_pokemon_id (int)
// optional: $learn_method_id (int), $skip (int), $limit (int)
// returns: learnset_entry_id, pokemon_id, pokemon_name, move_id, move_name, learn_method_id, learn_method_name, level_learned_at, attacker_type_id, attacker_type_name, defender_pokemon_id, defender_pokemon_name, factor, effectiveness, advantage, data_complete
// order: learn_method_id, level_learned_at, move_id, learnset_entry_id
// limit: coalesce($limit, 50)

MATCH (p:Pokemon {id: $pokemon_id})-[:HAS_LEARNSET_ENTRY]->(e:LearnsetEntry)
MATCH (e)-[:IN_VERSION_GROUP]->(:VersionGroup {id: $version_group_id})
MATCH (e)-[:TEACHES]->(m:Move)
MATCH (e)-[:BY_LEARN_METHOD]->(lm:MoveLearnMethod)
WHERE $learn_method_id IS NULL OR lm.id = $learn_method_id
OPTIONAL MATCH (m)-[:HAS_TYPE]->(atkFromRel:Type)
OPTIONAL MATCH (atkFromName:Type {name: m.type})
WITH p, e, m, lm, coalesce(atkFromRel, atkFromName) AS atk
MATCH (def:Pokemon {id: $defender_pokemon_id})-[:HAS_TYPE]->(dt:Type)
WITH p, e, m, lm, atk, def, dt,
     atk IS NOT NULL AND size([(atk)-[:DAMAGE_TO]->() | 1]) > 0 AS attacker_enriched
OPTIONAL MATCH (atk)-[r:DAMAGE_TO]->(dt)
WITH p, e, m, lm, atk, def, attacker_enriched,
     CASE
       WHEN atk IS NULL THEN null
       WHEN r IS NOT NULL THEN r.factor
       WHEN attacker_enriched THEN 1.0
       ELSE null
     END AS type_factor
WITH p, e, m, lm, atk, def, attacker_enriched, collect({factor: type_factor}) AS parts
WITH p, e, m, lm, atk, def, attacker_enriched, parts,
     reduce(
       acc = 1.0,
       x IN parts |
         CASE WHEN acc IS NULL OR x.factor IS NULL THEN null ELSE acc * x.factor END
     ) AS factor,
     size(parts) > 0 AND all(x IN parts WHERE x.factor IS NOT NULL) AS types_complete
WITH p, e, m, lm, atk, def, factor, attacker_enriched AND types_complete AS data_complete
RETURN e.id AS learnset_entry_id,
       p.id AS pokemon_id,
       p.name AS pokemon_name,
       m.id AS move_id,
       m.name AS move_name,
       lm.id AS learn_method_id,
       lm.name AS learn_method_name,
       e.level_learned_at AS level_learned_at,
       atk.id AS attacker_type_id,
       atk.name AS attacker_type_name,
       def.id AS defender_pokemon_id,
       def.name AS defender_pokemon_name,
       factor,
       CASE
         WHEN factor IS NULL THEN 'unknown'
         WHEN factor = 0.0 THEN 'immune'
         WHEN factor < 1.0 THEN 'resist'
         WHEN factor = 1.0 THEN 'neutral'
         ELSE 'weak'
       END AS effectiveness,
       CASE WHEN factor IS NOT NULL AND factor > 1.0 THEN true ELSE false END AS advantage,
       data_complete
ORDER BY learn_method_id, level_learned_at, move_id, learnset_entry_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
