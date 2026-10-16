class_name MapTerrainSurfaces
extends RefCounted

# Twenty grounded presentation subtypes, separate from the twelve authoritative
# movement/cover terrains. Ecological zones never create historical tree cover.
static var catalog: Dictionary={}
static var regions: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists("res://presentation/data/terrain_surface_catalog.json"):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/terrain_surface_catalog.json"))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func geography() -> Dictionary:
	if regions.is_empty() and FileAccess.file_exists("res://presentation/data/terrain_surface_regions.json"):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/terrain_surface_regions.json"))
		if parsed is Dictionary:regions=parsed
	return regions

static func available() -> bool:
	return data().get("types",{}).size()==20 and data().get("records",{}).size()==80

static func ids(family: String) -> Array:
	return data().get("types",{}).get(family,{}).get("assets",[])

static func apply(cells: Dictionary, map_id: String) -> Dictionary:
	var counts: Dictionary={};var assigned=0
	if not available():return {"active":false}
	var rows: Dictionary=geography().get("maps",{}).get(map_id,{})
	for hex in cells:
		var cell: Dictionary=cells[hex];var row=rows.get(str(cell.get("id","")),[])
		if row.size()!=3 or not data().types.has(str(row[0])):continue
		if TerrainVisuals.kind_for_cell(cell) in ["sea","river","road","city","port","ford"]:continue
		cell["presentation_terrain_surface"]=str(row[0])
		cell["presentation_terrain_ecoregion"]=int(row[1])
		cell["presentation_terrain_source_gate"]=str(row[2])
		counts[row[0]]=int(counts.get(row[0],0))+1;assigned+=1
	return {"active":true,"registered_types":20,"independent_originals":80,"assignments":assigned,"types":counts,"source_year":2017,"source_scope":"regional_ground_reference_plus_archived_dem","historical_landuse_survey":false,"rule_maps_modified":false,"water_or_forest_added":false}

static func family_for(cell: Dictionary) -> String:
	var family=str(cell.get("presentation_terrain_surface",""))
	if TerrainVisuals.kind_for_cell(cell) in ["sea","river","road","city","port","ford"]:return ""
	return family if data().get("types",{}).has(family) else ""

static func label_for(cell: Dictionary) -> String:
	return str(data().get("types",{}).get(family_for(cell),{}).get("name",""))

static func variant_for(family: String, hex: Vector2i) -> String:
	var pool=ids(family)
	if pool.size()!=4:return ""
	# Axial q-r modulo three is a proper colouring of the six-neighbour hex
	# lattice: adjacent cells cannot use the same immutable original. The fourth
	# independently generated texture replaces only colour zero in broad stable
	# patches; it cannot collide with the other two colour classes. No gameplay
	# random stream, camera position or occupying faction enters the selection.
	var phase=posmod(hex.x-hex.y,3)
	if phase==0 and absi(hash("surface:"+family+":"+str(Vector2i(floori(hex.x/5.0),floori(hex.y/5.0)))))%2==1:phase=3
	return str(pool[phase])

static func alpha_for(family: String, strategic: bool) -> float:
	if not data().get("types",{}).has(family):return -1.0
	# Keep the natural material visible beneath the separate .21/.26 political
	# wash. This affects the ground texture, never territorial opacity.
	return .94 if not strategic else .91
