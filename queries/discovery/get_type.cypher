// query: get_type
// answers: Does this Type id exist?
// does_not: Compute effectiveness.
// required: $type_id (int)
// optional: (none)
// returns: type_id

MATCH (t:Type {id: $type_id})
RETURN t.id AS type_id
