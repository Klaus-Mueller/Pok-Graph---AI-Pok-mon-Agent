// query: get_move
// answers: Does this Move id exist?
// does_not: Say who learns the move.
// required: $move_id (int)
// optional: (none)
// returns: move_id

MATCH (m:Move {id: $move_id})
RETURN m.id AS move_id
