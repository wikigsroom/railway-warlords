class_name MapCoastBand
extends RefCounted

# A single soft display ribbon follows the unchanged source centreline. It is
# neither a beach-width measurement nor invented cliff/surf geometry. Batching
# avoids three draw calls for each of thousands of small source islands.
const HALF_WIDTH=2.8
const OFFSETS=[-1.0,-.20,0.0,.20,1.0]
const COLORS=[Color(.20,.31,.33,0),Color(.20,.31,.33,.35),Color(.72,.73,.60,.72),Color(.20,.31,.33,.35),Color(.20,.31,.33,0)]

static func build(lines: Array) -> Dictionary:
	var vertices=PackedVector3Array();var colors=PackedColorArray();var indices=PackedInt32Array()
	var source_points=0;var source_lines=0
	for raw in lines:
		var points=PackedVector2Array()
		for point in raw:
			if points.is_empty() or points[-1].distance_squared_to(point)>.00000001:points.append(point)
		if points.size()<2:continue
		var closed=points[0].distance_squared_to(points[-1])<.00000001
		if closed:points.remove_at(points.size()-1)
		if points.size()<2:continue
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
			for cross_section in range(OFFSETS.size()):
				var at=points[index]+miter*factor*HALF_WIDTH*OFFSETS[cross_section]
				vertices.append(Vector3(at.x,at.y,0));colors.append(COLORS[cross_section])
			if row>0:
				for band in range(OFFSETS.size()-1):
					var a=base+(row-1)*OFFSETS.size()+band;var b=base+row*OFFSETS.size()+band
					indices.append_array(PackedInt32Array([a,b,a+1,a+1,b,b+1]))
	var mesh: ArrayMesh=null
	if not indices.is_empty():
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=indices
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return {"mesh":mesh,"source_lines":source_lines,"source_points":source_points,"triangles":indices.size()/3,
		"batched_draws":1 if mesh!=null else 0,"half_width_world":HALF_WIDTH,"source_centrelines_modified":false}
