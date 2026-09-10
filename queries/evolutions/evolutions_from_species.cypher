// query: evolutions_from_species
// answers: Which EVOLVES_TO conditions start from this PokemonSpecies?
// does_not: Claim the evolution is available in a given game unless version_group is present; do not collapse alternatives.
// required: $species_id (int)
// optional: $skip (int), $limit (int)
// returns: evolves_to_id, from_species_id, from_species_name, to_species_id, to_species_name, trigger, min_level, min_happiness, min_beauty, min_affection, time_of_day, needs_overworld_rain, turn_upside_down, relative_physical_stats, known_move, known_move_type, held_item, location, party_species, trade_species, gender, version_group, region, is_default, item_id, item_name
// order: to_species_id, evolves_to_id
// limit: coalesce($limit, 50)

MATCH (from:PokemonSpecies {id: $species_id})-[rel:EVOLVES_TO]->(to:PokemonSpecies)
OPTIONAL MATCH (to)-[:REQUIRES_ITEM]->(i:Item)
WITH rel, from, to, collect(i)[0] AS i
RETURN rel.id AS evolves_to_id,
       from.id AS from_species_id,
       from.name AS from_species_name,
       to.id AS to_species_id,
       to.name AS to_species_name,
       rel.trigger AS trigger,
       rel.min_level AS min_level,
       rel.min_happiness AS min_happiness,
       rel.min_beauty AS min_beauty,
       rel.min_affection AS min_affection,
       rel.time_of_day AS time_of_day,
       rel.needs_overworld_rain AS needs_overworld_rain,
       rel.turn_upside_down AS turn_upside_down,
       rel.relative_physical_stats AS relative_physical_stats,
       rel.known_move AS known_move,
       rel.known_move_type AS known_move_type,
       rel.held_item AS held_item,
       rel.location AS location,
       rel.party_species AS party_species,
       rel.trade_species AS trade_species,
       rel.gender AS gender,
       rel.version_group AS version_group,
       rel.region AS region,
       rel.is_default AS is_default,
       i.id AS item_id,
       i.name AS item_name
ORDER BY to_species_id, evolves_to_id
SKIP coalesce($skip, 0)
LIMIT coalesce($limit, 50)
