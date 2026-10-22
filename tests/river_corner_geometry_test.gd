extends SceneTree

var checks: Array=[]
var failures: Array=[]
var output=""
var revised=false

func _init() -> void:
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()):
		if args[i]=="--require-rounded-profile":revised=true
		if args[i]=="--report-output" and i+1<args.size():output=args[i+1]
	run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func pairs(points: PackedVector2Array) -> Array:
	var result: Array=[]
	for p in points:result.append([p.x,p.y])
	return result

func largest_turn(points: PackedVector2Array) -> float:
	var result=0.0
	for i in range(1,points.size()-1):
		var a=points[i]-points[i-1];var b=points[i+1]-points[i]
		if a.length_squared()<.000001 or b.length_squared()<.000001:continue
		result=maxf(result,rad_to_deg(acos(clampf(a.normalized().dot(b.normalized()),-1,1))))
	return result

func run() -> void:
	if output.is_empty():push_error("A new report path is required");quit(1);return
	var content=ContentRegistry.new();verify(content.load_all(),"native_content_loads")
	var rows: Array=[];var map_fingerprints: Dictionary={};var fixtures: Array=[]
	var raw_preserved=true;var endpoints=true;var finite=true
	for map_id in content.maps:
		var map: Dictionary=content.maps[map_id];var before=ContentRegistry.fingerprint(map)
		var hydro=MapHydrography.build(map,map_id);var radius=float(map.hex_radius_m)
		for role in ["major_rows","detail"]:
			var index=0
			for row in hydro[role]:
				var source: PackedVector2Array=row.points;var display: PackedVector2Array=row.display_points
				endpoints=endpoints and display[0]==source[0] and display[-1]==source[-1]
				for point in display:finite=finite and point.is_finite()
				rows.append({"map":map_id,"role":role,"index":index,"source_reach_id":row.source_reach_id,
					"source":pairs(source),"display":pairs(display),"radius_m":radius,
					"budget_m":60.0 if row.source_reach_id>0 else 0.0})
				index+=1
		raw_preserved=raw_preserved and before==ContentRegistry.fingerprint(map)
		map_fingerprints[map_id]=before
	verify(raw_preserved,"all_six_rule_maps_unchanged_after_actual_hydrography_preparation")
	verify(endpoints,"all_actual_reach_endpoints_remain_exact")
	verify(finite,"all_actual_display_points_are_finite")
	var originals_unchanged=true;var reversed_equivalent=true
	for degrees in range(-175,176,5):
		if degrees==0:continue
		var angle=deg_to_rad(float(degrees))
		var source=PackedVector2Array([Vector2(-100,0),Vector2.ZERO,Vector2(cos(angle),sin(angle))*100])
		var original=source.duplicate()
		var display=MapHydrography.rounded_source_corners(source,5.0 if revised else 10.0)
		var reverse=source.duplicate();reverse.reverse()
		var backward=MapHydrography.rounded_source_corners(reverse,5.0 if revised else 10.0);backward.reverse()
		originals_unchanged=originals_unchanged and source==original
		reversed_equivalent=reversed_equivalent and backward.size()==display.size()
		if backward.size()==display.size():
			for i in range(display.size()):reversed_equivalent=reversed_equivalent and display[i].distance_to(backward[i])<.0001
		fixtures.append({"angle_degrees":degrees,"budget_world":5.0,"source":pairs(source),"display":pairs(display),"maximum_turn_degrees":largest_turn(display)})
	verify(originals_unchanged,"acute_obtuse_and_reverse_turn_fixtures_do_not_mutate_sources")
	verify(reversed_equivalent,"reversing_source_order_preserves_the_same_curve_geometry")
	var right=PackedVector2Array([Vector2(-100,0),Vector2.ZERO,Vector2(0,100)])
	var right_display=MapHydrography.rounded_source_corners(right,5.0 if revised else 10.0)
	var right_turn=largest_turn(right_display)
	if revised:
		verify(right_turn<16.0,"right_angle_has_no_residual_polyline_turn_of_sixteen_degrees_or_more")
		verify(MapHydrography.rounded_source_corners(right,0)==right,"zero_deviation_budget_preserves_the_entire_original")
		verify(MapHydrography.rounded_source_corners(right,-1)==right,"negative_budget_cannot_create_geometry")
	for count in [0,1,2]:
		var source=PackedVector2Array()
		for i in range(count):source.append(Vector2(i*10,-i*3))
		verify(MapHydrography.rounded_source_corners(source,5)==source,"short_source_remains_exact:"+str(count))
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,
		"native_content_hash":content.content_hash,"development_geometry_dump":true,"revised_profile_required":revised,
		"right_angle_maximum_turn_degrees":right_turn,"map_fingerprints":map_fingerprints,"rows":rows,"fixtures":fixtures,
		"scope":"Actual native source/display arrays for independent GEOS distance, source and topology comparison. No raster processing, shipping claim or historical channel survey."}
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report));file.close()
	print("RIVER_CORNER_GEOMETRY ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"actual_rows":rows.size(),"right_angle_turn":right_turn}))
	quit(0 if failures.is_empty() else 1)
