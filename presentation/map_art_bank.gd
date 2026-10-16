class_name MapArtBank
extends RefCounted

# A presentation-only index of immutable whole Sub2 originals. No gameplay RNG,
# owner, terrain class, historical boundary or source PNG is changed here.
static var catalog: Dictionary={}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists("res://presentation/data/map_bank_visuals.json"):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/map_bank_visuals.json"))
		if parsed is Dictionary:catalog=parsed
	return catalog

static func available() -> bool:
	return data().get("records",{}).size()>=796

static func ids(family: String) -> Array:
	return data().get("families",{}).get(family,[])

static func pick(family: String, identity: String) -> String:
	var pool=ids(family)
	return "" if pool.is_empty() else str(pool[absi(hash(family+":"+identity))%pool.size()])

static func assign(items: Array, radius: float=240.0) -> Dictionary:
	# Stable global placement, not viewport order: panning cannot change a sprite.
	# Greedy spatial exclusion prevents the same silhouette reappearing nearby.
	var sorted=items.duplicate();sorted.sort_custom(func(a,b):return a.key<b.key)
	var occupied: Dictionary={};var result: Dictionary={}
	for item in sorted:
		var pool: Array=item.get("candidate_ids",ids(item.family))
		if pool.is_empty():continue
		var bucket=Vector2i(floori(item.position.x/radius),floori(item.position.y/radius))
		var uses: Dictionary={}
		for dx in range(-1,2):
			for dy in range(-1,2):
				for other in occupied.get(bucket+Vector2i(dx,dy),[]):
					if item.position.distance_squared_to(other.position)<radius*radius:uses[other.id]=int(uses.get(other.id,0))+1
		var start=absi(hash(item.family+":"+item.key))%pool.size()
		var chosen="";var score=2147483647
		for index in range(pool.size()):
			var candidate=str(pool[(start+index)%pool.size()]);var count=int(uses.get(candidate,0))
			if count<score:chosen=candidate;score=count
			if score==0:break
		result[item.key]=chosen
		if not occupied.has(bucket):occupied[bucket]=[]
		occupied[bucket].append({"position":item.position,"id":chosen})
	return result

static func source_rect(id: String, bounds: Vector2) -> Rect2:
	var row: Dictionary=data().get("records",{}).get(id,{})
	if row.is_empty():return Rect2(Vector2(-bounds.x*.5,-bounds.y),bounds)
	var alpha=row.alpha_bounds
	var occupied=Vector2(alpha[2]-alpha[0],alpha[3]-alpha[1])
	var factor=minf(bounds.x/occupied.x,bounds.y/occupied.y)
	var foot=Vector2((alpha[0]+alpha[2])*.5,alpha[3])*factor
	# The entire original texture, with its native aspect and transparent margin.
	return Rect2(-foot,Vector2(row.dimensions[0],row.dimensions[1])*factor)

static func material_family(cell: Dictionary) -> String:
	var kind=TerrainVisuals.kind_for_cell(cell)
	if kind=="sea":return "sea_water"
	if kind=="forest":return "woodland_floor"
	if kind=="wetland":return "wetland_ground"
	if kind in ["hill","mountain","peak"]:return "rocky_ground"
	if kind=="plain":
		# Source geography chooses the material. Identity is used only to choose
		# an independent image within that material, never to invent a biome.
		var sourced=str(cell.get("presentation_surface_family",""))
		if sourced in ["meadow","dry_grass","sandy_ground","arid_gravel","alluvial_soil","wetland_ground"]:return sourced
		return "meadow"
	return ""

static func region_for(node: Dictionary) -> String:
	# Explicit source-location bindings: conquest never changes architecture.
	var id=str(node.get("id",""))
	var bindings={
		"japan":["tokyo","yokohama","osaka","hiroshima","sapporo"],
		"korea":["seoul","pyongyang","busan"],
		"north_eurasia":["vladivostok","khabarovsk","irkutsk","petrograd","moscow"],
		"west_central_asia":["tashkent","samarkand","baku","tehran","tabriz","baghdad","kabul","kashgar"],
		"south_asia":["delhi","lahore","bombay","calcutta","madras"],
		"southeast_asia":["haiphong","rangoon","mandalay","bangkok","hanoi","saigon","phnom_penh","singapore","manila","batavia","surabaya"]}
	for region in bindings:
		if id in bindings[region]:return region
	# These mixed/locally distinctive places need a separately sourced symbol.
	# Do not disguise an unsuitable Chinese facade as a local reconstruction.
	if id in ["lhasa","ulaanbaatar","istanbul","jerusalem","tbilisi","hong_kong","macau","urumqi"]:return ""
	var lon=float(node.get("longitude",float(node.get("lon_e6",0))/1000000.0))
	var lat=float(node.get("latitude",float(node.get("lat_e6",0))/1000000.0))
	if lon>=99 and lon<=130 and lat>=21 and lat<=50:
		return "north_china" if lat>=33 else "south_china"
	return ""

static func settlement_id(node: Dictionary, date: String, role_override: String="") -> String:
	return pick(settlement_family(node,date,role_override),str(node.get("id","")))

static func settlement_family(node: Dictionary, date: String, role_override: String="") -> String:
	var region=region_for(node)
	if region.is_empty():return ""
	var role=role_override if not role_override.is_empty() else HistoricalPlaces.kind(node,date)
	role={"national_capital":"capital","city":"county","port":"market"}.get(role,role)
	if role not in ["village","market","county","capital","station","dock"]:return ""
	var family=role+"_"+region
	# A dock or station uses the nearest appropriate generic regional visual
	# only if a source family was deliberately authored for that region.
	return family if not ids(family).is_empty() else ""
