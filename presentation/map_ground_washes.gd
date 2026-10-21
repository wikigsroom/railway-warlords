class_name MapGroundWashes
extends RefCounted

# Cached vector triangles, identical to the former per-cell feathered washes.
# This is draw-call batching; no texture, terrain or source class is generated.
var cache: Dictionary={}

func clear() -> void:cache.clear()

func for_bucket(bucket: Vector2i, entries: Array, strategic: bool, zoom: float, depth: bool) -> Dictionary:
	var level=(3 if zoom<.30 else 2 if zoom<.40 else 1) if strategic and not depth else 0
	var key=Vector4i(bucket.x,bucket.y,level,1 if depth else 0)
	if cache.has(key):return cache[key]
	var vertices=PackedVector3Array();var colors=PackedColorArray();var count=0;var bounds=Rect2()
	for entry in entries:
		var kind=str(entry.kind)
		if kind not in (["hill","mountain","peak"] if depth else ["forest","wetland","hill","mountain","peak"]):continue
		if not depth and not TerrainVisuals.keep_at_overview(entry.cell,kind,strategic,zoom):continue
		var center=HexGrid.to_world(entry.hex)+(Vector2(5,7) if depth else Vector2.ZERO)
		var radius=39.0 if depth else 46.8
		var color=Color(.20,.29,.25,.045 if kind=="hill" else .065) if depth else {
			"forest":Color("64855b",.12),"wetland":Color("74928a",.09),"hill":Color("a5ad83",.09),"mountain":Color("758777",.09),"peak":Color("80918c",.09)}[kind]
		var corners=HexGrid.corners(center,radius)
		for index in 6:
			for point in [center,corners[index],corners[(index+1)%6]]:vertices.append(Vector3(point.x,point.y,0))
			colors.append_array(PackedColorArray([color,Color(color,0.0),Color(color,0.0)]))
		var rectangle=Rect2(center-Vector2.ONE*radius,Vector2.ONE*radius*2)
		bounds=rectangle if count==0 else bounds.merge(rectangle);count+=1
	var mesh: ArrayMesh
	if count>0:
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var row={"mesh":mesh,"source_cells":count,"bounds":bounds,"depth":depth}
	cache[key]=row;return row
