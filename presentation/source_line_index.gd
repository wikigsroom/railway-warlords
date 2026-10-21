extends RefCounted

# Cull source segments without moving, resampling, or smoothing their vertices.
# Consecutive visible chunks remain one polyline, preserving interior joins.
const SEGMENTS_PER_CHUNK=32
var rows: Array=[]
var enabled=true

func build(lines: Array) -> void:
	rows.clear()
	for points in lines:
		if points.size()<2:continue
		var chunks: Array=[]
		for start in range(0,points.size()-1,SEGMENTS_PER_CHUNK):
			var end=mini(start+SEGMENTS_PER_CHUNK,points.size()-1)
			var bounds=Rect2(points[start],Vector2.ZERO)
			for i in range(start+1,end+1):bounds=bounds.expand(points[i])
			chunks.append({"start":start,"end":end,"bounds":bounds.grow(.001)})
		rows.append({"points":points,"chunks":chunks})

func visible(view: Rect2) -> Array:
	var result: Array=[]
	for row in rows:
		var points: PackedVector2Array=row.points
		if not enabled:result.append(points);continue
		var start=-1;var end=-1
		for chunk in row.chunks:
			if view.intersects(chunk.bounds):
				if start<0:start=chunk.start
				end=chunk.end
			elif start>=0:
				result.append(points.slice(start,end+1));start=-1
		if start>=0:result.append(points.slice(start,end+1))
	return result
