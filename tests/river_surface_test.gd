extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func distance_to_source(point: Vector2, source: PackedVector2Array) -> float:
	var result=INF
	for index in range(source.size()-1):
		result=minf(result,point.distance_to(Geometry2D.get_closest_point_to_segment(point,source[index],source[index+1])))
	return result

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"content_loads_with_continuous_water_renderer")
	var replacement_checks=0
	for map_id in content.maps:
		var map: Dictionary=content.maps[map_id];var before=ContentRegistry.fingerprint(map)
		var hydro=MapHydrography.build(map,map_id)
		var raw_ok=hydro.major_rows.size()==hydro.major.size();var endpoints=true;var bounded=true
		for index in range(hydro.major_rows.size()):
			var row: Dictionary=hydro.major_rows[index];var points: PackedVector2Array=row.points;var display: PackedVector2Array=row.display_points
			raw_ok=raw_ok and points==hydro.major[index]
			endpoints=endpoints and not display.is_empty() and display[0]==points[0] and display[-1]==points[-1]
			if row.source_reach_id>0:
				replacement_checks+=1
				for point in display:bounded=bounded and distance_to_source(point,points)<=60.0*48.0/float(map.hex_radius_m)+.0001
			else:bounded=bounded and display==points
		verify(raw_ok,"all_primary_source_arrays_retained:"+map_id)
		verify(endpoints,"all_primary_source_confluences_and_endpoints_retained:"+map_id)
		verify(bounded,"primary_display_is_original_or_within_existing_60m_bound:"+map_id)
		verify(ContentRegistry.fingerprint(map)==before,"river_preparation_leaves_rules_crossings_and_history_immutable:"+map_id)
	verify(replacement_checks==31,"all_31_yangtze_replacement_reaches_receive_bounded_display_geometry")
	var connected=0;var sections_match=true
	for map_id in ["hankou","ningpu"]:
		var rows: Array=MapHydrography.build(content.maps[map_id],map_id).major_rows
		for row in rows:
			for at_start in [true,false]:
				if not row.has("start_join" if at_start else "end_join"):continue
				var at: Vector2=row.points[0] if at_start else row.points[-1];var counterpart_found=false
				var own=MapRiverSurface.prepared(row,MapHydrography.primary_width(row,false)).banks.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
				var section=own.slice(0,9) if at_start else own.slice(own.size()-9)
				for other in rows:
					if row==other or row.stream_order!=other.stream_order:continue
					if row.next_down!=other.source_reach_id and other.next_down!=row.source_reach_id:continue
					for other_start in [true,false]:
						if (other.points[0] if other_start else other.points[-1])!=at:continue
						var other_vertices=MapRiverSurface.prepared(other,MapHydrography.primary_width(other,false)).banks.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
						var other_section=other_vertices.slice(0,9) if other_start else other_vertices.slice(other_vertices.size()-9)
						for vertex in section:
							var found=false
							for candidate in other_section:found=found or vertex.is_equal_approx(candidate)
							sections_match=sections_match and found
						counterpart_found=true;connected+=1
				sections_match=sections_match and counterpart_found
	verify(connected>0 and sections_match,"real_same_order_upstream_downstream_joins_share_exact_drawn_cross_sections")
	var separate=[MapHydrography.main_row(PackedVector2Array([Vector2.ZERO,Vector2(10,0)]),9,1250,1,2),MapHydrography.main_row(PackedVector2Array([Vector2(10.05,0),Vector2(30,10)]),9,1250,2,3)]
	verify(MapHydrography.join_primary_rows(separate)==0,"nearby_source_endpoints_are_never_snapped_or_given_fabricated_connections")
	var unlinked=[MapHydrography.main_row(PackedVector2Array([Vector2.ZERO,Vector2(10,0)]),9,1250,1,0),MapHydrography.main_row(PackedVector2Array([Vector2(10,0),Vector2(30,10)]),9,1250,2,0)]
	verify(MapHydrography.join_primary_rows(unlinked)==0,"coincident_endpoints_without_source_topology_cannot_acquire_a_guessed_join")
	var short={"points":PackedVector2Array([Vector2.ZERO,Vector2(60,0)]),"stream_order":0}
	var dense=short.duplicate(true);dense.points=PackedVector2Array()
	for i in range(101):dense.points.append(Vector2(i*.6,0))
	verify(is_equal_approx(MapHydrography.primary_width(short,false),MapHydrography.primary_width(dense,false)),"resampling_identical_river_cannot_change_symbolic_width")
	verify(MapRiverSurface.build(PackedVector2Array(),6).is_empty() and MapRiverSurface.build(PackedVector2Array([Vector2.ZERO]),6).is_empty(),"empty_and_single_point_sources_do_not_create_water")
	verify(MapRiverSurface.build(short.points,0).is_empty() and MapRiverSurface.build(short.points,-1).is_empty(),"invalid_widths_cannot_generate_geometry")
	var paths=[PackedVector2Array([Vector2(-150,-90),Vector2(-20,-90),Vector2(70,-35),Vector2(110,50)]),PackedVector2Array([Vector2.ZERO,Vector2.ZERO,Vector2(60,0),Vector2(60.1,.01),Vector2(12,1)])]
	for path_index in range(paths.size()):
		var source: PackedVector2Array=paths[path_index];var raw=source.duplicate();var result=MapRiverSurface.build(source,8)
		verify(not result.is_empty() and source==raw,"ribbon_preserves_source_with_negative_positions_or_duplicate_joins:"+str(path_index))
		var arrays=result.ribbon.surface_get_arrays(0);var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var uvs: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV];var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
		var finite=true;var phase=true;var contained=true;var feather=false;var core=false
		for i in range(vertices.size()):
			var point=Vector2(vertices[i].x,vertices[i].y)
			finite=finite and point.is_finite() and is_finite(colors[i].a)
			phase=phase and uvs[i].is_equal_approx(point/256.0)
			contained=contained and distance_to_source(point,source)<=8*.5*1.7*1.45+.0001
			feather=feather or colors[i].a==0;core=core or colors[i].a>.9
		verify(finite and contained,"acute_join_has_finite_geometry_and_bounded_symbolic_banks:"+str(path_index))
		verify(phase,"actual_mesh_world_uvs_keep_shared_phase_at_negative_coordinates:"+str(path_index))
		verify(feather and core,"ribbon_contains_soft_outer_edge_and_readable_water_core:"+str(path_index))
		var row={"points":source};var first=MapRiverSurface.prepared(row,8);var again=MapRiverSurface.prepared(row,8)
		verify(first.ribbon.get_instance_id()==again.ribbon.get_instance_id(),"unchanged_selection_reuses_real_mesh_resource:"+str(path_index))
		var changed=MapRiverSurface.prepared(row,9)
		verify(changed.ribbon.get_instance_id()!=first.ribbon.get_instance_id() and row.points==raw,"width_change_invalidates_only_presentation_geometry:"+str(path_index))
	var forward=MapRiverSurface.build(short.points,8).ribbon.surface_get_arrays(0)
	var reversed_points: PackedVector2Array=short.points.duplicate();reversed_points.reverse()
	var backward=MapRiverSurface.build(reversed_points,8).ribbon.surface_get_arrays(0)
	var lighting=true
	for i in range(forward[Mesh.ARRAY_VERTEX].size()):
		var match_index=backward[Mesh.ARRAY_VERTEX].find(forward[Mesh.ARRAY_VERTEX][i])
		lighting=lighting and match_index>=0
		if match_index>=0:lighting=lighting and forward[Mesh.ARRAY_COLOR][i].is_equal_approx(backward[Mesh.ARRAY_COLOR][match_index])
	verify(lighting,"source_direction_cannot_flip_world_light_or_bank_shading")
	var layered=MapRiverSurface.build(short.points,8)
	var bank_arrays=layered.banks.surface_get_arrays(0);var body_arrays=layered.body.surface_get_arrays(0)
	var bank_outside=true;var body_inside=true
	for index in bank_arrays[Mesh.ARRAY_INDEX]:
		var v: Vector3=bank_arrays[Mesh.ARRAY_VERTEX][index]
		bank_outside=bank_outside and distance_to_source(Vector2(v.x,v.y),short.points)>=4-.0001
	for index in body_arrays[Mesh.ARRAY_INDEX]:
		var v: Vector3=body_arrays[Mesh.ARRAY_VERTEX][index]
		body_inside=body_inside and distance_to_source(Vector2(v.x,v.y),short.points)<=4+.0001
	verify(bank_outside and body_inside,"actual_bank_and_water_indices_are_separate_for_confluence_passes")
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"replacement_reaches_checked":replacement_checks,"scope":"Actual source geometry, bounded display mains, mesh joins, world UV phase, cache lifetime and authoritative-state isolation; not measured riverbanks or historical-channel certification."}
	var file=FileAccess.open("res://reports/river_surface_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RIVER_SURFACE_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
