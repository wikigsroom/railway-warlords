class_name MapCoastalControl
extends RefCounted

# Only actual source land within otherwise omitted coastal rule hexes. This
# cache contains no owners, dates, movement rules or invented political border.
const PATH="res://presentation/data/coastal_control_asia.json"
const SHA256="4c2ed2b82bddf1d8393b9deb7a074a6d4f59356d0d91d89468ec7d2517976803"
static var loaded: Dictionary={}

static func for_map(map: Dictionary) -> Dictionary:
	if str(map.get("id",""))!="asia_strategic":return {}
	if loaded.is_empty():
		if not FileAccess.file_exists(PATH) or FileAccess.get_sha256(PATH)!=SHA256:
			push_error("Source coastal control supplement checksum mismatch");return {}
		var data=JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if not data is Dictionary or data.get("format",0)!=1:return {}
		if data.get("map_sha256","")!=FileAccess.get_sha256("res://content/maps/asia_strategic.json") or float(data.hex_radius)!=HexGrid.RADIUS or float(data.get("field_radius",0))!=HexGrid.RADIUS:
			push_error("Source coastal control supplement is stale");return {}
		loaded=data
	return loaded

static func facts(data: Dictionary) -> Dictionary:
	if data.is_empty():return {"active":false}
	return {"active":true,"source":data.source,"data_sha256":SHA256,"map_sha256":data.map_sha256,
		"source_cells":data.supplement_cells,"source_land_triangles":data.source_land_triangles,
		"field_radius":data.field_radius,"rules_changed":false,"historical_military_frontiers_claimed":false}
