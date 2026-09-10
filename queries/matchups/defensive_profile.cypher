// query: defensive_profile
// answers: How does each stored Type hit this Pokémon, combining defender types and marking incomplete charts?
// does_not: Assert generation-specific charts, or predict battle outcomes.
// required: $pokemon_id (int)
// optional: $skip (int), $limit (int)
// returns: attacker_type_id, attacker_type_name, defender_pokemon_id, defender_pokemon_name, factor, effectiveness, data_complete
// order: attacker_type_id
// limit: coalesce($limit, 50)

MATCH (def:Pokemon {id: $pokemon_id})-[:HAS_TYPE]->(dt:Type)
WITH def, collect(dt) AS def_types
MATCH (atk:Type)
WITH def, def_types, atk, size([(atk)-[:DAMAGE_TO]->() | 1]) > 0 AS attacker_enriched
UNWIND def_types AS dt
OPTIONAL MATCH (atk)-[r:DAMAGE_TO]->(dt)
WITH def, atk, attacker_enriched,
     CASE
       WHEN r IS NOT NULL THEN r.factor
       WHEN attacker_enriched THEN 1.0
       ELSE null
     END AS type_factor
WITH def, atk, attacker_enriched, collect({factor: type_factor}) AS parts
WITH def, atk, attacker_enriched, parts,
     reduce(
       acc = 1.0,
       x IN parts |
         CASE WHEN acc IS NULL OR x.factor IS NULL THEN null ELSE acc * x.factor END
     ) AS factor,
     size(parts) > 0 AND all(x IN parts WHERE x.factor IS NOT NULL) AS types_complete
WITH def, atk, factor, attacker_enriched AND types_complete AS data_complete
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
       data_complete
ORDER BY attacker_type_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
