// query: get_species
// answers: Does this PokemonSpecies id exist?
// does_not: Describe the species or its evolutions.
// required: $species_id (int)
// optional: (none)
// returns: species_id

MATCH (s:PokemonSpecies {id: $species_id})
RETURN s.id AS species_id
