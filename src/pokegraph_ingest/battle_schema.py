"""Battle constraints shared by schema setup and the separate battle writer."""

BATTLE_CONSTRAINTS = tuple(
    f'CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE'
    for name, label in (
        ('trainer_id', 'Trainer'), ('battle_encounter_id', 'BattleEncounter'),
        ('battle_variant_id', 'BattleVariant'), ('trainer_pokemon_id', 'TrainerPokemon'),
    )
)
