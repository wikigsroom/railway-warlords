class_name MapGroundCoverage
extends RefCounted

# Numerical geometry only. Each map is loaded independently; this cache never
# retains all six coast meshes on a phone, and never changes a rule cell.
const PATH="res://presentation/data/ground_coverage.json"
static var catalog: Dictionary={}
static var loaded_id=""
static var loaded: Dictionary={}
static var validated: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists(PATH):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func for_map(map: Dictionary) -> Dictionary:
	var id=str(map.get("id",""))
	var entry: Dictionary=data().get("maps",{}).get(id,{})
	if entry.is_empty():return {}
	if loaded_id==id:return loaded
	var path="res://"+str(entry.get("file",""))
	if not validated.has(id):
		validated[id]=FileAccess.file_exists(path) and FileAccess.get_sha256(path)==entry.get("data_sha256","") and FileAccess.get_sha256("res://content/maps/"+id+".json")==entry.get("map_sha256","") and FileAccess.get_sha256("res://presentation/data/terrain_surface_regions.json")==data().get("source_geography_sha256","") and float(entry.get("hex_radius",0))==HexGrid.RADIUS
	if not validated[id]:
		push_error("Source ground coverage is stale: "+id)
		return {}
	var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:return {}
	loaded_id=id;loaded=parsed
	return loaded

static func diagnostics(row: Dictionary) -> Dictionary:
	if row.is_empty():return {"active":false}
	return {"active":true,"covered_cells":int(row.get("covered_cells",0)),"partial_cells":int(row.get("partial_cells",0)),"unclassified_cells":int(row.get("unclassified_cells",0)),"supplemental_underlays":row.get("supplements",{}).size(),"source_land_clipped":true,"rule_cells_modified":false,"new_rasters":0,"historical_landuse_claimed":false,"cache_scope":"one_map_catalogue"}
