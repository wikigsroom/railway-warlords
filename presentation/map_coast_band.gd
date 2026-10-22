class_name MapCoastBand
extends RefCounted

# A cartographic transition follows the unchanged source waterline. Actual
# land containment determines which side receives the water-facing wash; the
# colors do not classify beaches, cliffs, bathymetry or historic tidal widths.
# All shores remain a single batch, including numerous small source islands.
const HALF_WIDTH=2.8
const OFFSETS=[-1.0,-.20,0.0,.20,1.0]
const COLORS=[Color(.25,.38,.37,0),Color(.25,.38,.37,.16),Color(.63,.70,.63,.26),Color(.25,.38,.37,.16),Color(.25,.38,.37,0)]
const SIDED_OFFSETS=[-1.8,-.50,0.0,.65,1.8,4.0]
const SIDED_COLORS=[Color(.35,.44,.36,0),Color(.35,.44,.36,.16),Color(.76,.75,.60,.36),Color(.51,.75,.74,.36),Color(.33,.56,.59,.16),Color(.33,.56,.59,0)]
const LIGHT_DIRECTION=Vector2(-.6,-.8)

static func clean_points(raw) -> PackedVector2Array:
	var points=PackedVector2Array()
	for point in raw:
		if points.is_empty() or points[-1].distance_squared_to(point)>.00000001:points.append(point)
	return points

static func ordered_before(a: Vector2, b: Vector2) -> bool:
	return a.x<b.x or (a.x==b.x and a.y<b.y)

static func edge_key(a: Vector2, b: Vector2) -> Vector4:
	return Vector4(a.x,a.y,b.x,b.y) if ordered_before(a,b) else Vector4(b.x,b.y,a.x,a.y)

static func boundary_index(shapes: Array) -> Dictionary:
	# An exact shared source boundary edge determines land/water orientation.
	# Stable scalar-double winding handles reversed exteriors and existing
	# holes. Conflicting duplicate edges are ambiguous and never used as hints.
	var result: Dictionary={}
	for shape in shapes:
		var rings=[{"points":shape.exterior,"hole":false}]
		for hole in shape.holes:rings.append({"points":hole,"hole":true})
		for ring in rings:
			var points=clean_points(ring.points)
			if points.size()>1 and points[0]==points[-1]:points.remove_at(points.size()-1)
			if points.size()<3:continue
			var area=0.0;var origin=points[0];var count=points.size()
			for index in range(count):
				var a=points[index];var b=points[(index+1)%count]
				area+=(float(a.x)-origin.x)*(float(b.y)-origin.y)-(float(a.y)-origin.y)*(float(b.x)-origin.x)
			if absf(area)<.00000001:continue
			var side=(-1 if area>0 else 1)*(-1 if ring.hole else 1)
			for index in range(count):
				var a=points[index];var b=points[(index+1)%count];var key=edge_key(a,b)
				var normalized_side=side*(1 if ordered_before(a,b) else -1)
				if not result.has(key):result[key]=normalized_side
				elif result[key]!=normalized_side:result[key]=0
	return result

static func classify(points: PackedVector2Array, closed: bool, land_query: Callable, boundaries: Dictionary={}) -> Dictionary:
	var result={"side":0,"probes":[],"reason":"no_land_query","matched_source_edges":0}
	if points.size()>=2 and not boundaries.is_empty():
		var candidate=0;var conflict=false;var count=points.size()
		for index in range(count if closed else count-1):
			var a=points[index];var b=points[(index+1)%count]
			var hint=int(boundaries.get(edge_key(a,b),0))
			if hint==0:continue
			var side=hint*(1 if ordered_before(a,b) else -1)
			result.matched_source_edges+=1
			if candidate!=0 and candidate!=side:conflict=true
			candidate=side
		if candidate!=0 and not conflict:
			result.side=candidate;result.reason="exact_source_boundary_edges"
			return result
		# A simplified tiny island can have no exact boundary in the actual land
		# mask. Keep its narrow neutral line instead of thousands of expensive
		# triangle queries or an unsupported assumption about its water side.
		result.reason="source_boundary_conflict_neutral" if conflict else "source_boundary_unmatched_neutral"
		return result
	if not land_query.is_valid() or points.size()<2:return result
	result.reason="no_separating_probe"
	var segments=points.size() if closed else points.size()-1
	var candidates: Array=[];var longest=0;var longest_length=0.0
	for index in range(segments):
		var length=points[index].distance_squared_to(points[(index+1)%points.size()])
		if length>longest_length:longest=index;longest_length=length
	candidates.append(longest)
	for fraction in [0.0,.2,.4,.6,.8,1.0]:
		var index=roundi(float(segments-1)*fraction)
		if not candidates.has(index):candidates.append(index)
	for index in candidates:
		var a=points[index];var b=points[(index+1)%points.size()];var delta=b-a
		if delta.length_squared()<.00000001:continue
		# Use exactly the same normal convention as the mesh cross section.
		var midpoint=(a+b)*.5;var normal=Vector2(-delta.y,delta.x).normalized()
		var distance=clampf(delta.length()*.2,.03,.6)
		var left=midpoint+normal*distance;var right=midpoint-normal*distance
		var left_land=bool(land_query.call(left));var right_land=bool(land_query.call(right))
		result.probes.append({"segment":index,"left":[left.x,left.y],"right":[right.x,right.y],"left_land":left_land,"right_land":right_land})
		if left_land==right_land:continue
		# Each validated source line follows one polygon boundary with a stable
		# orientation. One separating pair resolves that line. Further probes
		# are only fallbacks for a tiny island or a clip-edge numerical ambiguity.
		result.side=-1 if left_land else 1;result.reason="source_land_separates_water"
		return result
	return result

static func closed_width_scale(points: PackedVector2Array, closed: bool) -> float:
	if not closed or points.size()<3:return 1.0
	# A display-only bound prevents a tiny island from becoming a wide halo.
	# 2A/P is derived from the unchanged source ring; it is not a tidal width.
	var twice_area=0.0;var perimeter=0.0;var origin=points[0]
	for index in range(points.size()):
		var a=points[index];var b=points[(index+1)%points.size()]
		twice_area+=(float(a.x)-origin.x)*(float(b.y)-origin.y)-(float(a.y)-origin.y)*(float(b.x)-origin.x)
		perimeter+=a.distance_to(b)
	return minf(1.0,absf(twice_area)/maxf(perimeter,.000001)/16.0)

static func build(lines: Array, land_query: Callable=Callable(), boundaries: Dictionary={}) -> Dictionary:
	var vertices=PackedVector3Array();var colors=PackedColorArray();var indices=PackedInt32Array()
	var started=Time.get_ticks_usec()
	var source_points=0;var source_lines=0;var sided_lines=0;var probes=0;var boundary_lines=0;var clamped_lines=0
	for raw in lines:
		var points=clean_points(raw)
		if points.size()<2:continue
		var closed=points[0].distance_squared_to(points[-1])<.00000001
		if closed:points.remove_at(points.size()-1)
		if points.size()<2:continue
		var orientation=classify(points,closed,land_query,boundaries);var side=int(orientation.side)
		probes+=orientation.probes.size()*2
		if side!=0:sided_lines+=1
		if str(orientation.reason).begins_with("exact_source_"):boundary_lines+=1
		var offsets: Array=SIDED_OFFSETS if side!=0 else OFFSETS
		var palette: Array=SIDED_COLORS if side!=0 else COLORS
		var width=1.0 if side!=0 else HALF_WIDTH;var stride=offsets.size()
		var width_scale=closed_width_scale(points,closed) if side!=0 else 1.0
		if width_scale<1.0:clamped_lines+=1
		var count=points.size();var rows=count+1 if closed else count;var base=vertices.size()
		source_points+=count;source_lines+=1
		for row in range(rows):
			var index=row%count;var before=points[(index-1+count)%count];var after=points[(index+1)%count]
			if not closed:
				if index==0:before=points[0]-(points[1]-points[0])
				if index==count-1:after=points[-1]+(points[-1]-points[-2])
			var incoming=(points[index]-before).normalized();var outgoing=(after-points[index]).normalized()
			var normal=Vector2(-outgoing.y,outgoing.x);var previous=Vector2(-incoming.y,incoming.x)
			var miter=(normal+previous).normalized()
			if miter.length_squared()<.1:miter=normal
			var factor=minf(1.35,1.0/maxf(.001,absf(miter.dot(normal))))
			if side!=0:miter*=float(side)
			var lighting=1.0+.07*miter.dot(LIGHT_DIRECTION) if side!=0 else 1.0
			for cross_section in range(stride):
				var at=points[index]+miter*factor*width*offsets[cross_section]*width_scale
				var pigment: Color=palette[cross_section]
				pigment=Color(pigment.r*lighting,pigment.g*lighting,pigment.b*lighting,pigment.a)
				vertices.append(Vector3(at.x,at.y,0));colors.append(pigment)
			if row>0:
				for band in range(stride-1):
					var a=base+(row-1)*stride+band;var b=base+row*stride+band
					indices.append_array(PackedInt32Array([a,b,a+1,a+1,b,b+1]))
	var mesh: ArrayMesh=null
	if not indices.is_empty():
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=indices
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return {"mesh":mesh,"source_lines":source_lines,"source_points":source_points,"triangles":indices.size()/3,
		"batched_draws":1 if mesh!=null else 0,"half_width_world":HALF_WIDTH,"source_centrelines_modified":false,
		"style":"source_sided_cartographic_water_transition","source_land_classified_lines":sided_lines,
		"exact_source_boundary_classified_lines":boundary_lines,"source_boundary_index_edges":boundaries.size(),
		"neutral_fallback_lines":source_lines-sided_lines,"land_side_probes":probes,"preparation_ms":(Time.get_ticks_usec()-started)/1000.0,
		"nominal_seaward_width_world":4.0,"nominal_landward_width_world":1.8,
		"maximum_classified_seaward_offset_world":5.4,"maximum_classified_landward_offset_world":2.43,
		"maximum_neutral_offset_world":HALF_WIDTH*1.35,"small_closed_source_lines":clamped_lines,"miter_limit":1.35,
		"beach_or_depth_measurement_claimed":false,"light_direction":[LIGHT_DIRECTION.x,LIGHT_DIRECTION.y]}
