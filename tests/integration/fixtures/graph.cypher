MERGE (vg_ab:VersionGroup {id: -301}) SET vg_ab.name = 'fixture-group-ab'
MERGE (vg_other:VersionGroup {id: -302}) SET vg_other.name = 'fixture-group-other'
MERGE (v_a:GameVersion {id: -201}) SET v_a.name = 'fixture-version-a'
MERGE (v_b:GameVersion {id: -202}) SET v_b.name = 'fixture-version-b'
MERGE (v_other:GameVersion {id: -203}) SET v_other.name = 'fixture-version-other'
MERGE (v_a)-[:IN_VERSION_GROUP]->(vg_ab)
MERGE (v_b)-[:IN_VERSION_GROUP]->(vg_ab)
MERGE (v_other)-[:IN_VERSION_GROUP]->(vg_other)

MERGE (region:Region {id: -401}) SET region.name = 'fixture-region'
MERGE (location:Location {id: -501}) SET location.name = 'fixture-location'
MERGE (area:LocationArea {id: -601}) SET area.name = 'fixture-area'
MERGE (location)-[:IN_REGION]->(region)
MERGE (area)-[:PART_OF_LOCATION]->(location)
MERGE (vg_ab)-[:IN_REGION]->(region)

MERGE (t_electric:Type {id: -701}) SET t_electric.name = 'fixture-electric', t_electric.source_url = null, t_electric.source_version = null, t_electric.retrieved_at = null
MERGE (t_water:Type {id: -702}) SET t_water.name = 'fixture-water', t_water.source_url = null, t_water.source_version = null, t_water.retrieved_at = null
MERGE (t_flying:Type {id: -703}) SET t_flying.name = 'fixture-flying', t_flying.source_url = null, t_flying.source_version = null, t_flying.retrieved_at = null
MERGE (t_ground:Type {id: -704}) SET t_ground.name = 'fixture-ground', t_ground.source_url = null, t_ground.source_version = null, t_ground.retrieved_at = null
MERGE (t_unenriched:Type {id: -705}) SET t_unenriched.name = 'fixture-unenriched', t_unenriched.source_url = null, t_unenriched.source_version = null, t_unenriched.retrieved_at = null
MERGE (t_electric)-[:DAMAGE_TO {factor: 2.0}]->(t_water)
MERGE (t_electric)-[:DAMAGE_TO {factor: 2.0}]->(t_flying)
MERGE (t_electric)-[:DAMAGE_TO {factor: 0.0}]->(t_ground)
MERGE (t_ground)-[:DAMAGE_TO {factor: 2.0}]->(t_water)
MERGE (t_ground)-[:DAMAGE_TO {factor: 0.0}]->(t_flying)
MERGE (t_water)-[:DAMAGE_TO {factor: 0.5}]->(t_electric)

MERGE (m_tb:Move {id: -801}) SET m_tb.name = 'fixture-thunderbolt', m_tb.type = 'fixture-electric'
MERGE (m_surf:Move {id: -802}) SET m_surf.name = 'fixture-surf', m_surf.type = 'fixture-water'
MERGE (m_tb)-[:HAS_TYPE]->(t_electric)
MERGE (m_surf)-[:HAS_TYPE]->(t_water)

MERGE (em_walk:EncounterMethod {id: -901}) SET em_walk.name = 'fixture-walk'
MERGE (lm_level:MoveLearnMethod {id: -911}) SET lm_level.name = 'level-up'
MERGE (lm_machine:MoveLearnMethod {id: -912}) SET lm_machine.name = 'machine'

MERGE (s_shared:PokemonSpecies {id: -121}) SET s_shared.name = 'fixture-shared'
MERGE (s_only_a:PokemonSpecies {id: -122}) SET s_only_a.name = 'fixture-only-a'
MERGE (s_only_b:PokemonSpecies {id: -123}) SET s_only_b.name = 'fixture-only-b'
MERGE (s_dual:PokemonSpecies {id: -124}) SET s_dual.name = 'fixture-dual'
MERGE (s_attacker:PokemonSpecies {id: -125}) SET s_attacker.name = 'fixture-attacker'
MERGE (s_ground:PokemonSpecies {id: -126}) SET s_ground.name = 'fixture-ground-mon'
MERGE (s_branch:PokemonSpecies {id: -111}) SET s_branch.name = 'fixture-branch'
MERGE (s_water:PokemonSpecies {id: -112}) SET s_water.name = 'fixture-water-evo'
MERGE (s_thunder:PokemonSpecies {id: -113}) SET s_thunder.name = 'fixture-thunder-evo'

MERGE (p_shared:Pokemon {id: -101}) SET p_shared.name = 'fixture-shared'
MERGE (p_only_a:Pokemon {id: -102}) SET p_only_a.name = 'fixture-only-a'
MERGE (p_only_b:Pokemon {id: -103}) SET p_only_b.name = 'fixture-only-b'
MERGE (p_dual:Pokemon {id: -104}) SET p_dual.name = 'fixture-dual'
MERGE (p_attacker:Pokemon {id: -105}) SET p_attacker.name = 'fixture-attacker'
MERGE (p_ground:Pokemon {id: -106}) SET p_ground.name = 'fixture-ground-mon'
MERGE (p_shared)-[:SPECIES]->(s_shared)
MERGE (p_only_a)-[:SPECIES]->(s_only_a)
MERGE (p_only_b)-[:SPECIES]->(s_only_b)
MERGE (p_dual)-[:SPECIES]->(s_dual)
MERGE (p_attacker)-[:SPECIES]->(s_attacker)
MERGE (p_ground)-[:SPECIES]->(s_ground)
MERGE (p_dual)-[:HAS_TYPE {slot: 1}]->(t_water)
MERGE (p_dual)-[:HAS_TYPE {slot: 2}]->(t_flying)
MERGE (p_attacker)-[:HAS_TYPE {slot: 1}]->(t_electric)
MERGE (p_ground)-[:HAS_TYPE {slot: 1}]->(t_ground)
MERGE (p_shared)-[:HAS_TYPE {slot: 1}]->(t_electric)

MERGE (e_shared_a:Encounter {id: '-101:-601:-201:-901:15:25:30:'})
SET e_shared_a.min_level = 15, e_shared_a.max_level = 25, e_shared_a.chance = 30, e_shared_a.condition_values = [], e_shared_a.source_url = null, e_shared_a.source_version = null, e_shared_a.retrieved_at = null
MERGE (e_shared_b:Encounter {id: '-101:-601:-202:-901:15:25:30:'})
SET e_shared_b.min_level = 15, e_shared_b.max_level = 25, e_shared_b.chance = 30, e_shared_b.condition_values = [], e_shared_b.source_url = null, e_shared_b.source_version = null, e_shared_b.retrieved_at = null
MERGE (e_only_a:Encounter {id: '-102:-601:-201:-901:5:10:20:'})
SET e_only_a.min_level = 5, e_only_a.max_level = 10, e_only_a.chance = 20, e_only_a.condition_values = [], e_only_a.source_url = null, e_only_a.source_version = null, e_only_a.retrieved_at = null
MERGE (e_only_b:Encounter {id: '-103:-601:-202:-901:5:10:20:'})
SET e_only_b.min_level = 5, e_only_b.max_level = 10, e_only_b.chance = 20, e_only_b.condition_values = [], e_only_b.source_url = null, e_only_b.source_version = null, e_only_b.retrieved_at = null

MERGE (p_shared)-[:HAS_ENCOUNTER]->(e_shared_a)
MERGE (e_shared_a)-[:AT_LOCATION_AREA]->(area)
MERGE (e_shared_a)-[:IN_VERSION]->(v_a)
MERGE (e_shared_a)-[:USES_METHOD]->(em_walk)
MERGE (p_shared)-[:HAS_ENCOUNTER]->(e_shared_b)
MERGE (e_shared_b)-[:AT_LOCATION_AREA]->(area)
MERGE (e_shared_b)-[:IN_VERSION]->(v_b)
MERGE (e_shared_b)-[:USES_METHOD]->(em_walk)
MERGE (p_only_a)-[:HAS_ENCOUNTER]->(e_only_a)
MERGE (e_only_a)-[:AT_LOCATION_AREA]->(area)
MERGE (e_only_a)-[:IN_VERSION]->(v_a)
MERGE (e_only_a)-[:USES_METHOD]->(em_walk)
MERGE (p_only_b)-[:HAS_ENCOUNTER]->(e_only_b)
MERGE (e_only_b)-[:AT_LOCATION_AREA]->(area)
MERGE (e_only_b)-[:IN_VERSION]->(v_b)
MERGE (e_only_b)-[:USES_METHOD]->(em_walk)

MERGE (le_level:LearnsetEntry {id: '-101:-801:-301:-911:26:1'})
SET le_level.pokemon_id = -101,
    le_level.move_id = -801,
    le_level.version_group_id = -301,
    le_level.learn_method_id = -911,
    le_level.level_learned_at = 26,
    le_level.order = 1,
    le_level.source_url = 'https://pokeapi.co/api/v2/pokemon/-101/',
    le_level.source_version = null,
    le_level.retrieved_at = '2026-01-01T00:00:00+00:00'
MERGE (le_machine:LearnsetEntry {id: '-101:-801:-301:-912:0:'})
SET le_machine.pokemon_id = -101,
    le_machine.move_id = -801,
    le_machine.version_group_id = -301,
    le_machine.learn_method_id = -912,
    le_machine.level_learned_at = 0,
    le_machine.order = null,
    le_machine.source_url = 'https://pokeapi.co/api/v2/pokemon/-101/',
    le_machine.source_version = null,
    le_machine.retrieved_at = '2026-01-01T00:00:00+00:00'
MERGE (p_shared)-[:HAS_LEARNSET_ENTRY]->(le_level)
MERGE (le_level)-[:TEACHES]->(m_tb)
MERGE (le_level)-[:IN_VERSION_GROUP]->(vg_ab)
MERGE (le_level)-[:BY_LEARN_METHOD]->(lm_level)
MERGE (p_shared)-[:HAS_LEARNSET_ENTRY]->(le_machine)
MERGE (le_machine)-[:TEACHES]->(m_tb)
MERGE (le_machine)-[:IN_VERSION_GROUP]->(vg_ab)
MERGE (le_machine)-[:BY_LEARN_METHOD]->(lm_machine)

MERGE (chain:EvolutionChain {id: -1001})
MERGE (s_branch)-[:IN_EVOLUTION_CHAIN]->(chain)
MERGE (s_water)-[:IN_EVOLUTION_CHAIN]->(chain)
MERGE (s_thunder)-[:IN_EVOLUTION_CHAIN]->(chain)
MERGE (item_water:Item {id: -1101}) SET item_water.name = 'water-stone'
MERGE (item_thunder:Item {id: -1102}) SET item_thunder.name = 'thunder-stone'
MERGE (s_branch)-[evo_water:EVOLVES_TO {id: '-111:-112:use-item::water-stone::'}]->(s_water)
SET evo_water.trigger = 'use-item',
    evo_water.min_level = null,
    evo_water.min_happiness = null,
    evo_water.min_beauty = null,
    evo_water.min_affection = null,
    evo_water.time_of_day = null,
    evo_water.needs_overworld_rain = false,
    evo_water.turn_upside_down = false,
    evo_water.relative_physical_stats = null,
    evo_water.known_move = null,
    evo_water.known_move_type = null,
    evo_water.held_item = null,
    evo_water.location = null,
    evo_water.party_species = null,
    evo_water.trade_species = null,
    evo_water.gender = null,
    evo_water.version_group = null,
    evo_water.region = null,
    evo_water.is_default = true,
    evo_water.source_url = null,
    evo_water.source_version = null,
    evo_water.retrieved_at = null
MERGE (s_branch)-[evo_thunder:EVOLVES_TO {id: '-111:-113:use-item::thunder-stone::'}]->(s_thunder)
SET evo_thunder.trigger = 'use-item',
    evo_thunder.min_level = null,
    evo_thunder.min_happiness = null,
    evo_thunder.min_beauty = null,
    evo_thunder.min_affection = null,
    evo_thunder.time_of_day = null,
    evo_thunder.needs_overworld_rain = false,
    evo_thunder.turn_upside_down = false,
    evo_thunder.relative_physical_stats = null,
    evo_thunder.known_move = null,
    evo_thunder.known_move_type = null,
    evo_thunder.held_item = null,
    evo_thunder.location = null,
    evo_thunder.party_species = null,
    evo_thunder.trade_species = null,
    evo_thunder.gender = null,
    evo_thunder.version_group = null,
    evo_thunder.region = null,
    evo_thunder.is_default = true,
    evo_thunder.source_url = null,
    evo_thunder.source_version = null,
    evo_thunder.retrieved_at = null
MERGE (s_water)-[:REQUIRES_ITEM]->(item_water)
MERGE (s_thunder)-[:REQUIRES_ITEM]->(item_thunder)
