class_name MapComposition
extends RefCounted

## Sizes are world units, relative to the existing 48-unit operation hex.
## Models and annotations share these dimensions; geography and hit targets do
## not move when the scene becomes crowded.
const GARRISON_OFFSET=Vector2(22,16)
const CITY_FOOT=Vector2(0,16)

static func settlement_bounds(rank: int) -> Vector2:
	return Vector2(56,44) if rank<=1 else Vector2(68,52) if rank==2 else Vector2(78,60) if rank==3 else Vector2(88,68) if rank==4 else Vector2(100,78)

static func unit_bounds(garrison: bool) -> Vector2:
	return Vector2(62,56) if garrison else Vector2(76,68)

static func alpha_rect(source: Dictionary, texture_rect: Rect2) -> Rect2:
	if source.is_empty():return texture_rect
	var alpha: Array=source.alpha_bounds
	var scale=texture_rect.size.x/float(source.dimensions[0])
	return Rect2(texture_rect.position+Vector2(alpha[0],alpha[1])*scale,Vector2(alpha[2]-alpha[0],alpha[3]-alpha[1])*scale)

static func label_rect(anchor: Vector2, dimensions: Vector2, body: Rect2, obstacles: Array, viewport: Rect2, zoom: float) -> Rect2:
	var gap=8.0/zoom
	var below=Vector2(anchor.x,body.end.y+gap+dimensions.y*.5)
	var above=Vector2(anchor.x,body.position.y-gap-dimensions.y*.5)
	var right=Vector2(body.end.x+gap+dimensions.x*.5,body.get_center().y)
	var left=Vector2(body.position.x-gap-dimensions.x*.5,body.get_center().y)
	var centers=[below,above,right,left]
	# Diagonal and outer alternatives keep key cities reachable in dense ports.
	# Candidate positions never change the historical node or the clickable hex.
	for distance in [28.0,56.0,84.0]:
		for direction in [Vector2(1,1),Vector2(-1,1),Vector2(1,-1),Vector2(-1,-1)]:
			centers.append(anchor+Vector2(direction.x*(dimensions.x*.5+distance/zoom),direction.y*(dimensions.y*.5+(distance+22.0)/zoom)))
	var best=Rect2();var score=INF
	for index in range(centers.size()):
		var rect=Rect2(centers[index]-dimensions*.5,dimensions)
		if not viewport.encloses(rect):continue
		var blocked=false
		for other in obstacles:
			if rect.grow(3.0/zoom).intersects(other):blocked=true;break
		if blocked:continue
		var cost=anchor.distance_squared_to(rect.get_center())+float(index)*8.0/(zoom*zoom)
		# Prefer a short caption below a miniature over a line through its roof.
		if index==0:cost*=.72
		if cost<score:score=cost;best=rect
	return best

static func nearest_edge(rect: Rect2, point: Vector2) -> Vector2:
	return Vector2(clampf(point.x,rect.position.x,rect.end.x),clampf(point.y,rect.position.y,rect.end.y))
