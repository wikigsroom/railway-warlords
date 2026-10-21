class_name MapContourLines
extends RefCounted

# One owner per unchanged source segment. The mesh is only its antialiased
# drawing band, with world-fixed endpoints and a constant screen-space width.
var buckets: Dictionary={}
var cache: Dictionary={}
var cached_zoom=-1.0
var overhang=0.0
var source_segments=0
const WIDTH_PIXELS=.65
const FRINGE_PIXELS=1.0

func build(contours: Array) -> void:
	buckets.clear();cache.clear();cached_zoom=-1;overhang=0;source_segments=contours.size()
	for segment in contours:
		var a: Vector2=segment[0];var b: Vector2=segment[1];var midpoint=(a+b)*.5
		var key=Vector2i(floori(midpoint.x/512.0),floori(midpoint.y/512.0))
		var bounds=Rect2(a,Vector2.ZERO).expand(b)
		if not buckets.has(key):buckets[key]={"points":PackedVector2Array(),"bounds":bounds}
		buckets[key].points.append_array(segment);buckets[key].bounds=buckets[key].bounds.merge(bounds)
		overhang=maxf(overhang,a.distance_to(b)*.5)

func batches(view: Rect2, zoom: float) -> Array:
	if not is_equal_approx(cached_zoom,zoom):cache.clear();cached_zoom=zoom
	var padding=overhang+(WIDTH_PIXELS*.5+FRINGE_PIXELS)/zoom
	var area=view.grow(padding);var result: Array=[]
	var low=Vector2i(floori(area.position.x/512.0),floori(area.position.y/512.0))
	var high=Vector2i(floori(area.end.x/512.0),floori(area.end.y/512.0))
	for x in range(low.x,high.x+1):
		for y in range(low.y,high.y+1):
			var key=Vector2i(x,y)
			if not buckets.has(key) or not view.intersects(buckets[key].bounds.grow(padding)):continue
			if not cache.has(key):cache[key]={"mesh":make_mesh(buckets[key].points,zoom),"source_points":buckets[key].points}
			if cache[key].mesh!=null:result.append(cache[key])
	return result

static func make_mesh(points: PackedVector2Array, zoom: float) -> ArrayMesh:
	var vertices=PackedVector3Array();var uvs=PackedVector2Array();var colors=PackedColorArray()
	var half=(WIDTH_PIXELS*.5+FRINGE_PIXELS)/zoom
	for index in range(0,points.size(),2):
		var a=points[index];var b=points[index+1];var length=a.distance_to(b)
		if length<=.00001:continue
		var axis=(b-a)/length;var normal=axis.orthogonal()*half;var cap=minf(FRINGE_PIXELS/zoom,length*.25)
		var quad=[a-axis*cap+normal,b+axis*cap+normal,b+axis*cap-normal,a-axis*cap-normal]
		var start=-cap/length;var end=1.0+cap/length
		var uv=[Vector2(1,1024+start),Vector2(1,1024+end),Vector2(-1,1024+end),Vector2(-1,1024+start)]
		for corner in [0,1,2,0,2,3]:
			vertices.append(Vector3(quad[corner].x,quad[corner].y,0));uvs.append(uv[corner]);colors.append(Color(.36,.33,.25,.20))
	if vertices.is_empty():return null
	var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=uvs;arrays[Mesh.ARRAY_COLOR]=colors
	var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);return mesh
