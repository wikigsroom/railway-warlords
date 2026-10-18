class_name MapDetails
extends RefCounted

# Decorations derive from existing source classes and vector edges. They never
# introduce a new river, coast, woodland boundary, settlement or rules cell.
var features: Array=[]
var buckets: Dictionary={}
var surfaces: Dictionary={}
var surface_families: Dictionary={}
var ground_families: Dictionary={}
var ground_clips: Dictionary={}
var source_ground_coverage: Dictionary={}
var ground_policy: Dictionary={}
var diagnostics: Dictionary={}
var overhang=220.0
var surface_template: Dictionary={}
var surface_color_templates: Dictionary={}
var blend_material: ShaderMaterial
var blend_material_prepared=false
var continuous_templates: Array=[]
var continuous_vertices=PackedVector3Array()
var continuous_uvs=PackedVector2Array()
var continuous_color_templates: Dictionary={}
var macro_chunks: Dictionary={}
var macro_chunk_meshes: Dictionary={}
var macro_index_prepared=false
const MACRO_CHUNK_SIZE=16
const SURFACE_BLEND_RADIUS=64.0
const SURFACE_BLEND_INNER=.70

func build(map: Dictionary, cells: Dictionary, relief: AtlasRelief, coast: Array, rivers: Array) -> void:
	features=[];buckets={};surfaces={};surface_families={};diagnostics={"active":false}
	ground_families={};ground_clips={};source_ground_coverage={};continuous_color_templates.clear()
	ground_policy={"forest_floor_requires_sourced_forest":true,"withheld_forest_floor_cells":0,"drawn_families":{}}
	blend_material=null;blend_material_prepared=false
	macro_chunks.clear();macro_chunk_meshes.clear();macro_index_prepared=false
	if not MapArtBank.available():return
	var started=Time.get_ticks_usec();var candidates: Array=[];var materials: Array=[]
	source_ground_coverage=MapGroundCoverage.for_map(map)
	ground_families=source_ground_coverage.get("families",{}).duplicate()
	ground_clips=source_ground_coverage.get("clips",{})
	for key in ground_families:
		var source_cell: Dictionary=cells.get(HexGrid.from_key(key),{})
		var regional=str(ground_families[key]);var drawn=MapTerrainSurfaces.draw_family(regional,source_cell)
		ground_families[key]=drawn
		if drawn!=regional:ground_policy.withheld_forest_floor_cells+=1
		ground_policy.drawn_families[drawn]=int(ground_policy.drawn_families.get(drawn,0))+1
	for h in cells:
		var cell: Dictionary=cells[h];var p=HexGrid.to_world(h)
		var kind=TerrainVisuals.kind_for_cell(cell);var family=MapArtBank.material_family(cell)
		# Reserve the entire material footprint against the surveyed boundary.
		# The continuous land/water base handles this narrow shore band, so a
		# hex texture cannot paint over an actual inlet, island edge or lake.
		var material_rect=Rect2(p-Vector2.ONE*SURFACE_BLEND_RADIUS,Vector2.ONE*SURFACE_BLEND_RADIUS*2.0)
		var safe_material=(kind=="sea" or cell.get("render_land_covered",true)) and not relief.intersects_index(material_rect,relief.boundary_buckets,0.0)
		if not family.is_empty() and safe_material:
			var new_surface=MapTerrainSurfaces.variant_for(family,h)
			if new_surface.is_empty():materials.append({"key":HexGrid.key(h),"family":family,"position":p})
			else:surfaces[HexGrid.key(h)]=new_surface
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
	surfaces.merge(MapArtBank.assign(materials,180.0))
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

func surface_meshes(entries: Array, strategic: bool, limit: int=1900, continuous: bool=true, fine_details: bool=true, include_macros: bool=true) -> Dictionary:
	# Batch feathered hex materials by immutable source texture. This is native
	# mesh drawing, not a generated-image composite or a stored raster atlas.
	prepare_surface_template()
	var groups: Dictionary={};var macro_groups: Dictionary={};var count=0
	for entry in entries:
		if count>=limit:break
		var key=HexGrid.key(entry.hex);var id=str(surfaces.get(key,""))
		if id.is_empty():continue
		var family=str(surface_families.get(key,MapArtBank.material_family(entry.cell)))
		var alpha=MapTerrainSurfaces.alpha_for(family,strategic)
		var macro_id=MapTerrainSurfaces.macro_id(family)
		if alpha<0:
			alpha=float({"meadow":.56,"dry_grass":.58,"rocky_ground":.38,"woodland_floor":.60,"wetland_ground":.66,"sea_water":.10,"sandy_ground":.74,"arid_gravel":.68,"alluvial_soil":.58}.get(family,.0))
			if strategic:alpha*=.86
		if not groups.has(id):groups[id]={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
		if include_macros and not macro_id.is_empty() and not macro_groups.has(macro_id):macro_groups[macro_id]={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
		var group: Dictionary=groups[id];var center=HexGrid.to_world(entry.hex)
		# Transform and append whole packed arrays in native code. Rebuilding
		# 54 vertices twice in GDScript for every visible cell stalled selection.
		# Geometry, source UVs and feather weights retain the same layout.
		var vertices: PackedVector3Array=Transform3D(Basis.IDENTITY,Vector3(center.x,center.y,0))*surface_template.vertices
		if fine_details or macro_id.is_empty():
			group.vertices.append_array(vertices)
			group.colors.append_array(surface_colors(alpha if macro_id.is_empty() else MapTerrainSurfaces.detail_alpha(strategic)))
			group.uvs.append_array(surface_template.detail_uvs)
		if include_macros and not macro_id.is_empty():
			var macro: Dictionary=macro_groups[macro_id]
			if continuous:append_continuous_ground(macro,entry.hex,family)
			else:
				macro.vertices.append_array(vertices);macro.colors.append_array(surface_colors(alpha))
				macro.uvs.append_array(Transform2D(0.0,MapTerrainSurfaces.macro_uv(center))*surface_template.macro_uvs)
		count+=1
	var result: Array=[]
	# Overlapping materials must keep their blend order while panning.
	# Continuous region-wide pigment precedes the low-strength per-cell detail.
	# Repeating UVs never move with the camera or change with faction ownership.
	for layer_index in range(2):
		var layer: Dictionary=macro_groups if layer_index==0 else groups
		var source_ids=layer.keys();source_ids.sort()
		for id in source_ids:
			var group: Dictionary=layer[id];var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
			if group.vertices.is_empty():continue
			arrays[Mesh.ARRAY_VERTEX]=group.vertices;arrays[Mesh.ARRAY_COLOR]=group.colors;arrays[Mesh.ARRAY_TEX_UV]=group.uvs
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			result.append({"asset_id":id,"mesh":mesh,"layer":"macro" if layer_index==0 else "detail","continuous":continuous and layer_index==0})
	return {"count":count,"batches":result,"macro_materials":macro_groups.size(),"continuous":continuous}

func continuous_macro_meshes(view: Rect2) -> Dictionary:
	# World-fixed chunks retain the exact same material triangles at every zoom.
	# Selection/panning only submits intersecting cached meshes; the 74k-cell
	# map does not walk or rebuild all ground assignments during an atlas pan.
	if not macro_index_prepared:
		macro_index_prepared=true
		var assignments=surface_families if ground_families.is_empty() else ground_families
		for key in assignments:
			var family=str(assignments[key])
			if MapTerrainSurfaces.macro_id(family).is_empty():continue
			var hex=HexGrid.from_key(key);var chunk=Vector2i(floori(float(hex.x)/MACRO_CHUNK_SIZE),floori(float(hex.y)/MACRO_CHUNK_SIZE))
			var center=HexGrid.to_world(hex);var bounds=Rect2(center-Vector2.ONE*HexGrid.RADIUS,Vector2.ONE*HexGrid.RADIUS*2)
			if not macro_chunks.has(chunk):macro_chunks[chunk]={"hexes":[],"bounds":bounds,"sources":{}}
			macro_chunks[chunk].hexes.append(hex);macro_chunks[chunk].bounds=macro_chunks[chunk].bounds.merge(bounds)
			macro_chunks[chunk].sources[MapTerrainSurfaces.macro_id(family)]=true
	var batches: Array=[];var sources: Dictionary={};var count=0;var created=0
	for chunk in macro_chunks:
		var row: Dictionary=macro_chunks[chunk]
		if not view.intersects(row.bounds):continue
		if not macro_chunk_meshes.has(chunk):
			var group={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
			for hex in row.hexes:append_continuous_ground(group,hex,ground_family(HexGrid.key(hex)))
			var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=group.vertices;arrays[Mesh.ARRAY_COLOR]=group.colors;arrays[Mesh.ARRAY_TEX_UV]=group.uvs
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			macro_chunk_meshes[chunk]={"asset_id":row.sources.keys()[0],"mesh":mesh,"layer":"macro","continuous":true,"source_asset_ids":row.sources.keys()};created+=1
		batches.append(macro_chunk_meshes[chunk]);sources.merge(row.sources);count+=row.hexes.size()
	return {"count":count,"batches":batches,"macro_materials":sources.size(),"chunks_created":created,"chunks_submitted":batches.size(),"chunks_cached":macro_chunk_meshes.size()}

func ground_material(strategic: bool) -> ShaderMaterial:
	if not blend_material_prepared:
		blend_material_prepared=true;blend_material=GroundMaterialBlend.material(strategic)
	return blend_material

func ground_family(key: String) -> String:
	return str(ground_families.get(key,"")) if not ground_families.is_empty() else str(surface_families.get(key,""))

func append_continuous_ground(group: Dictionary, hex: Vector2i, family: String) -> void:
	# The six source-centre triangles partition the hex exactly. Adjacent hexes
	# sample the same three originals with the same barycentric weights, so a
	# same-family region has constant opacity instead of overlapping apertures.
	if continuous_templates.is_empty():
		for direction in range(6):
			var a=HexGrid.to_world(HexGrid.DIRECTIONS[direction]);var b=HexGrid.to_world(HexGrid.DIRECTIONS[(direction+1)%6])
			var corner=(a+b)/3.0
			continuous_templates.append(PackedVector3Array([Vector3.ZERO,Vector3(a.x*.5,a.y*.5,0),Vector3(corner.x,corner.y,0),Vector3.ZERO,Vector3(corner.x,corner.y,0),Vector3(b.x*.5,b.y*.5,0)]))
			continuous_vertices.append_array(continuous_templates[-1])
			continuous_uvs.append_array(PackedVector2Array([GroundMaterialBlend.weights(1,0),GroundMaterialBlend.weights(.5,.5),GroundMaterialBlend.weights(1.0/3.0,1.0/3.0),GroundMaterialBlend.weights(1,0),GroundMaterialBlend.weights(1.0/3.0,1.0/3.0),GroundMaterialBlend.weights(.5,0)]))
	var layer_ids=GroundMaterialBlend.source_layers();var first=int(layer_ids[family]);var center=HexGrid.to_world(hex)
	var nearby: Array=[]
	for direction in HexGrid.DIRECTIONS:nearby.append(int(layer_ids.get(ground_family(HexGrid.key(hex+direction)),-1)))
	var clipped: Array=ground_clips.get(HexGrid.key(hex),[])
	if not clipped.is_empty():
		# These numerical vertices partition only the source land intersection.
		# Interpolated weights retain the very same three-source basis as an
		# unclipped neighbour; no texture is painted across a source lake/inlet.
		for vertex in clipped:
			var direction=int(vertex[4]);var a=int(nearby[direction]);var b=int(nearby[(direction+1)%6])
			group.vertices.append(Vector3(float(vertex[0]),float(vertex[1]),0))
			group.uvs.append(GroundMaterialBlend.weights(float(vertex[2]),float(vertex[3])))
			group.colors.append(Color(first/255.0,(first if a<0 else a)/255.0,(first if b<0 else b)/255.0,1))
		return
	group.vertices.append_array(Transform3D(Basis.IDENTITY,Vector3(center.x,center.y,0))*continuous_vertices)
	group.uvs.append_array(continuous_uvs)
	for direction in range(6):
		var a=int(nearby[direction]);var b=int(nearby[(direction+1)%6]);var signature=Vector3i(first,a,b)
		if not continuous_color_templates.has(signature):
			var pigment=Color(first/255.0,(first if a<0 else a)/255.0,(first if b<0 else b)/255.0,1)
			var corner_coverage=(1.0+float(a>=0)+float(b>=0))/3.0;var colors=PackedColorArray()
			for coverage in [1.0,(1.0+float(a>=0))*.5,corner_coverage,1.0,corner_coverage,(1.0+float(b>=0))*.5]:colors.append(Color(pigment,coverage if source_ground_coverage.is_empty() else 1.0))
			continuous_color_templates[signature]=colors
		group.colors.append_array(continuous_color_templates[signature])

func prepare_surface_template() -> void:
	if not surface_template.is_empty():return
	surface_template={"vertices":PackedVector3Array(),"detail_uvs":PackedVector2Array(),"macro_uvs":PackedVector2Array(),"weights":PackedFloat32Array()}
	var corners=HexGrid.corners(Vector2.ZERO,SURFACE_BLEND_RADIUS)
	for index in range(6):
		var a=corners[index];var b=corners[(index+1)%6];var inner_a=a*SURFACE_BLEND_INNER;var inner_b=b*SURFACE_BLEND_INNER
		var offsets=[Vector2.ZERO,inner_a,inner_b,inner_a,a,b,inner_a,b,inner_b]
		for vertex in range(offsets.size()):
			var offset: Vector2=offsets[vertex]
			surface_template.vertices.append(Vector3(offset.x,offset.y,0))
			surface_template.detail_uvs.append(offset/(SURFACE_BLEND_RADIUS*2.0)+Vector2(.5,.5))
			surface_template.macro_uvs.append(MapTerrainSurfaces.macro_uv(offset))
			surface_template.weights.append(0.0 if vertex in [4,5,7] else 1.0)

func surface_colors(alpha: float) -> PackedColorArray:
	if not surface_color_templates.has(alpha):
		var colors=PackedColorArray()
		for weight in surface_template.weights:colors.append(Color(1,1,1,weight*alpha))
		surface_color_templates[alpha]=colors
	return surface_color_templates[alpha]
