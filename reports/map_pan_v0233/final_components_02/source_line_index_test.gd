extends SceneTree

const SourceLines=preload("res://presentation/source_line_index.gd")
var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func intersects_segment(a: Vector2, b: Vector2, view: Rect2) -> bool:
	# Independent segment/rectangle test, including a long crossing whose two
	# endpoints are outside. Culling must never drop a genuinely visible edge.
	if view.has_point(a) or view.has_point(b):return true
	var corners=[view.position,Vector2(view.end.x,view.position.y),view.end,Vector2(view.position.x,view.end.y)]
	for i in 4:
		if Geometry2D.segment_intersects_segment(a,b,corners[i],corners[(i+1)%4])!=null:return true
	return false

func run() -> void:
	var line=PackedVector2Array()
	for i in 1201:line.append(Vector2((i-600)*11.0,sin(i*.031)*340.0+cos(i*.113)*72.0))
	var crossing=PackedVector2Array([Vector2(-9000,-5000),Vector2(9000,5000)])
	var sources=[line,crossing,PackedVector2Array([Vector2(-300,-10),Vector2(-300,210)])]
	var fingerprint=ContentRegistry.fingerprint(sources)
	var helper=SourceLines.new();helper.build(sources)
	for rectangle in [Rect2(-680,-240,500,410),Rect2(50,-180,600,300),Rect2(-12,-12,24,24),Rect2(20000,20000,100,100)]:
		var runs=helper.visible(rectangle);var kept: Dictionary={};var all_original=true
		for run in runs:
			var found=false
			for source in sources:
				var start=source.find(run[0])
				if start>=0 and source.slice(start,start+run.size())==run:found=true;break
			all_original=all_original and found
			for i in range(run.size()-1):kept[str(run[i])+">"+str(run[i+1])]=true
		var covered=true
		for source in sources:
			for i in range(source.size()-1):
				if intersects_segment(source[i],source[i+1],rectangle):covered=covered and kept.has(str(source[i])+">"+str(source[i+1]))
		verify(all_original,"all_kept_runs_retain_exact_original_order_and_vertices_"+str(rectangle))
		verify(covered,"independent_visible_segment_oracle_has_no_missing_crossing_"+str(rectangle))
	verify(helper.visible(Rect2(-12,-12,24,24)).any(func(run):return run==crossing),"long_crossing_with_both_endpoints_outside_remains_visible")
	verify(helper.visible(Rect2(20000,20000,100,100)).is_empty(),"distant_provinces_submit_no_line_vertices")
	var all=helper.visible(Rect2(-20000,-20000,40000,40000))
	verify(all==sources,"adjacent_chunks_coalesce_into_the_whole_source_line_without_duplicate_join_vertices")
	verify(ContentRegistry.fingerprint(sources)==fingerprint,"culling_never_rewrites_source_geography")
	helper.build([PackedVector2Array(),PackedVector2Array([Vector2.ZERO])])
	verify(helper.rows.is_empty(),"map_change_and_degenerate_lines_clear_previous_map_cache")
	var view=MapView.new()
	var edge={"id":"existing_source_rail","path_hexes":[{"q":-5,"r":2},{"q":-2,"r":3},{"q":1,"r":1}]}
	var original=PackedVector2Array()
	for point in edge.path_hexes:original.append(HexGrid.to_world(HexGrid.coordinate(point)))
	var geometry=view.cached_rail_geometry(edge)
	verify(geometry.points==view.rounded_track(original),"rail_cache_retains_the_previous_curve_and_sleeper_phase_vertices")
	verify(view.cached_rail_geometry(edge).index==geometry.index,"rail_damage_and_color_updates_reuse_the_source_geometry")
	edge.path_hexes.append({"q":4,"r":0})
	verify(view.cached_rail_geometry(edge).points!=geometry.points,"a_changed_source_path_never_reuses_stale_rail_geometry")
	view.free()
	var result={"passed":failures.is_empty(),"checks":checks,"failures":failures,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_02/source_line_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"\t"));file.close()
	print("SOURCE_LINE_CHECKS ",checks.size()," passed=",failures.is_empty());quit(0 if failures.is_empty() else 1)
