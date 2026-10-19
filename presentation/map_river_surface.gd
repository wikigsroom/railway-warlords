class_name MapRiverSurface
extends RefCounted

# A cartographic ribbon, not a measured bank polygon. The archived centreline
# and confluences remain authoritative. Source PNGs are sampled in world space.
const TEXTURE_ID=MapWaterMaterials.RIVER_ID
const TEXTURE_PERIOD=256.0
const SMALL_STREAM_LIMIT=3.6
const CROSS_SECTION=[-1.7,-1.2,-1.0,-.60,0.0,.60,1.0,1.2,1.7]
const LIGHT=Vector2(-.55,-.68)

static func cross_color(offset: float, normal: Vector2) -> Color:
	var distance=absf(offset)
	if distance>1.6:return Color(0,0,0,0)
	var illumination=normal.dot(LIGHT.normalized())*signf(offset)
	if distance>1.01:
		return Color(Color("9cac88").lerp(Color("c9c8a2"),.5+illumination*.24),.40-illumination*.12)
	var color=Color("447986") if distance>.9 else Color("508b98") if distance>.4 else Color("6099a3")
	color=color.lightened(maxf(0,illumination)*.04)
	return Color(color,.97)

static func build(source: PackedVector2Array, width: float, start_join: Vector2=Vector2.ZERO, end_join: Vector2=Vector2.ZERO) -> Dictionary:
	var points=PackedVector2Array()
	for point in source:
		if not point.is_finite():return {}
		if points.is_empty() or point.distance_squared_to(points[-1])>.000001:points.append(point)
	if points.size()<2 or width<=0.0 or not is_finite(width):return {}
	var vertices=PackedVector3Array();var colors=PackedColorArray();var uvs=PackedVector2Array()
	var indices=PackedInt32Array();var water_indices=PackedInt32Array();var bank_indices=PackedInt32Array()
	for index in range(points.size()):
		var incoming=(points[index]-points[maxi(0,index-1)]).normalized()
		var outgoing=(points[mini(points.size()-1,index+1)]-points[index]).normalized()
		if index==0:incoming=outgoing
		if index==points.size()-1:outgoing=incoming
		var normal=(incoming.orthogonal()+outgoing.orthogonal()).normalized()
		if normal.length_squared()<.001:normal=outgoing.orthogonal()
		# Bound acute joins so a source hairpin cannot create a long spike.
		var miter=minf(1.45,1.0/maxf(.001,absf(normal.dot(outgoing.orthogonal()))))
		var join=start_join if index==0 else end_join if index==points.size()-1 else Vector2.ZERO
		if not join.is_zero_approx():normal=join.normalized();miter=join.length()
		for offset in CROSS_SECTION:
			var p=points[index]+normal*miter*width*.5*offset
			vertices.append(Vector3(p.x,p.y,0));colors.append(cross_color(offset,normal));uvs.append(p/TEXTURE_PERIOD)
		if index==0:continue
		for band in range(CROSS_SECTION.size()-1):
			var a=(index-1)*CROSS_SECTION.size()+band;var b=index*CROSS_SECTION.size()+band
			var quad=PackedInt32Array([a,b,b+1,a,b+1,a+1]);indices.append_array(quad)
			if band>=2 and band<=5:water_indices.append_array(quad)
			else:bank_indices.append_array(quad)
	var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_TEX_UV]=uvs;arrays[Mesh.ARRAY_INDEX]=indices
	arrays[Mesh.ARRAY_INDEX]=bank_indices
	var banks=ArrayMesh.new();banks.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	arrays[Mesh.ARRAY_INDEX]=water_indices
	var body=ArrayMesh.new();body.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var texture_colors=PackedColorArray();texture_colors.resize(vertices.size());texture_colors.fill(Color(1,1,1,.26))
	arrays[Mesh.ARRAY_COLOR]=texture_colors;arrays[Mesh.ARRAY_INDEX]=water_indices
	var water_uv=uvs.duplicate()
	for index in range(water_uv.size()):water_uv[index].x+=MapWaterMaterials.UV_MARKER
	arrays[Mesh.ARRAY_TEX_UV]=water_uv
	var water=ArrayMesh.new();water.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return {"ribbon":banks,"banks":banks,"body":body,"water":water,"width":width,"source_points":points.size(),"vertices":vertices.size(),"triangles":indices.size()/3,"maximum_half_width":width*.5*1.7*1.45,"world_texture_period":TEXTURE_PERIOD}

static func prepared(row: Dictionary, width: float) -> Dictionary:
	if not row.has("ribbon_cache") or not is_equal_approx(float(row.ribbon_cache.get("width",-1)),width):
		row["ribbon_cache"]=build(row.get("display_points",row.points),width,row.get("start_join",Vector2.ZERO),row.get("end_join",Vector2.ZERO))
	return row.ribbon_cache

static func paint(canvas: CanvasItem, row: Dictionary, width: float, opacity: float, texture: Texture2D, layer: int=0) -> bool:
	if opacity<=0:return false
	if width<SMALL_STREAM_LIMIT:
		var points: PackedVector2Array=row.get("display_points",row.points)
		if points.size()<2:return false
		# Subpixel triangle cores alias in the cached viewport. Native line AA
		# preserves continuous headwaters. A quiet riparian halo and waterbed
		# give the source line depth without inventing banks or a new centreline.
		# Separate passes keep downstream water above every tributary's halo.
		if layer in [0,1]:
			canvas.draw_polyline(points,Color("858b6e",opacity*.13),width+4.2,true)
			canvas.draw_polyline(points,Color("6c816a",opacity*.24),width+2.3,true)
		if layer in [0,2]:
			canvas.draw_polyline(points,Color("3f625f",opacity*.44),width+.6,true)
			canvas.draw_polyline(points,Color("57847f",opacity*.93),width,true)
			canvas.draw_polyline(points,Color("a4beb0",opacity*.34),maxf(.5,width*.30),true)
		return true
	var geometry=prepared(row,width)
	if geometry.is_empty():return false
	if layer in [0,1]:canvas.draw_mesh(geometry.banks,null,Transform2D.IDENTITY,Color(1,1,1,opacity))
	if layer in [0,2]:canvas.draw_mesh(geometry.body,null,Transform2D.IDENTITY,Color(1,1,1,opacity))
	# Tiny headwaters retain a quiet, readable ink width. Wider water receives
	# the same immutable hand-painted texture as the sea, with a shared phase.
	if layer in [0,3] and width>=4 and texture!=null:canvas.draw_mesh(geometry.water,texture,Transform2D.IDENTITY,Color(1,1,1,opacity))
	return true
