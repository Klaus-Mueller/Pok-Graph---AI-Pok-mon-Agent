// query: offensive_coverage_by_types
// answers: How do this Pokémon's types hit the defender (combined factors, including immunities)?
// does_not: Predict a win, or assert generation-specific charts. Advantage means factor > 1.
// required: $pokemon_id (int), $defender_pokemon_id (int)
// optional: $skip (int), $limit (int)
// returns: pokemon_id, pokemon_name, attacker_type_id, attacker_type_name, defender_pokemon_id, defender_pokemon_name, factor, effectiveness, advantage, data_complete
// order: attacker_type_id
// limit: coalesce($limit, 50)

MATCH (atk_p:Pokemon {id: $pokemon_id})-[:HAS_TYPE]->(atk:Type)
MATCH (def:Pokemon {id: $defender_pokemon_id})-[:HAS_TYPE]->(dt:Type)
WITH atk_p, atk, def, dt, size([(atk)-[:DAMAGE_TO]->() | 1]) > 0 AS attacker_enriched
OPTIONAL MATCH (atk)-[r:DAMAGE_TO]->(dt)
WITH atk_p, atk, def, attacker_enriched,
     CASE
       WHEN r IS NOT NULL THEN r.factor
       WHEN attacker_enriched THEN 1.0
       ELSE null
     END AS type_factor
WITH atk_p, atk, def, attacker_enriched, collect({factor: type_factor}) AS parts
WITH atk_p, atk, def, attacker_enriched, parts,
     reduce(
       acc = 1.0,
       x IN parts |
         CASE WHEN acc IS NULL OR x.factor IS NULL THEN null ELSE acc * x.factor END
     ) AS factor,
     size(parts) > 0 AND all(x IN parts WHERE x.factor IS NOT NULL) AS types_complete
WITH atk_p, atk, def, factor, attacker_enriched AND types_complete AS data_complete
RETURN atk_p.id AS pokemon_id,
       atk_p.name AS pokemon_name,
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
ORDER BY attacker_type_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
