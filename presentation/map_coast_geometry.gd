class_name MapCoastGeometry
extends RefCounted

# One-map cache: the phone never retains every continental/coastal mesh.
# Source geometry is compiled offline; the game does not ear-clip a 100k-point
# mainland polygon when opening the atlas. Rules keep their existing hex grid.
const PATH="res://presentation/data/coast_geometry.json"
static var catalog: Dictionary={}
static var loaded_id=""
static var loaded: Dictionary={}
static var validated: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists(PATH):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func for_map(map: Dictionary, source_id: String="") -> Dictionary:
	var id=str(map.get("id","")) if source_id.is_empty() else source_id
	var entry: Dictionary=data().get("maps",{}).get(id,{})
	if entry.is_empty():return {}
	# Explicit opt-in for a copy of the production map used by capacity QA.
	if str(map.get("id",""))!=id and map.get("fixture_source",{}).get("production_map_sha256","")!=entry.get("map_sha256",""):return {}
	if map.get("physical_detail_source","")!=data().get("source_id",""):return {}
	if loaded_id==id:return loaded
	var path="res://"+str(entry.get("file",""))
	if not validated.has(id):
		validated[id]=FileAccess.file_exists(path) and FileAccess.get_sha256(path)==entry.get("data_sha256","") and FileAccess.get_sha256("res://content/maps/"+id+".json")==entry.get("map_sha256","") and float(entry.get("hex_radius",0))==HexGrid.RADIUS
	if not validated[id]:
		push_error("Source marine geometry is stale: "+id)
		return {}
	var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:return {}
	if parsed.get("settlement_source_sha256","")!=FileAccess.get_sha256("res://presentation/data/settlements_v023.json"):
		push_error("Source marine control clipping is stale: "+id)
		return {}
	loaded_id=id;loaded=parsed
	return loaded

static func land(row: Dictionary, texture_scale: float) -> Dictionary:
	if row.is_empty():return {}
	if not row.has("_land") or row.get("_land_texture_scale",0)!=texture_scale:
		row["_land"]=AtlasSurface.build_indexed(row.get("vertices",[]),row.get("indices",[]),texture_scale)
		row["_land_texture_scale"]=texture_scale
	var result: Dictionary=row._land
	return {"mesh":result.mesh,"rings":int(row.get("source_land_polygons",0)),"triangles":result.triangles,"errors":result.errors}

static func diagnostics(row: Dictionary) -> Dictionary:
	if row.is_empty():return {"active":false}
	return {"active":true,"source":"gshhg_2_3_7_L1","pretriangulated":true,
		"land_polygons":int(row.get("source_land_polygons",0)),"coast_vertices":int(row.get("coast_vertices",0)),
		"land_triangles":int(row.get("triangles",0)),"existing_inland_water_preserved":true,
		"new_l2_reservoirs_imported":false,"historical_survey_claimed":false,"cache_scope":"one_map"}

static func land_queries(row: Dictionary) -> Dictionary:
	if row.is_empty():return {}
	if row.has("_land_queries"):return row._land_queries
	var vertices=PackedVector2Array()
	for point in row.get("vertices",[]):vertices.append(Vector2(point[0],point[1]))
	var indices=PackedInt32Array(row.get("indices",[]));var buckets: Dictionary={}
	for offset in range(0,indices.size(),3):
		var a=vertices[indices[offset]];var b=vertices[indices[offset+1]];var c=vertices[indices[offset+2]]
		if (float(b.x)-a.x)*(float(c.y)-a.y)-(float(b.y)-a.y)*(float(c.x)-a.x)==0:continue
		var bounds=Rect2(a,Vector2.ZERO).expand(b).expand(c)
		for x in range(floori(bounds.position.x/512),floori(bounds.end.x/512)+1):
			for y in range(floori(bounds.position.y/512),floori(bounds.end.y/512)+1):
				var key=Vector2i(x,y)
				if not buckets.has(key):buckets[key]=[]
				buckets[key].append(offset)
	row["_land_queries"]={"vertices":vertices,"indices":indices,"buckets":buckets}
	return row._land_queries

static func query_land(index: Dictionary, point: Vector2) -> bool:
	var key=Vector2i(floori(point.x/512),floori(point.y/512))
	for offset in index.buckets.get(key,[]):
		var a: Vector2=index.vertices[index.indices[offset]]
		var b: Vector2=index.vertices[index.indices[offset+1]]
		var c: Vector2=index.vertices[index.indices[offset+2]]
		# Use scalar double arithmetic on the actual float mesh coordinates.
		# This avoids long-ray intersection cancellation on a 50k-point mainland.
		var ab=(float(b.x)-a.x)*(float(point.y)-a.y)-(float(b.y)-a.y)*(float(point.x)-a.x)
		var bc=(float(c.x)-b.x)*(float(point.y)-b.y)-(float(c.y)-b.y)*(float(point.x)-b.x)
		var ca=(float(a.x)-c.x)*(float(point.y)-c.y)-(float(a.y)-c.y)*(float(point.x)-c.x)
		if (ab>=0 and bc>=0 and ca>=0) or (ab<=0 and bc<=0 and ca<=0):return true
	return false
