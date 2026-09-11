// query: get_pokemon
// answers: Does this Pokemon id exist?
// does_not: Describe the Pokémon or its encounters.
// required: $pokemon_id (int)
// optional: (none)
// returns: pokemon_id

MATCH (p:Pokemon {id: $pokemon_id})
RETURN p.id AS pokemon_id
