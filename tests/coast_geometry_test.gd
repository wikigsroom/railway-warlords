extends SceneTree

var checks: Array=[]
var failures: Array=[]
var evidence: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var truth=JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/coast_land_query_truth.json"))
	var content=ContentRegistry.new();verify(content.load_all() and not truth.production_compiler_imported and truth.maps.size()==4,"current_native_content_and_independent_land_fixture_load")
	for id in ["jingfeng","jingjin","conquest_china","asia_strategic"]:
		var map: Dictionary=content.maps[id];var before=ContentRegistry.fingerprint(map)
		var started=Time.get_ticks_usec();var row=MapCoastGeometry.for_map(map);var result=MapCoastGeometry.land(row,768)
		verify(not row.is_empty() and row.map_sha256==FileAccess.get_sha256("res://content/maps/"+id+".json") and truth.maps[id].map_sha256==row.map_sha256,"actual_source_map_hash:"+id)
		verify(not result.is_empty() and result.mesh!=null and result.errors.is_empty(),"precompiled_source_mesh_loads_without_ear_clipping:"+id)
		if result.is_empty() or result.mesh==null:continue
		var arrays=result.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX];var uv: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV]
		var source_vertices=true;var source_indices=true;var world_uv=true;var finite=true;var area=0.0
		for i in range(vertices.size()):
			var expected=Vector2(row.vertices[i][0],row.vertices[i][1]);var actual=Vector2(vertices[i].x,vertices[i].y)
			source_vertices=source_vertices and actual==expected
			world_uv=world_uv and uv[i].distance_to(expected/768)<.00001
			finite=finite and is_finite(actual.x) and is_finite(actual.y)
		for i in range(indices.size()):source_indices=source_indices and indices[i]==int(row.indices[i])
		for i in range(0,indices.size(),3):
			var a=vertices[indices[i]];var b=vertices[indices[i+1]];var c=vertices[indices[i+2]]
			area+=absf((b-a).cross(c-a).z)*.5
		verify(vertices.size()==row.vertices.size() and source_vertices and finite,"actual_native_mesh_keeps_every_source_vertex:"+id)
		verify(indices.size()==row.indices.size() and source_indices,"actual_native_mesh_keeps_source_triangle_indices:"+id)
		verify(absf(area-float(row.source_land_area))<maxf(.1,float(row.source_land_area)*.000001),"native_float_mesh_area_preserves_land_and_water_holes:"+id)
		verify(world_uv,"whole_ground_texture_phase_is_world_anchored:"+id)
		verify(result.mesh==MapCoastGeometry.land(MapCoastGeometry.for_map(map),768).mesh,"same_map_reuses_prepared_mesh:"+id)
		var lines: Array=[]
		for source in map.render_coast:
			var points=PackedVector2Array()
			for xy in source:points.append(Vector2(xy[0],xy[1]))
			lines.append(points)
		var band=MapCoastBand.build(lines)
		verify(band.mesh!=null and band.source_lines==lines.size() and band.batched_draws==1,"thousands_of_source_shores_share_one_display_batch:"+id)
		var view=MapView.new();view.state={"map":map,"date":"1924-10-06"};view.prepare_administration(false)
		var expected_lines=row.get("administration_lines",{}).get(ContentRegistry.administration_year("1924-10-06"),[])
		verify(view.region_lines.size()==expected_lines.size(),"map_view_uses_source_land_clipped_administrative_lines:"+id);view.free()
		if id!="asia_strategic":
			var places=HistoricalPlaces.new();places.prepare(map,"1924-10-06")
			verify(not places.zones.is_empty() and places.zones.all(func(zone):return zone.get("land_clipped",false)),"shipping_city_influence_uses_source_land_clipped_meshes:"+id)
		var shapes: Array=[]
		for shape in map.render_land:
			shapes.append({"exterior":PackedVector2Array(shape.exterior.map(func(p):return Vector2(p[0],p[1]))),"holes":shape.holes.map(func(hole):return PackedVector2Array(hole.map(func(p):return Vector2(p[0],p[1]))))})
		var relief=AtlasRelief.new();relief.prepare_land_queries(shapes)
		relief.land_mesh_queries=MapCoastGeometry.land_queries(row)
		var probes: Array=truth.maps[id].points
		var classifications=true
		for probe in probes:
			var point=Vector2(probe[0],probe[1]);var expected: bool=probe[2]
			var direct=relief.source_dry_point(point);var cached=relief.dry_point(point);var repeated=relief.dry_point(point)
			classifications=classifications and direct==expected and cached==expected and repeated==expected
		verify(classifications,"direct_and_cached_land_match_independent_GEOS_at_cells_and_shores:"+id)
		verify(relief.uniform_land_queries.keys().all(func(key):return not relief.boundary_buckets.has(key)),"source_coast_and_hole_squares_never_use_uniform_land_cache:"+id)
		verify(relief.uniform_land_query_hits>0 and not relief.uniform_land_queries.is_empty(),"repeated_exact_interior_queries_reuse_constant_land_classification:"+id)
		verify(ContentRegistry.fingerprint(map)==before,"coast_preparation_keeps_all_rules_and_source_fields_immutable:"+id)
		evidence.append({"map_id":id,"source_polygons":row.source_land_polygons,"source_coast_vertices":row.coast_vertices,"land_triangles":result.triangles,
			"native_area_error":absf(area-float(row.source_land_area)),"band_triangles":band.triangles,"exact_land_query_probes":probes.size(),"uniform_query_hits":relief.uniform_land_query_hits,"preparation_ms":(Time.get_ticks_usec()-started)/1000.0})
	verify(MapCoastGeometry.loaded_id=="asia_strategic","cache_retains_only_the_most_recent_map")
	for id in ["hankou","ningpu"]:verify(MapCoastGeometry.for_map(content.maps[id]).is_empty(),"inland_map_keeps_existing_water_geometry:"+id)
	var invalid=AtlasSurface.build_indexed([[0,0],[2,0],[0,2]],[0,1,9],768)
	verify(invalid.mesh==null and not invalid.errors.is_empty(),"invalid_source_triangle_is_rejected_before_gpu_upload")
	var fixture={"id":"unrelated_fixture","physical_detail_source":"gshhg_marine_2_3_7"}
	verify(MapCoastGeometry.for_map(fixture,"jingfeng").is_empty(),"unrelated_fixture_cannot_borrow_a_production_coast_mesh")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"maps":evidence,"formal_art_approval":false,"historical_coast_survey_approval":false}
	var file=FileAccess.open("res://reports/coast_geometry_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("COAST_GEOMETRY_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"maps":evidence}));quit(0 if report.passed else 1)
