// query: dataset_fingerprint
// answers: What node counts and latest LearnsetEntry.retrieved_at describe this graph snapshot?
// does_not: Version the dataset formally; there is no stored manifest. Use this as an example fingerprint only.
// required: (none)
// optional: (none)
// returns: pokemon_count, encounter_count, learnset_entry_count, game_version_count, version_group_count, latest_learnset_retrieved_at
// order: single row
// limit: 1

CALL () { MATCH (n:Pokemon) RETURN count(n) AS pokemon_count }
CALL () { MATCH (n:Encounter) RETURN count(n) AS encounter_count }
CALL () { MATCH (n:LearnsetEntry) RETURN count(n) AS learnset_entry_count, max(n.retrieved_at) AS latest_learnset_retrieved_at }
CALL () { MATCH (n:GameVersion) RETURN count(n) AS game_version_count }
CALL () { MATCH (n:VersionGroup) RETURN count(n) AS version_group_count }
RETURN pokemon_count,
       encounter_count,
       learnset_entry_count,
       game_version_count,
       version_group_count,
       latest_learnset_retrieved_at
