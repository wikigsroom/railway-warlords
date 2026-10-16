class_name MapHydrography
extends RefCounted

# Archived source lines only. These arrays belong to the presentation cache;
# tributaries never create rule crossings, channels, names or movement costs.
static var catalogs: Dictionary={}

static func symbolic_width(order: int, strategic: bool, fallback: float=1.7) -> float:
	if order<=0:return fallback
	# Stream order controls hierarchy, never the number of vertices in a reach.
	# The same order has the same width on either side of a source junction.
	var width=float([0.0,1.45,1.85,2.4,3.1,4.15,6.8,9.6,13.6,19.2,27.2][clampi(order,1,10)])
	return width*(.82 if strategic else 1.0)

static func primary_width(row: Dictionary, strategic: bool) -> float:
	return symbolic_width(int(row.get("stream_order",0)),strategic,6.8*(.82 if strategic else 1.0))

static func source(name: String) -> Dictionary:
	if not catalogs.has(name):
		var path="res://presentation/data/"+name+".json"
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(path)) if FileAccess.file_exists(path) else {}
		catalogs[name]=parsed if parsed is Dictionary else {}
	return catalogs[name]

static func points_array(raw: Array) -> PackedVector2Array:
	var result=PackedVector2Array()
	for point in raw:result.append(Vector2(float(point[0]),float(point[1])))
	return result

static func rounded_source_corners(points: PackedVector2Array, maximum_cut: float) -> PackedVector2Array:
	# A quadratic fillet stays in the convex hull of the original join. With
	# cuts <=2*D its displacement from the two source segments is <=D. No new
	# junction, endpoint, branch or random meander can be introduced.
	if points.size()<3:return points
	var result=PackedVector2Array([points[0]])
	for index in range(1,points.size()-1):
		var before=points[index-1];var center=points[index];var after=points[index+1]
		var cut=minf(maximum_cut,minf(before.distance_to(center),after.distance_to(center))*.30)
		if cut<.01 or (center-before).normalized().dot((after-center).normalized())>.995:
			result.append(center);continue
		var entry=center+(before-center).normalized()*cut
		var exit=center+(after-center).normalized()*cut;result.append(entry)
		for step in range(1,5):
			var t=float(step)/4.0
			result.append(entry*(1-t)*(1-t)+center*2*(1-t)*t+exit*t*t)
	result.append(points[points.size()-1]);return result

static func detail_row(raw: Dictionary, source_id: String, radius_m: float) -> Dictionary:
	var bounds: Array=raw.get("bounds",[])
	if bounds.size()!=4 or raw.get("points",[]).size()<2:return {}
	var points=points_array(raw.points)
	var display=rounded_source_corners(points,120.0*48.0/maxf(1.0,radius_m)) if raw.has("source_reach_id") else points
	return {"points":points,"display_points":display,"bounds":Rect2(Vector2(bounds[0],bounds[1]),Vector2(bounds[2]-bounds[0],bounds[3]-bounds[1])),"rank":int(raw.get("source_rank",10)),"source_name":str(raw.get("source_name","")),"source_id":source_id,"source_reach_id":int(raw.get("source_reach_id",0)),"stream_order":int(raw.get("stream_order",0)),"min_zoom":float(raw.get("min_zoom",.38)),"width_symbolic":true}

static func main_row(points: PackedVector2Array, order: int, radius_m: float, source_reach_id: int=0, next_down: int=0) -> Dictionary:
	var bounds=Rect2(points[0],Vector2.ZERO) if not points.is_empty() else Rect2()
	for point in points:bounds=bounds.expand(point)
	# Replacement mains receive the same bounded fillet as tributaries.
	var display=rounded_source_corners(points,120.0*48.0/maxf(1,radius_m)) if source_reach_id>0 else points
	return {"points":points,"display_points":display,"bounds":bounds,"stream_order":order,"source_reach_id":source_reach_id,"next_down":next_down,"width_symbolic":true}

static func join_primary_rows(rows: Array) -> int:
	var nodes: Dictionary={};var joined=0
	for row_index in range(rows.size()):
		var row: Dictionary=rows[row_index];var points: PackedVector2Array=row.points
		if points.size()<2 or int(row.source_reach_id)<=0:continue
		for at_start in [true,false]:
			var point=points[0] if at_start else points[-1]
			var away=((points[1] if at_start else points[-2])-point).normalized()
			if not nodes.has(point):nodes[point]=[]
			nodes[point].append({"index":row_index,"start":at_start,"away":away})
	for point in nodes:
		var ends: Array=nodes[point]
		for own in ends:
			var row: Dictionary=rows[own.index]
			for other in ends:
				if own.index==other.index:continue
				var neighbor: Dictionary=rows[other.index]
				var source_link=int(row.next_down)==int(neighbor.source_reach_id) or int(neighbor.next_down)==int(row.source_reach_id)
				if not source_link or row.stream_order!=neighbor.stream_order:continue
				var incoming: Vector2=-other.away if own.start else -own.away
				var outgoing: Vector2=own.away if own.start else other.away
				var normal=(incoming.orthogonal()+outgoing.orthogonal()).normalized()
				if normal.length_squared()<.001:continue
				var miter=minf(1.45,1.0/maxf(.001,absf(normal.dot(outgoing.orthogonal()))))
				row["start_join" if own.start else "end_join"]=normal*miter;joined+=1;break
	return joined

static func build(map: Dictionary, source_map_id: String) -> Dictionary:
	var major: Array=[];var major_orders: Array=[];var major_rows: Array=[];var detail: Array=[]
	var radius=float(map.get("hex_radius_m",1000))
	for line in map.get("render_rivers",[]):
		var points=points_array(line);major.append(points);major_orders.append(0);major_rows.append(main_row(points,0,radius))
	for raw in source("hydrography_detail").get("maps",{}).get(source_map_id,[]):
		var row=detail_row(raw,"natural_earth_rivers_10m",float(map.get("hex_radius_m",1000)))
		if not row.is_empty():detail.append(row)
	# The continental overview has its own primary source geometry. Do not
	# parse thousands of tactical tributaries when it cannot display them.
	var fine={} if map.get("strategic_scale",false) else source("hydrography_fine")
	var replacements: Array=fine.get("major_presentation_replacements",{}).get(source_map_id,[])
	if not replacements.is_empty():
		major.clear();major_orders.clear();major_rows.clear()
		for row in replacements:
			var points=points_array(row.points);var order=int(row.stream_order)
			major.append(points);major_orders.append(order);major_rows.append(main_row(points,order,radius,int(row.source_reach_id),int(row.next_down)))
	var shared_endpoint_frames=join_primary_rows(major_rows)
	var fine_count=0
	for raw in fine.get("maps",{}).get(source_map_id,[]):
		var row=detail_row(raw,str(fine.get("source_id","")),float(map.get("hex_radius_m",1000)))
		if not row.is_empty():detail.append(row);fine_count+=1
	return {"major":major,"major_orders":major_orders,"major_rows":major_rows,"detail":detail,"diagnostics":{"source_map_id":source_map_id,"fine_source_id":fine.get("source_id",""),"fine_source_sha256":fine.get("source_sha256",""),"source_fine_reaches":fine_count,"major_presentation_replacements":replacements.size(),"source_linked_endpoint_frames":shared_endpoint_frames,"rule_geometry_modified":false,"historical_channel_survey":false,"width_is_symbolic":true,"flat_lowland_model_branches_excluded":true,"display_corner_rounding_max_deviation_metres":60.0 if fine_count>0 or not replacements.is_empty() else 0.0,"source_endpoints_preserved":true}}

static func visible(row: Dictionary, view: Rect2, zoom: float, strategic: bool) -> bool:
	if not view.intersects(row.bounds.grow(8)) or zoom<float(row.get("min_zoom",.38)):return false
	return not (strategic and int(row.get("rank",10))>=8 and zoom<.66)

static func spatial_index(rows: Array) -> Dictionary:
	var result: Dictionary={}
	for index in range(rows.size()):
		var area: Rect2=rows[index].bounds.grow(8)
		for x in range(floori(area.position.x/512),floori(area.end.x/512)+1):
			for y in range(floori(area.position.y/512),floori(area.end.y/512)+1):
				var bucket=Vector2i(x,y)
				if not result.has(bucket):result[bucket]=[]
				result[bucket].append(index)
	return result

static func visible_rows(rows: Array, buckets: Dictionary, view: Rect2, zoom: float, strategic: bool) -> Array:
	var indices: Dictionary={};var result: Array=[]
	for x in range(floori(view.position.x/512),floori(view.end.x/512)+1):
		for y in range(floori(view.position.y/512),floori(view.end.y/512)+1):
			for index in buckets.get(Vector2i(x,y),[]):indices[index]=true
	var ordered=indices.keys();ordered.sort()
	for index in ordered:
		if visible(rows[index],view,zoom,strategic):result.append(rows[index])
	return result

static func facts(rows: Array, buckets: Dictionary, diagnostics: Dictionary, view: Rect2, zoom: float, strategic: bool) -> Dictionary:
	var result=diagnostics.duplicate(true);var fine=0;var base=0;var segments=0;var orders: Dictionary={}
	for row in visible_rows(rows,buckets,view,zoom,strategic):
		segments+=row.points.size()-1
		if int(row.get("source_reach_id",0))>0:
			fine+=1;var key=str(row.stream_order);orders[key]=int(orders.get(key,0))+1
		else:base+=1
	result["visible_fine_reaches"]=fine;result["visible_existing_detail_reaches"]=base
	result["visible_detail_segments"]=segments;result["visible_fine_stream_orders"]=orders
	return result
