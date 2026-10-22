class_name HarborRules
extends RefCounted

# A fine tactical map can distinguish the city centre from its river approach.
# Older maps retain their original adjacent-city harbor behaviour.
static func land_hex(city: Dictionary) -> Vector2i:
	return HexGrid.coordinate(city.get("harbor_position",city.position))

static func water_position(city: Dictionary) -> Dictionary:
	return city.get("harbor_water_position",city.get("harbor_position",city.position))

static func controlled_port(state: Dictionary, hex: Vector2i, owner: String) -> Dictionary:
	var nearest: Dictionary={};var distance=2
	for city in state.cities:
		if city.owner_id!=owner or not city.get("port",false) or city.get("blockaded",false):continue
		var candidate=HexGrid.distance(hex,land_hex(city))
		if candidate<distance:
			distance=candidate;nearest=city
	return nearest
