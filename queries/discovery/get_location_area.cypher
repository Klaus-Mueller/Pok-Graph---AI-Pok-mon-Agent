// query: get_location_area
// answers: Does this LocationArea id exist?
// does_not: List encounters in the area.
// required: $location_area_id (int)
// optional: (none)
// returns: location_area_id

MATCH (la:LocationArea {id: $location_area_id})
RETURN la.id AS location_area_id
