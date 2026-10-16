class_name MapDetails
extends RefCounted

# Decorations derive from existing source classes and vector edges. They never
# introduce a new river, coast, woodland boundary, settlement or rules cell.
var features: Array=[]
var buckets: Dictionary={}
var surfaces: Dictionary={}
var surface_families: Dictionary={}
var diagnostics: Dictionary={}
var overhang=220.0
const SURFACE_BLEND_RADIUS=64.0
const SURFACE_BLEND_INNER=.50

func build(map: Dictionary, cells: Dictionary, relief: AtlasRelief, coast: Array, rivers: Array) -> void:
	features=[];buckets={};surfaces={};surface_families={};diagnostics={"active":false}
	if not MapArtBank.available():return
	var started=Time.get_ticks_usec();var candidates: Array=[];var materials: Array=[]
	for h in cells:
		var cell: Dictionary=cells[h];var p=HexGrid.to_world(h)
		var kind=TerrainVisuals.kind_for_cell(cell);var family=MapArtBank.material_family(cell)
		# Reserve the entire material footprint against the surveyed boundary.
		# The continuous land/water base handles this narrow shore band, so a
		# hex texture cannot paint over an actual inlet, island edge or lake.
		var material_rect=Rect2(p-Vector2.ONE*SURFACE_BLEND_RADIUS,Vector2.ONE*SURFACE_BLEND_RADIUS*2.0)
		var safe_material=(kind=="sea" or cell.get("render_land_covered",true)) and not relief.intersects_index(material_rect,relief.boundary_buckets,0.0)
		if not family.is_empty() and safe_material:
			materials.append({"key":HexGrid.key(h),"family":family,"position":p})
			surface_families[HexGrid.key(h)]=family
		if kind not in ["forest","wetland","hill","mountain","peak"] or not cell.get("render_land_covered",false):continue
		var seed=absi(hash(str(cell.get("id",HexGrid.key(h)))))
		var bounds=Vector2(92,64);var min_zoom=.50
		if kind=="forest":
			var profile=TerrainVisuals.edge_profile(cells,h,"forest")
			var sparse=int(profile.boundary_edges)>=3
			# A named site's supplied tree language wins over decorative variation.
			var source_kind=str(cell.get("presentation_forest_asset",""))
			var pine=source_kind.contains("pine") if not source_kind.is_empty() else seed%3!=0
			family=("pine" if pine else "deciduous")+("_sparse" if sparse else "_dense")
			if int(profile.boundary_edges)>=4 and source_kind.is_empty():family="forest_edge"
			bounds=Vector2(104,94) if sparse else Vector2(122,112);min_zoom=.28
		elif kind=="wetland":family="wetland_reeds";bounds=Vector2(82,58)
		else:
			if seed%11!=0:continue
			family="rocky_outcrop";bounds=Vector2(72,49);min_zoom=.68
		var foot=p+Vector2(float(seed%11)-5,24+float((seed/11)%9)-4)
		var candidate={"key":"cell:"+str(cell.id),"cell_id":cell.id,"family":family,"position":foot,"bounds":bounds,"min_zoom":min_zoom,"source_kind":kind}
		if kind=="wetland":candidate["candidate_ids"]=eligible_marsh_ids()
		candidates.append(candidate)
	# Decorations are spaced along the actual archived vector. Candidate anchors
	# must pass a whole-source land and route-clearance test after assignment.
	append_edge_candidates(candidates,coast,"shore",relief,200.0)
	append_edge_candidates(candidates,rivers,"riverbank",relief,230.0)
	surfaces=MapArtBank.assign(materials,180.0)
	var choices=MapArtBank.assign(candidates,250.0)
	var rejected=0;var uses: Dictionary={}
	for feature in candidates:
		var id=str(choices.get(feature.key,""))
		if id.is_empty():continue
		var rectangle=MapArtBank.source_rect(id,feature.bounds)
		var footprint=Rect2(feature.position+rectangle.position,rectangle.size)
		# Full original transparent margins are reserved as well. This makes a
		# large canopy unable to hide a source tributary or railway.
		if not relief.dry_footprint(footprint) or relief.intersects_index(footprint,relief.path_buckets.river,4) or relief.intersects_index(footprint,relief.path_buckets.rail,5):rejected+=1;continue
		feature["asset_id"]=id;feature["texture_rect"]=rectangle;feature["footprint"]=footprint
		feature["terrain_id"]=feature.source_kind;feature["category"]="scenery"
		features.append(feature);uses[id]=int(uses.get(id,0))+1
	features.sort_custom(func(a,b):return a.position.y<b.position.y if a.position.y!=b.position.y else a.key<b.key)
	for index in range(features.size()):
		var feature=features[index];var bucket=Vector2i(floori(feature.position.x/512),floori(feature.position.y/512))
		if not buckets.has(bucket):buckets[bucket]=[]
		buckets[bucket].append(index)
		var rect: Rect2=feature.texture_rect
		overhang=maxf(overhang,maxf(rect.position.length(),rect.end.length()))
	diagnostics={"active":true,"source_cells":cells.size(),"material_assignments":surfaces.size(),"placed":features.size(),"unique_originals":uses.size(),"rejected_for_source_geography":rejected,"preparation_ms":(Time.get_ticks_usec()-started)/1000.0,"invented_waterways":0,"rule_cells_changed":false,"random_stream_used":false,"source_images_modified":false,"full_source_rectangles_reserved":true}

func append_edge_candidates(result: Array, lines: Array, family: String, relief: AtlasRelief, spacing: float) -> void:
	for line_index in range(lines.size()):
		var line: PackedVector2Array=lines[line_index]
		var accumulated=0.0;var ordinal=0
		for index in range(1,line.size()):
			var a: Vector2=line[index-1];var b: Vector2=line[index];var segment=a.distance_to(b)
			if segment<.01:continue
			var direction=(b-a).normalized();var normal=direction.orthogonal()
			var distance=spacing-accumulated
			while distance<=segment:
				var point=a+direction*distance
				for side in [1.0,-1.0]:
					# An offset is a symbol clearance, not a measured river width.
					var position=point+normal*side*62.0
					if not relief.dry_point(position):continue
					var source_cell: Dictionary=relief.cells.get(HexGrid.key(HexGrid.from_world(position)),{})
					var source_terrain=str(source_cell.get("natural_terrain_id",source_cell.get("terrain_id","")))
					var pool=eligible_edge_ids(family,source_terrain)
					if pool.is_empty():continue
					result.append({"key":"%s:%d:%d"%[family,line_index,ordinal],"family":family,"candidate_ids":pool,"position":position,"bounds":Vector2(74,45),"min_zoom":.62,"source_kind":family,"source_terrain":source_terrain,"source_vector_position":point,"symbol_clearance_world":62.0})
					break
				ordinal+=1;distance+=spacing
			accumulated=fmod(accumulated+segment,spacing)

func eligible_edge_ids(family: String, source_terrain: String) -> Array:
	# Whole-source visual inspection: riverbank 001--006 are low grass tufts;
	# later originals contain rock hummocks. Shore originals are rocky too.
	# A surveyed waterline alone is not evidence for a rocky floodplain/coast.
	var rocky=source_terrain in ["hill","mountain","peak"]
	if family=="shore" and not rocky:return []
	if family=="riverbank" and not rocky:
		if source_terrain not in ["plain","forest","wetland"]:return []
		return MapArtBank.ids(family).filter(func(id):return int(MapArtBank.data().records[id].get("variant",0)) in range(1,7))
	return MapArtBank.ids(family)

func eligible_marsh_ids() -> Array:
	# Exclude inspected outputs with prominent invented rock mounds. Retain
	# their original bytes and provenance; wetland classification is no rock
	# survey and does not justify those particular silhouettes on a marsh cell.
	var flat_variants=[1,2,3,4,5,6,8,9,10,11,12,13,16,17,18,19,21,24]
	return MapArtBank.ids("wetland_reeds").filter(func(id):return int(MapArtBank.data().records[id].get("variant",0)) in flat_variants)

func visible_features(view: Rect2, zoom: float) -> Array:
	var expanded=view.grow(overhang);var indices: Array=[]
	for x in range(floori(expanded.position.x/512),floori(expanded.end.x/512)+1):
		for y in range(floori(expanded.position.y/512),floori(expanded.end.y/512)+1):
			for index in buckets.get(Vector2i(x,y),[]):
				var feature=features[index]
				if zoom>=feature.min_zoom and view.intersects(feature.footprint):indices.append(index)
	indices.sort();var result: Array=[]
	for index in indices:result.append(features[index])
	return result

func surface_meshes(entries: Array, strategic: bool, limit: int=1900) -> Dictionary:
	# Batch feathered hex materials by immutable source texture. This is native
	# mesh drawing, not a generated-image composite or a stored raster atlas.
	var groups: Dictionary={};var count=0
	for entry in entries:
		if count>=limit:break
		var key=HexGrid.key(entry.hex);var id=str(surfaces.get(key,""))
		if id.is_empty():continue
		var family=str(surface_families.get(key,MapArtBank.material_family(entry.cell)))
		var alpha=float({"meadow":.56,"dry_grass":.58,"rocky_ground":.38,"woodland_floor":.60,"wetland_ground":.66,"sea_water":.10,"sandy_ground":.74,"arid_gravel":.68,"alluvial_soil":.58}.get(family,.0))
		if strategic:alpha*=.86
		if not groups.has(id):groups[id]={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
		var group: Dictionary=groups[id];var center=HexGrid.to_world(entry.hex);var corners=HexGrid.corners(center,SURFACE_BLEND_RADIUS)
		for index in range(6):
			var outer_a=corners[index]-center;var outer_b=corners[(index+1)%6]-center
			var inner_a=outer_a*SURFACE_BLEND_INNER;var inner_b=outer_b*SURFACE_BLEND_INNER
			# Neighboring feathered materials overlap across the operation edge.
			# This removes bare green gutters without changing the 48px grid;
			# build() reserves this entire wider footprint against real coastlines.
			var offsets=[Vector2.ZERO,inner_a,inner_b,inner_a,outer_a,outer_b,inner_a,outer_b,inner_b]
			for vertex in range(offsets.size()):
				var offset: Vector2=offsets[vertex]
				group.vertices.append(Vector3(center.x+offset.x,center.y+offset.y,0))
				group.colors.append(Color(1,1,1,0.0 if vertex in [4,5,7] else alpha))
				group.uvs.append(offset/(SURFACE_BLEND_RADIUS*2.0)+Vector2(.5,.5))
		count+=1
	var result: Array=[]
	# Overlapping materials must keep their blend order while panning.
	var source_ids=groups.keys();source_ids.sort()
	for id in source_ids:
		var group: Dictionary=groups[id];var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=group.vertices;arrays[Mesh.ARRAY_COLOR]=group.colors;arrays[Mesh.ARRAY_TEX_UV]=group.uvs
		var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		result.append({"asset_id":id,"mesh":mesh})
	return {"count":count,"batches":result}
