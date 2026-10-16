class_name AtlasRelief
extends RefCounted

# Presentation-only relief, derived from the immutable surveyed map. No rules data is edited.
var mesh: ArrayMesh
var shade_field=ReliefShadeField.new()
var contours: Array=[]
var features: Array=[]
var diagnostics: Dictionary={}
var cells: Dictionary={}
var land: Array=[]
var land_bounds: Array[Rect2]=[]
var rivers: Array=[]
var tracks: Array=[]
var boundary_buckets: Dictionary={}
var path_buckets: Dictionary={}
var meters_per_world_unit=1.0
var strategic_relief=false
var geographic_gradient=false
var asset_metadata: Dictionary={}
var feature_buckets: Dictionary={}
var maximum_feature_overhang=0.0
const LIGHT_DIRECTION=Vector3(-.55,-.68,.62)
const HEIGHT_EXAGGERATION=6.0

func build(map: Dictionary, land_shapes: Array, river_lines: Array, minor_river_lines: Array=[]) -> void:
	var started=Time.get_ticks_usec()
	var surveyed_grid=map.get("physical_grid_source","")=="natural_earth_land_10m_v5_1_1"
	var strategic_scale=map.get("strategic_scale",false)
	strategic_relief=strategic_scale
	geographic_gradient=strategic_scale and not str(map.get("physical_relief_source","")).is_empty()
	meters_per_world_unit=maxf(1.0,float(map.get("hex_radius_m",1000))/HexGrid.RADIUS)
	asset_metadata={}
	if FileAccess.file_exists("res://presentation/data/relief_visuals.json"):
		var visual_data=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/relief_visuals.json"))
		if visual_data is Dictionary:asset_metadata=visual_data.get("records",{})
	if MapArtBank.available():asset_metadata.merge(MapArtBank.data().records)
	land=land_shapes;rivers=river_lines.duplicate();rivers.append_array(minor_river_lines)
	features.clear();feature_buckets.clear();maximum_feature_overhang=0.0
	contours.clear();cells.clear();tracks.clear();boundary_buckets.clear();land_bounds.clear();mesh=null
	path_buckets={"river":{},"rail":{}}
	for shape in land:
		var bounds=Rect2(shape.exterior[0],Vector2.ZERO)
		for point in shape.exterior:bounds=bounds.expand(point)
		land_bounds.append(bounds)
		index_boundary(shape.exterior)
		for hole in shape.holes:index_boundary(hole)
	for cell in map.cells:cells[HexGrid.key(HexGrid.coordinate(cell.position))]=cell
	for edge in map.rail_edges:
		var line=PackedVector2Array()
		for position in edge.path_hexes:line.append(HexGrid.to_world(HexGrid.coordinate(position)))
		tracks.append(line)
	for line in rivers:index_path(line,path_buckets.river)
	for line in tracks:index_path(line,path_buckets.rail)
	var indexed=Time.get_ticks_usec()
	var vertices=PackedVector3Array();var colors=PackedColorArray();var uvs=PackedVector2Array();var seen: Dictionary={};var shades: Dictionary={}
	for cell in map.cells:
		if not sampled_land(cell) or (surveyed_grid and not cell.get("render_land_covered",false)):continue
		# Surveyed cell coverage and the clipped presentation coastline have
		# different extents. Check the actual drawn polygon before adding relief.
		if strategic_scale:
			# Strategic cells are already classified against Natural Earth land/water
			# geometry. Re-testing every cell against hundreds of coastline rings would
			# make the continental overview unusably slow; the land surface below still
			# clips the visible polygon.
			if cell.get("render_land_covered",false):shades[cell.id]=shade(cell)
		elif dry_point(HexGrid.to_world(HexGrid.coordinate(cell.position))):shades[cell.id]=shade(cell)
	shade_field.build(cells,shades)
	for cell in map.cells:
		if not shades.has(cell.id):continue
		var h=HexGrid.coordinate(cell.position);var p=HexGrid.to_world(h)
		for i in range(6):
			var a=cells.get(HexGrid.key(h+HexGrid.DIRECTIONS[i]),{})
			var b=cells.get(HexGrid.key(h+HexGrid.DIRECTIONS[(i+1)%6]),{})
			if not shades.has(a.get("id","")) or not shades.has(b.get("id","")):continue
			var ids=[cell.id,a.id,b.id];ids.sort();var key="|".join(ids)
			if seen.has(key):continue
			seen[key]=true
			var pa=HexGrid.to_world(HexGrid.coordinate(a.position));var pb=HexGrid.to_world(HexGrid.coordinate(b.position))
			if not surveyed_grid and not strategic_scale and (not dry_point((p+pa+pb)/3) or not dry_point((p+pa)*.5) or not dry_point((p+pb)*.5) or not dry_point((pa+pb)*.5)):continue
			if crosses_boundary(PackedVector2Array([p,pa,pb])):continue
			# Continental DEM samples support broad relief. Drawing interpolated
			# tactical contour lines across 150 km cells would imply false detail.
			if not strategic_scale and cell.get("elevation_m")!=null and a.get("elevation_m")!=null and b.get("elevation_m")!=null:
				add_contours([p,pa,pb],[elevation_value(cell),elevation_value(a),elevation_value(b)])
			for pair in [[p,cell.id],[pa,a.id],[pb,b.id]]:
				vertices.append(Vector3(pair[0].x,pair[0].y,0));colors.append(shades[pair[1]])
				uvs.append(shade_field.uv(HexGrid.from_world(pair[0])))
	if not vertices.is_empty():
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_TEX_UV]=uvs
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var shaded=Time.get_ticks_usec()
	var candidates: Array=[];var relief_items: Array=[]
	for cell in map.cells:
		if not sampled_land(cell) or cell.get("natural_terrain_id",cell.terrain_id) not in ["hill","mountain","peak"]:continue
		var terrain=cell.get("natural_terrain_id",cell.terrain_id)
		var seed=absi(hash(cell.id));var ridge=terrain in ["mountain","peak"]
		var scale=.94+float(seed%9)/100.0
		var axis=crest_axis(cell)
		var dimensions=(Vector2(176,120) if axis=="ew" else Vector2(116,146)) if ridge else (Vector2(144,94) if axis=="ew" else Vector2(96,116))
		if strategic_scale:dimensions*=.88
		if terrain=="peak":dimensions*=1.10
		dimensions*=scale
		var asset_id=("scenery_ridge_spine_" if ridge else "scenery_foothill_")+axis
		var center=HexGrid.to_world(HexGrid.coordinate(cell.position))+Vector2(float(seed%17)-8.0,(24.0 if ridge else 19.0)+float((seed/17)%13)-6.0)
		var family=("peak" if terrain=="peak" else "ridge" if ridge else "foothill")+"_"+axis
		relief_items.append({"key":cell.id,"cell_id":cell.id,"source_cell":cell,"terrain_id":terrain,"position":center,"bounds":dimensions,"axis":axis,"family":family,"asset_id":asset_id,"rank":relief_value(cell)+elevation_value(cell)*.16+float(seed%23)})
	var choices=MapArtBank.assign(relief_items,270.0) if MapArtBank.available() else {}
	for feature in relief_items:
		# A different silhouette never changes the actual source land class.
		var cell: Dictionary=feature.source_cell
		var terrain=feature.terrain_id;var ridge=terrain in ["mountain","peak"]
		var asset_id=str(choices.get(feature.key,feature.asset_id));var dimensions: Vector2=feature.bounds;var center: Vector2=feature.position
		# The full, unchanged source is drawn around its measured foot anchor.
		# This keeps the visible silhouette consistent between wide and deep
		# sources while reserving the complete image rectangle for coast/path QA.
		var texture_rect=source_rect(asset_id,dimensions)
		var footprint=Rect2(center+texture_rect.position,texture_rect.size)
		var dry=(cell.get("render_land_covered",false) and dry_point(center) and not intersects_index(footprint,boundary_buckets,0)) if surveyed_grid or strategic_scale else dry_footprint(footprint)
		if not dry or intersects_index(footprint,path_buckets.river,9) or intersects_index(footprint,path_buckets.rail,8):continue
		var visual_spacing=(84.0 if ridge else 76.0) if strategic_scale else (83.0 if ridge else 76.0)
		candidates.append({"cell_id":cell.id,"terrain_id":terrain,"position":center,"bounds":dimensions,"texture_rect":texture_rect,"footprint":footprint,"spacing":visual_spacing,"axis":feature.axis,"family":feature.family,"asset_id":asset_id,"rank":feature.rank})
	candidates.sort_custom(func(a,b):return a.rank>b.rank if a.rank!=b.rank else a.cell_id<b.cell_id)
	var occupied: Dictionary={}
	for feature in candidates:
		var bucket=Vector2i(floori(feature.position.x/128),floori(feature.position.y/128));var separated=true
		for x in range(-2,3):
			for y in range(-2,3):
				for other in occupied.get(bucket+Vector2i(x,y),[]):
					if feature.position.distance_to(other.position)<maxf(feature.spacing,other.spacing):separated=false;break
				if not separated:break
			if not separated:break
		if not separated:continue
		if not occupied.has(bucket):occupied[bucket]=[]
		occupied[bucket].append(feature);features.append(feature)
	features.sort_custom(func(a,b):return a.position.y<b.position.y if a.position.y!=b.position.y else a.position.x<b.position.x)
	for index in range(features.size()):
		var feature=features[index]
		var bucket=Vector2i(floori(feature.position.x/512),floori(feature.position.y/512))
		if not feature_buckets.has(bucket):feature_buckets[bucket]=[]
		feature_buckets[bucket].append(index)
		var local_rect: Rect2=feature.texture_rect
		maximum_feature_overhang=maxf(maximum_feature_overhang,maxf(local_rect.position.abs().x,maxf(local_rect.position.abs().y,maxf(local_rect.end.abs().x,local_rect.end.abs().y))))
	diagnostics={"source":(str(map.physical_relief_source) if geographic_gradient else "Natural_Earth_named_relief_corridors_category_shading" if strategic_scale else ("Tilezen_TerrainTiles_geotiff_five_point_samples" if surveyed_grid else "SRTM90m_v3_five_point_samples")),"triangles":vertices.size()/3,"contour_segments":contours.size(),"eligible_features":candidates.size(),"placed_features":features.size(),"preparation_ms":(Time.get_ticks_usec()-started)/1000.0,"index_ms":(indexed-started)/1000.0,"mesh_ms":(shaded-indexed)/1000.0,"placement_ms":(Time.get_ticks_usec()-shaded)/1000.0,"historical_vegetation_claimed":false,"strategic_category_relief":strategic_scale and not geographic_gradient,"geographic_gradient_in_meters":geographic_gradient,"rules_map_mutated":false,"lighting":"continuous_source_height_normals","height_exaggeration_display_only":HEIGHT_EXAGGERATION,"source_meters_per_world_unit":meters_per_world_unit,"crest_axis_from_source_neighbours":true,"generated_continental_contours":false}
	var variants: Dictionary={};var family_counts: Dictionary={}
	for feature in features:
		variants[feature.asset_id]=true
		family_counts[feature.family]=int(family_counts.get(feature.family,0))+1
	diagnostics["independent_relief_originals_used"]=variants.size()
	diagnostics["families"]=family_counts
	diagnostics["nearby_variant_exclusion_world"]=270.0 if MapArtBank.available() else 0.0
	diagnostics["continuous_lighting"]=shade_field.facts()

func visible_features(view: Rect2) -> Array:
	var area=view.grow(maximum_feature_overhang+1.0)
	var indices: Array=[]
	for x in range(floori(area.position.x/512),floori(area.end.x/512)+1):
		for y in range(floori(area.position.y/512),floori(area.end.y/512)+1):
			for index in feature_buckets.get(Vector2i(x,y),[]):
				if view.intersects(features[index].footprint):indices.append(index)
	# Stored indices preserve the exact global foot-depth order of the direct
	# renderer, even when the viewport traverses several spatial buckets.
	indices.sort()
	var result: Array=[]
	for index in indices:result.append(features[index])
	return result

func source_rect(asset_id: String, bounds: Vector2) -> Rect2:
	if not asset_metadata.has(asset_id):return Rect2(Vector2(-bounds.x*.5,-bounds.y),bounds)
	var record: Dictionary=asset_metadata[asset_id];var alpha=record.alpha_bounds
	var occupied_size=Vector2(alpha[2]-alpha[0],alpha[3]-alpha[1])
	var factor=minf(bounds.x/occupied_size.x,bounds.y/occupied_size.y)
	var foot=Vector2((alpha[0]+alpha[2])*.5,alpha[3])*factor
	return Rect2(-foot,Vector2(record.dimensions[0],record.dimensions[1])*factor)

func crest_axis(cell: Dictionary) -> String:
	# A ridge follows the sampled direction with the least height curvature.
	# The three opposite neighbour pairs are sufficient for this symbolic view;
	# this does not claim a surveyed crest line or add a terrain/rules cell.
	var h=HexGrid.coordinate(cell.position);var value=elevation_value(cell)
	var best=INF;var result="ew"
	for index in range(3):
		var a: Dictionary=cells.get(HexGrid.key(h+HexGrid.DIRECTIONS[index]),{})
		var b: Dictionary=cells.get(HexGrid.key(h+HexGrid.DIRECTIONS[index+3]),{})
		if not sampled_land(a) or not sampled_land(b):continue
		var curvature=absf(elevation_value(a)+elevation_value(b)-2*value)
		if curvature<best:
			best=curvature
			var direction=HexGrid.to_world(HexGrid.DIRECTIONS[index])
			result="ns" if absf(direction.y)>absf(direction.x) else "ew"
	return result

func add_contours(points: Array, elevations: Array) -> void:
	var low=minf(elevations[0],minf(elevations[1],elevations[2]));var high=maxf(elevations[0],maxf(elevations[1],elevations[2]))
	if high-low<30:return
	for height in [40,100,250,500,750,1000,1500,2000,3000,4000]:
		if height<=low or height>=high:continue
		var crossings=PackedVector2Array()
		for i in range(3):
			var j=(i+1)%3
			if (elevations[i]<height and elevations[j]>=height) or (elevations[j]<height and elevations[i]>=height):crossings.append(points[i].lerp(points[j],(height-elevations[i])/(elevations[j]-elevations[i])))
		if crossings.size()==2:contours.append(crossings)

func sampled_land(cell: Dictionary) -> bool:
	return not cell.is_empty() and cell.get("region_id")=="theater" and cell.get("natural_terrain_id",cell.get("terrain_id","")) not in ["sea","river","ford","port"] and (cell.get("elevation_m")!=null and cell.get("relief_sample_m")!=null or cell.get("render_land_covered",false))

func elevation_value(cell: Dictionary) -> float:
	if cell.get("elevation_m")!=null:return float(cell.elevation_m)
	# The continental source deliberately stores a named-relief category rather
	# than a false DEM value.  These bands are only for visual hillshade and
	# contour separation; movement and combat never read them as rules numbers.
	return {"plain":18.0,"hill":260.0,"mountain":1250.0,"peak":2600.0}.get(cell.get("natural_terrain_id",cell.get("terrain_id","plain")),18.0)

func relief_value(cell: Dictionary) -> float:
	if cell.get("relief_sample_m")!=null:return float(cell.relief_sample_m)
	return {"plain":10.0,"hill":180.0,"mountain":900.0,"peak":2100.0}.get(cell.get("natural_terrain_id",cell.get("terrain_id","plain")),10.0)

func shade(cell: Dictionary) -> Color:
	var gradient=height_gradient(cell)
	var normal=Vector3(-gradient.x*HEIGHT_EXAGGERATION,-gradient.y*HEIGHT_EXAGGERATION,1).normalized()
	var light=normal.dot(LIGHT_DIRECTION.normalized())
	var flat_light=Vector3(0,0,1).dot(LIGHT_DIRECTION.normalized())
	var rugged=clampf(relief_value(cell)/320.0,0.0,1.0)
	var illumination=clampf(.50+(light-flat_light)*2.1,.04,.96)
	var color=Color("3a5147").lerp(Color("e7e6b8"),illumination)
	# Quiet plains retain their own source material. Sustained relief has
	# continuous lit and shaded slopes, instead of isolated miniature islands.
	color.a=.025+rugged*.34+minf(absf(light-flat_light)*.50,.13)
	if strategic_relief:color.a*=.74
	return color

func height_gradient(cell: Dictionary) -> Vector2:
	var h=HexGrid.coordinate(cell.position);var p=HexGrid.to_world(h)
	var xx=0.0;var xy=0.0;var yy=0.0;var xz=0.0;var yz=0.0
	var step_m=meters_per_world_unit if not strategic_relief else 12.0
	for direction in HexGrid.DIRECTIONS:
		var next=cells.get(HexGrid.key(h+direction),{})
		if not sampled_land(next):continue
		var delta=(HexGrid.to_world(h+direction)-p)*step_m
		if geographic_gradient:
			var average_lat=(float(cell.lat_e6)+float(next.lat_e6))/2000000.0
			delta=Vector2((float(next.lon_e6)-float(cell.lon_e6))/1000000.0*111320.0*cos(deg_to_rad(average_lat)),-(float(next.lat_e6)-float(cell.lat_e6))/1000000.0*111320.0)
		var dz=elevation_value(next)-elevation_value(cell)
		xx+=delta.x*delta.x;xy+=delta.x*delta.y;yy+=delta.y*delta.y
		xz+=delta.x*dz;yz+=delta.y*dz
	var determinant=xx*yy-xy*xy
	if absf(determinant)<.001:return Vector2.ZERO
	return Vector2((yy*xz-xy*yz)/determinant,(xx*yz-xy*xz)/determinant)

func dry_point(point: Vector2) -> bool:
	for index in range(land.size()):
		if not land_bounds[index].has_point(point):continue
		var shape=land[index]
		if not Geometry2D.is_point_in_polygon(point,shape.exterior):continue
		var in_hole=false
		for hole in shape.holes:
			if Geometry2D.is_point_in_polygon(point,hole):in_hole=true;break
		if not in_hole:return true
	return false

func dry_footprint(rect: Rect2) -> bool:
	for x in [0.0,.5,1.0]:
		for y in [0.0,.5,1.0]:
			if not dry_point(rect.position+rect.size*Vector2(x,y)):return false
	return not crosses_boundary(PackedVector2Array([rect.position,Vector2(rect.end.x,rect.position.y),rect.end,Vector2(rect.position.x,rect.end.y)]))

func index_boundary(line: PackedVector2Array) -> void:
	index_path(line,boundary_buckets)

func index_path(line: PackedVector2Array, buckets: Dictionary) -> void:
	for i in range(line.size()-1):
		var bounds=Rect2(line[i],Vector2.ZERO).expand(line[i+1])
		for x in range(floori(bounds.position.x/256),floori(bounds.end.x/256)+1):
			for y in range(floori(bounds.position.y/256),floori(bounds.end.y/256)+1):
				var key=Vector2i(x,y)
				if not buckets.has(key):buckets[key]=[]
				buckets[key].append([line[i],line[i+1]])

func intersects_index(rect: Rect2, buckets: Dictionary, margin: float) -> bool:
	var area=rect.grow(margin)
	var corners=[area.position,Vector2(area.end.x,area.position.y),area.end,Vector2(area.position.x,area.end.y)]
	for x in range(floori(area.position.x/256),floori(area.end.x/256)+1):
		for y in range(floori(area.position.y/256),floori(area.end.y/256)+1):
			for segment in buckets.get(Vector2i(x,y),[]):
				if area.has_point(segment[0]) or area.has_point(segment[1]):return true
				for i in range(4):
					if Geometry2D.segment_intersects_segment(segment[0],segment[1],corners[i],corners[(i+1)%4])!=null:return true
	return false

func crosses_boundary(polygon: PackedVector2Array) -> bool:
	var bounds=Rect2(polygon[0],Vector2.ZERO)
	for point in polygon:bounds=bounds.expand(point)
	for x in range(floori(bounds.position.x/256),floori(bounds.end.x/256)+1):
		for y in range(floori(bounds.position.y/256),floori(bounds.end.y/256)+1):
			for segment in boundary_buckets.get(Vector2i(x,y),[]):
				if Geometry2D.is_point_in_polygon(segment[0],polygon) or Geometry2D.is_point_in_polygon(segment[1],polygon):return true
				for i in range(polygon.size()):
					if Geometry2D.segment_intersects_segment(segment[0],segment[1],polygon[i],polygon[(i+1)%polygon.size()])!=null:return true
	return false

func intersects_paths(rect: Rect2, paths: Array, margin: float) -> bool:
	var area=rect.grow(margin)
	var corners=[area.position,Vector2(area.end.x,area.position.y),area.end,Vector2(area.position.x,area.end.y)]
	for line in paths:
		for i in range(line.size()-1):
			if area.has_point(line[i]) or area.has_point(line[i+1]):return true
			for j in range(4):
				if Geometry2D.segment_intersects_segment(line[i],line[i+1],corners[j],corners[(j+1)%4])!=null:return true
	return false
