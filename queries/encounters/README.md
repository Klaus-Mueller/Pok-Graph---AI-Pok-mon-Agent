# Encounters

Recorded encounter rows for a `GameVersion`. Every result includes `encounter_id`.

Absence of a row is missing evidence, not proof the Pokémon cannot be obtained.

Level filters overlap intervals: searching 10–20 includes an encounter at 15–25.

| File | Question |
| --- | --- |
| [`pokemon_in_area.cypher`](pokemon_in_area.cypher) | Which Pokémon have encounters in this area and game? |
| [`locations_of_pokemon.cypher`](locations_of_pokemon.cypher) | Where does this Pokémon have recorded encounters in this game? |
| [`compare_versions.cypher`](compare_versions.cypher) | Which Pokémon appear in both games, only A, or only B? |
