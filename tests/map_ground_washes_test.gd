extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func run() -> void:
	var helper=MapGroundWashes.new();var entries: Array=[]
	for i in 7:
		var kind=["plain","sea","forest","wetland","hill","mountain","peak"][i]
		entries.append({"kind":kind,"hex":Vector2i(i-8,-4),"cell":{"id":"sourced_"+str(i),"terrain_id":kind}})
	var before=ContentRegistry.fingerprint(entries)
	var row=helper.for_bucket(Vector2i(-1,-1),entries,false,1.05,false)
	var arrays=row.mesh.surface_get_arrays(0);var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
	var area=0.0;var contact=true;var normal_count=0;var transparent_count=0
	for i in range(0,vertices.size(),3):
		var a=vertices[i];var b=vertices[i+1];var c=vertices[i+2]
		area+=absf(Vector2(b.x-a.x,b.y-a.y).cross(Vector2(c.x-a.x,c.y-a.y)))*.5
		contact=contact and absf(a.z)+absf(b.z)+absf(c.z)<.00001 and colors[i].a>0 and colors[i+1].a==0 and colors[i+2].a==0
		normal_count+=1;transparent_count+=2
	verify(row.source_cells==5 and vertices.size()==5*18,"all_five_existing_detail_classes_keep_six_triangles_while_plain_and_sea_stay_clear")
	verify(absf(area-5.0*3.0*sqrt(3.0)*pow(46.8,2)*.5)<.1,"batch_area_matches_independent_regular_hex_area_without_new_ground_coverage")
	verify(contact and transparent_count==normal_count*2,"every_source_class_wash_retains_opaque_centre_and_transparent_perimeter")
	verify(helper.for_bucket(Vector2i(-1,-1),entries,false,.42,false).mesh==row.mesh,"tactical_zoom_changes_reuse_the_same_world_fixed_wash_mesh")
	var depth=helper.for_bucket(Vector2i(-1,-1),entries,false,1.05,true)
	var points: PackedVector3Array=depth.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var anchors=true
	for i in 3:
		var expected=HexGrid.to_world(entries[i+4].hex)+Vector2(5,7)
		anchors=anchors and Vector2(points[i*18].x,points[i*18].y).distance_to(expected)<.001
	verify(depth.source_cells==3 and anchors,"only_existing_relief_receives_the_original_directional_contact_shadow_at_its_actual_anchor")
	var shallow=helper.for_bucket(Vector2i(-1,-1),entries,true,.29,false)
	var medium=helper.for_bucket(Vector2i(-1,-1),entries,true,.39,false)
	verify(helper.for_bucket(Vector2i(-1,-1),entries,true,.21,false).mesh==shallow.mesh,"continental_sparse_zoom_band_reuses_its_own_mesh")
	verify(helper.for_bucket(Vector2i(-1,-1),entries,true,.31,false).mesh==medium.mesh,"continental_medium_zoom_band_is_separate_and_stable")
	verify(ContentRegistry.fingerprint(entries)==before,"batching_preserves_all_source_cells_classes_and_geographic_positions")
	helper.clear();verify(helper.cache.is_empty(),"loading_another_map_clears_old_geographic_meshes")
	var empty=helper.for_bucket(Vector2i.ZERO,entries.slice(0,2),false,1.0,false)
	verify(empty.mesh==null and empty.source_cells==0,"empty_detail_buckets_allocate_no_gpu_mesh")
	var contours=[PackedVector2Array([Vector2(-700,-520),Vector2(700,520)]),PackedVector2Array([Vector2(-512,0),Vector2(-510,8)]),PackedVector2Array([Vector2(511,511),Vector2(514,514)]),PackedVector2Array([Vector2(100,100),Vector2(105,102)])]
	var lines=MapContourLines.new();var source=ContentRegistry.fingerprint(contours);lines.build(contours)
	var expected: Dictionary={};var owners: Dictionary={}
	for segment in contours:expected[ContentRegistry.fingerprint(segment)]=true
	for bucket in lines.buckets.values():
		for i in range(0,bucket.points.size(),2):
			var key=ContentRegistry.fingerprint(PackedVector2Array([bucket.points[i],bucket.points[i+1]]))
			owners[key]=int(owners.get(key,0))+1
	verify(owners.size()==expected.size() and owners.keys().all(func(key):return expected.has(key) and owners[key]==1),"every_unchanged_contour_segment_has_exactly_one_mesh_owner_including_bucket_crossings")
	var preserved=true
	for view in [Rect2(-800,-600,1600,1200),Rect2(-720,-540,40,40),Rect2(-520,-10,20,30),Rect2(500,500,20,20),Rect2(90,90,40,40),Rect2(8000,8000,100,100)]:
		var submitted: Dictionary={}
		for batch in lines.batches(view,1.05):
			for i in range(0,batch.source_points.size(),2):submitted[ContentRegistry.fingerprint(PackedVector2Array([batch.source_points[i],batch.source_points[i+1]]))]=true
		for segment in contours:
			if view.has_point(segment[0]) or view.has_point(segment[1]):preserved=preserved and submitted.has(ContentRegistry.fingerprint(segment))
	verify(preserved,"visible_source_endpoints_are_never_lost_by_midpoint_bucket_culling_or_negative_coordinates")
	var geometry=true
	for zoom in [.20,.65,1.05,2.40]:
		var mesh=MapContourLines.make_mesh(contours[0],zoom);var data=mesh.surface_get_arrays(0)
		var v: PackedVector3Array=data[Mesh.ARRAY_VERTEX];var uv: PackedVector2Array=data[Mesh.ARRAY_TEX_UV]
		var left=(Vector2(v[0].x,v[0].y)+Vector2(v[5].x,v[5].y))*.5
		var right=(Vector2(v[1].x,v[1].y)+Vector2(v[2].x,v[2].y))*.5
		var start=uv[0].y-1024.0;var end=uv[1].y-1024.0;var delta=(right-left)/(end-start)
		geometry=geometry and (left-delta*start).distance_to(contours[0][0])<.3 and (left+delta*(1.0-start)).distance_to(contours[0][1])<.3
		geometry=geometry and absf(Vector2(v[1].x-v[2].x,v[1].y-v[2].y).length()*zoom-2.65)<.002
	var view=Rect2(-800,-600,1600,1200);var first=lines.batches(view,1.05);var second=lines.batches(view,1.05)
	verify(geometry,"inverse_render_coordinates_recover_original_endpoints_and_constant_screen_width_at_four_zooms")
	verify(first.map(func(row):return row.mesh.get_instance_id())==second.map(func(row):return row.mesh.get_instance_id()),"panning_reuses_contour_meshes_without_rebuilding_strokes")
	verify(ContentRegistry.fingerprint(contours)==source,"drawing_bands_do_not_smooth_reposition_or_add_source_contours")
	lines.build([])
	verify(lines.buckets.is_empty() and lines.cache.is_empty() and lines.batches(view,1.05).is_empty(),"maps_without_contours_do_not_retain_previous_map_lines")
	var report={"passed":failures.is_empty(),"build_version":ContentRegistry.APP_VERSION,"checks":checks,"failures":failures,"scope":"Vector geometry, source order, alpha falloff, spatial index and cache invariants. Native pixel and performance evidence is separate."}
	var file=FileAccess.open("res://reports/relief_grounding_v0232/batching_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_WASH_BATCH_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
