class_name MapControlLandClip
extends RefCounted

# Source-bound presentation vectors. Owners and all rule geometry stay outside
# this cache. Missing/stale data omits the wash instead of painting over water.
const PATH="res://presentation/data/control_land_clip.json"
static var catalog: Dictionary={}
static var validated: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists(PATH):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func for_map(map: Dictionary) -> Dictionary:
	var id=str(map.get("id",""))
	var row: Dictionary=data().get("maps",{}).get(id,{})
	if row.is_empty():return {}
	if not validated.has(id):
		validated[id]=FileAccess.get_sha256("res://content/maps/"+id+".json")==row.get("map_sha256","") and float(row.get("hex_radius",0))==HexGrid.RADIUS
		if not validated[id]:push_error("Source land clipping data is stale: "+id)
	return row if validated[id] else {}

static func vertices(record: Dictionary) -> PackedVector3Array:
	if not record.has("packed_vertices"):
		var packed=PackedVector3Array()
		for point in record.get("triangles",[]):packed.append(Vector3(point[0],point[1],0))
		record["packed_vertices"]=packed
	return record.packed_vertices

static func city_zones(row: Dictionary) -> Array:
	var result: Array=[]
	for record in row.get("city_zones",[]):
		var packed=vertices(record)
		if packed.is_empty():continue
		if not record.has("mesh_cache"):
			var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=packed
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			record["mesh_cache"]=mesh
		var bounds: Array=record.bounds
		var borders: Array=[]
		for raw in record.borders:
			var points=PackedVector2Array()
			for xy in raw:points.append(Vector2(xy[0],xy[1]))
			borders.append(points)
		result.append({"city_id":record.city_id,"province":record.province,"mesh":record.mesh_cache,"borders":borders,
			"bounds":Rect2(Vector2(bounds[0],bounds[1]),Vector2(bounds[2]-bounds[0],bounds[3]-bounds[1])),"land_clipped":true})
	return result

static func inland_water_mesh(row: Dictionary, period: float) -> ArrayMesh:
	var record: Dictionary=row.get("inland_water",{})
	var packed=vertices(record)
	if packed.is_empty():return null
	if not record.has("mesh_cache") or float(record.get("uv_period",0))!=period:
		var uv=PackedVector2Array()
		for point in packed:uv.append(Vector2(point.x,point.y)/period)
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=packed;arrays[Mesh.ARRAY_TEX_UV]=uv
		var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		record["mesh_cache"]=mesh;record["uv_period"]=period
	return record.mesh_cache

static func diagnostics(row: Dictionary) -> Dictionary:
	if row.is_empty():return {"enabled":false,"land_clipped":false}
	return {"enabled":true,"land_clipped":true,"source":"existing_render_land_exteriors_minus_holes",
		"source_map_sha256":row.map_sha256,"source_land_polygons":row.source_land_polygons,"source_land_holes":row.source_land_holes,
		"eligible_field_cells":row.eligible_field_cells,"partial_field_cells":row.partial_field_cells,"empty_field_cells":row.empty_field_cells,
		"city_zones":row.city_zones.size(),"clipped_city_zones":row.clipped_city_zones,"inland_water_preserves_source_islands":true,"historical_military_frontiers_claimed":false}
