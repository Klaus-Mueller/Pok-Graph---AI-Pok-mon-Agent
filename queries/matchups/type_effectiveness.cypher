// query: type_effectiveness
// answers: What combined DAMAGE_TO factor does this attacking Type have against this Pokémon's types?
// does_not: Assert generation-specific charts, or treat a missing edge as neutral unless the attacker is enriched.
// required: $attacker_type_id (int), $defender_pokemon_id (int)
// optional: (none)
// returns: attacker_type_id, attacker_type_name, defender_pokemon_id, defender_pokemon_name, factor, effectiveness, data_complete, source_url, source_version, retrieved_at
// order: attacker_type_id, defender_pokemon_id
// limit: 1 row

MATCH (atk:Type {id: $attacker_type_id})
MATCH (def:Pokemon {id: $defender_pokemon_id})-[:HAS_TYPE]->(dt:Type)
WITH atk, def, dt, size([(atk)-[:DAMAGE_TO]->() | 1]) > 0 AS attacker_enriched
OPTIONAL MATCH (atk)-[r:DAMAGE_TO]->(dt)
WITH atk, def, attacker_enriched,
     CASE
       WHEN r IS NOT NULL THEN r.factor
       WHEN attacker_enriched THEN 1.0
       ELSE null
     END AS type_factor
WITH atk, def, attacker_enriched, collect({factor: type_factor}) AS parts
WITH atk, def, attacker_enriched, parts,
     reduce(
       acc = 1.0,
       x IN parts |
         CASE WHEN acc IS NULL OR x.factor IS NULL THEN null ELSE acc * x.factor END
     ) AS factor,
     size(parts) > 0 AND all(x IN parts WHERE x.factor IS NOT NULL) AS types_complete
WITH atk, def, factor, attacker_enriched AND types_complete AS data_complete
RETURN atk.id AS attacker_type_id,
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
       data_complete,
       atk.source_url AS source_url,
       atk.source_version AS source_version,
       atk.retrieved_at AS retrieved_at
ORDER BY attacker_type_id, defender_pokemon_id
