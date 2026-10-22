class_name HistoricalPlaces
extends RefCounted

# This catalog is presentation data. It never appends cities, changes income,
# expands visibility, or mutates the saved rules state.
static var catalog: Dictionary={}
var nodes: Array=[]
var index: Dictionary={}
var zones: Array=[]
var owners: Dictionary={}
var owner_signature=""
var map_key=""
var control_clip_diagnostics: Dictionary={}
var control_borders = preload("res://presentation/map_control_borders.gd").new()

static func data() -> Dictionary:
	if catalog.is_empty():
		var file=FileAccess.open("res://presentation/data/settlements_v023.json",FileAccess.READ)
		if file!=null:catalog=JSON.parse_string(file.get_as_text())
	return catalog

static func kind(node: Dictionary, date: String) -> String:
	var role=node.get("kind",data().get("role_overrides",{}).get(node.get("id",""),{}).get("kind","city"))
	# No unsupported exact day is assigned to the 1925 province-seat transition.
	if node.get("id","")=="tianjin" and date>="1925-01-01":return "city"
	return role

static func kind_label(node: Dictionary, date: String) -> String:
	return {"national_capital":"首都","capital":"省城","county":"县城","city":"城市","market":"集镇","village":"村落","pass":"关隘"}.get(kind(node,date),"地方节点")

static func asset_id(node: Dictionary, date: String) -> String:
	return {"national_capital":"scenery_historic_capital","capital":"scenery_historic_capital","county":"scenery_historic_county","city":"scenery_station_town","market":"scenery_historic_market","village":"scenery_historic_village","pass":"scenery_jiumenkou_wall"}.get(kind(node,date),"scenery_historic_market")

static func importance(node: Dictionary, date: String) -> int:
	return {"national_capital":6,"capital":5,"city":4,"county":3,"market":2,"village":1,"pass":3}.get(kind(node,date),2)

static func visible_at(node: Dictionary, date: String, zoom: float, selected: String="") -> bool:
	if date<str(node.get("active_from","0000-01-01")) or date>=str(node.get("active_to","9999-12-31")):return false
	if node.get("id","")==selected:return true
	var rank=importance(node,date)
	return zoom>=.48 if rank==1 else zoom>=.30 if rank==2 else zoom>=.16 if rank==3 else zoom>=.06 if rank==4 else true

func prepare(map: Dictionary, date: String="1924-01-01") -> void:
	map_key=map.get("fixture_source",{}).get("source_map_id",map.id)
	if map_key=="qa_capacity_conquest":map_key="conquest_china"
	nodes=[];index={};zones=[];owners={};owner_signature="";control_clip_diagnostics={}
	var entry=data().get("maps",{}).get(map_key,{})
	for record in entry.get("markers",[]):add_node(record)
	for city in map.cities:
		var node=city.duplicate(true)
		node["world"]=city.get("render_position",[HexGrid.to_world(HexGrid.coordinate(city.position)).x,HexGrid.to_world(HexGrid.coordinate(city.position)).y])
		node["kind"]=city.get("kind",data().get("role_overrides",{}).get(city.id,{}).get("kind","city"))
		node["administration"]=ContentRegistry.administration_name(city,date)
		node["longitude"]=city.lon_e6/1000000.0;node["latitude"]=city.lat_e6/1000000.0
		node["sources"]=data().get("role_overrides",{}).get(city.id,{}).get("sources",[])
		node["note"]="历史地方与交通节点。军用城池等级另行显示。"
		node["rank_period"]="1920—1924";add_node(node)
	var year=ContentRegistry.administration_year(date)
	var marine=MapCoastGeometry.for_map(map,map_key)
	var zone_records=marine.get("control_zones_by_year",{}).get(year,entry.get("control_zones_by_year",{}).get(year,[]))
	for record in zone_records:
		if record.triangles.is_empty():continue
		var vertices=PackedVector3Array()
		for point in record.triangles:vertices.append(Vector3(point[0],point[1],0))
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices
		var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		var bounds=record.bounds
		zones.append({"city_id":record.city_id,"province":record.province,"mesh":mesh,"borders":record.borders.map(points_array),"bounds":Rect2(Vector2(bounds[0],bounds[1]),Vector2(bounds[2]-bounds[0],bounds[3]-bounds[1])),"land_clipped":not marine.is_empty()})
	# The continental map does not pretend to have surveyed historical county
	# polygons.  It still needs a readable ownership layer, so each real city
	# receives a deterministic influence hex, intersected with source land and
	# water holes. The authoritative owner remains state.cities[].owner_id.
	if zones.is_empty() and map.id=="asia_strategic":
		var clipped=MapControlLandClip.for_map(map)
		zones=MapControlLandClip.city_zones(clipped)
		control_clip_diagnostics=MapControlLandClip.diagnostics(clipped)
	control_borders.prepare(map_key, year)

func add_node(record: Dictionary) -> void:
	var node=record.duplicate(true);node["at"]=Vector2(node.world[0],node.world[1])
	nodes.append(node);index[node.id]=node

func points_array(raw: Array) -> PackedVector2Array:
	var result=PackedVector2Array()
	for xy in raw:result.append(Vector2(xy[0],xy[1]))
	return result

func update_owners(state: Dictionary) -> void:
	owners={};var parts=PackedStringArray()
	for city in state.cities:owners[city.id]=city.owner_id;parts.append(city.id+":"+city.owner_id)
	owner_signature="|".join(parts)

func references(state: Dictionary) -> Array:
	var excluded={}
	for city in state.cities:excluded[city.id]=true
	for poi in state.map.get("reference_pois",[]):excluded[poi.id]=true
	return nodes.filter(func(node):return not excluded.has(node.id))

func control_city(state: Dictionary, at: Vector2) -> Dictionary:
	# A place inherits the local game's city influence, never a purported historic
	# county boundary. Inactive or occupied reference nodes stay uncolored.
	var best=INF;var nearest={}
	var region=index.values().filter(func(node):return node.at.distance_squared_to(at)<.01)
	var admin=region[0].get("province",region[0].get("administration","")).split(" · ")[0] if not region.is_empty() else ""
	if admin=="京兆地方":admin="直隶"
	for city in state.map.cities:
		var city_admin=ContentRegistry.administration_name(city,state.date)
		if city_admin=="京兆地方":city_admin="直隶"
		if not admin.is_empty() and not city_admin.begins_with(admin):continue
		var position=Vector2(city.render_position[0],city.render_position[1])
		var distance=position.distance_squared_to(at)
		if distance<best:best=distance;nearest=city
	if nearest.is_empty() or not owners.has(nearest.id):return {}
	return StateAccess.find(state,"cities",nearest.id)
