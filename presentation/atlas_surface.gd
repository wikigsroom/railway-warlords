class_name AtlasSurface
extends RefCounted

static func build_indexed(source_vertices: Array, source_indices: Array, texture_scale: float) -> Dictionary:
	var vertices=PackedVector3Array();var uv=PackedVector2Array();var indices=PackedInt32Array();var errors: Array=[]
	for point in source_vertices:
		if point.size()!=2 or not is_finite(float(point[0])) or not is_finite(float(point[1])):
			errors.append("invalid_source_vertex");break
		var at=Vector2(point[0],point[1]);vertices.append(Vector3(at.x,at.y,0));uv.append(at/texture_scale)
	if source_indices.size()%3!=0:errors.append("incomplete_source_triangle")
	for value in source_indices:
		var index=int(value)
		if index<0 or index>=vertices.size():errors.append("source_index_out_of_bounds");break
		indices.append(index)
	var mesh: ArrayMesh=null
	if errors.is_empty() and not indices.is_empty():
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_INDEX]=indices
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return {"mesh":mesh,"triangles":indices.size()/3,"errors":errors}

# Surveyed rings can contain tiny islands far from the map origin. Triangulate
# in local coordinates once, then keep the original coordinates in the mesh.
# This avoids cancellation in CanvasItem's per-frame polygon triangulator.
static func build(rings: Array, texture_scale: float) -> Dictionary:
	var vertices=PackedVector3Array();var uv=PackedVector2Array();var indices=PackedInt32Array();var errors: Array=[]
	for ring_index in range(rings.size()):
		var points=PackedVector2Array()
		for point in rings[ring_index]:
			if points.is_empty() or points[-1]!=point:points.append(point)
		if points.size()>1 and points[0]==points[-1]:points.remove_at(points.size()-1)
		if points.size()<3:errors.append(ring_index);continue
		var local=PackedVector2Array();var origin=points[0]
		for point in points:local.append(point-origin)
		var triangles=Geometry2D.triangulate_polygon(local)
		if triangles.is_empty():errors.append(ring_index);continue
		var offset=vertices.size()
		for point in points:vertices.append(Vector3(point.x,point.y,0));uv.append(point/texture_scale)
		for index in triangles:indices.append(offset+index)
	var mesh: ArrayMesh=null
	if not indices.is_empty():
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_INDEX]=indices
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return {"mesh":mesh,"rings":rings.size(),"triangles":indices.size()/3,"errors":errors}
