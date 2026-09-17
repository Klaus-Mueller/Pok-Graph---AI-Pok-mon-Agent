# Battle model — revised implementation contract

This supersedes the original TrainerMove/Source battle model. See README.md for
commands and validation.md for verification results.

- Trainer (1) owns BattleEncounter (16), one record per battle and game version.
- BattleEncounter owns three BattleVariant (48 total), selected by the player's
  original starter species through WHEN_PLAYER_CHOSE.
- BattleVariant owns 1..6 TrainerPokemon (198 total) through HAS_MEMBER.
- TrainerPokemon links to exactly one existing Pokemon through INSTANCE_OF and
  carries slot, level and observed_type_names.
- TrainerPokemon links directly to existing Move via 1..4 KNOWS_MOVE relationships
  (702 total). Each carries id, slot and observed_type_name. No intermediate node.
- BattleEncounter links to one GameVersion and zero or one resolved Location.
  GameVersion's existing IN_VERSION_GROUP relationship supplies group context.
- No Source node, HAS_SOURCE relationship or source/evidence property is emitted
  by the battle writer. Offline source documentation remains outside the graph.

Stable keys are trainer:blue; battle:blue:{version_id}:{battle_key};
{battle_id}:starter:{species_id}; {variant_id}:member:{slot}; and, for the direct
move relationship, {member_id}:move:{slot}. Node uniqueness constraints cover only
Trainer, BattleEncounter, BattleVariant and TrainerPokemon. Relationship slot/ID
consistency is checked by validation, preflight and server verification.

The normalizer parses the 24 existing party chunks, resolves canonical references,
and expands them into 16 versioned records. The writer checks canonical nodes and
existing structure before mutation, then writes one battle per transaction.
Canonical nodes and their type/learnset properties are reused without modification.
Existing old-model battle records require explicit reconciliation; there is no
automatic global deletion of TrainerMove or Source nodes/constraints.

Acceptance: 263 battle nodes, 702 equipped-move relationships, no source data in
the battle payload, identical-load idempotence, valid team queries, rollback on
failed battle transactions, and explicit unknown locations/progression.
