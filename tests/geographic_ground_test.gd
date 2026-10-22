extends SceneTree

var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--report-output")
	var output=args[index+1] if index>=0 else "res://reports/geographic_ground_v0237/native_rules.json"
	var content=ContentRegistry.new();verify(content.load_all(),"actual_playable_content_loads")
	var map: Dictionary=content.maps.asia_strategic
	var before=ContentRegistry.fingerprint(map);var file_before=FileAccess.get_sha256("res://content/maps/asia_strategic.json")
	var source: ArrayMesh=MapCoastGeometry.land(MapCoastGeometry.for_map(map),768).mesh
	var field=GeographicGroundField.new();field.build(map,source)
	verify(field.mesh!=null and field.image!=null,"runtime_normalized_map_loads_geographic_material_field")
	if field.mesh==null:quit(1);return
	var data=JSON.parse_string(FileAccess.get_file_as_string(GeographicGroundField.PATH))
	var probes=JSON.parse_string(FileAccess.get_file_as_string("res://reports/geographic_ground_v0237/source_probes01.json"))
	verify(probes.data_sha256==data.classification_source_json_sha256,"native_probes_are_bound_to_the_all_node_primary_polygon_audit")
	verify(field.dimensions==Vector2i(1601,901) and field.image.get_format()==Image.FORMAT_R8 and not field.image.has_mipmaps(),"categorical_ids_use_exact_numeric_r8_without_art_mipmaps")
	var exact=true
	for probe in probes.probes:
		var value=roundi(field.image.get_pixel(int(probe.node[0]),int(probe.node[1])).r*255.0)
		exact=exact and value==int(probe.family_index_plus_one)
	verify(exact and probes.probes.size()>6000,"native_source_ids_match_audited_primary_polygon_probes_including_unknown_water")
	verify(field.weight_images.size()==20 and field.weight_dimensions==Vector2i(801,451),"all_twenty_family_weight_layers_have_declared_dimensions")
	var valid_images=true
	for image in field.weight_images:valid_images=valid_images and image.get_format()==Image.FORMAT_R8 and image.get_size()==field.weight_dimensions and not image.has_mipmaps()
	verify(valid_images,"mixing_weights_are_linear_numeric_channels_not_recoloured_art")
	var sums_valid=true;var sums_seen=0;var maximum_sum_error=0.0
	for y in range(0,451,7):
		for x in range(0,801,11):
			var sum=0.0
			for image in field.weight_images:sum+=image.get_pixel(x,y).r
			if sum>.001:maximum_sum_error=maxf(maximum_sum_error,absf(sum-1.0));sums_seen+=1
			sums_valid=sums_valid and (sum<.001 or absf(sum-1.0)<=.025)
	verify(sums_valid and sums_seen>1000,"quantized_weight_sums_remain_bounded_and_are_renormalized_by_renderer")
	var exact_mesh=true;var tags=true;var vertices=0
	for surface in source.get_surface_count():
		var original=source.surface_get_arrays(surface);var actual=field.mesh.surface_get_arrays(surface)
		exact_mesh=exact_mesh and original[Mesh.ARRAY_VERTEX]==actual[Mesh.ARRAY_VERTEX] and original[Mesh.ARRAY_INDEX]==actual[Mesh.ARRAY_INDEX]
		for uv in actual[Mesh.ARRAY_TEX_UV]:tags=tags and uv==Vector2(0,GeographicGroundField.UV_MARKER)
		vertices+=actual[Mesh.ARRAY_VERTEX].size()
	verify(exact_mesh and vertices>100000,"material_pass_reuses_all_source_islands_coasts_and_existing_lake_holes_exactly")
	verify(tags,"geographic_material_pass_has_its_own_exact_mesh_mode")
	var unsupported=GeographicGroundField.new();unsupported.build({"id":"jingjin"},source)
	verify(unsupported.mesh==null and unsupported.image==null,"local_map_projection_retains_existing_materials")
	var wrong_projection=map.duplicate(false);wrong_projection.projection="not_equirectangular"
	unsupported.build(wrong_projection,source)
	verify(unsupported.mesh==null,"misregistered_projection_is_rejected")
	field.bind_to(null)
	verify(ContentRegistry.fingerprint(map)==before and FileAccess.get_sha256("res://content/maps/asia_strategic.json")==file_before,"all_movement_terrain_elevations_cities_rivers_ownership_and_gameplay_random_state_stay_unchanged")
	verify(HexGrid.RADIUS==48 and int(map.hex_radius_m)==150000,"operation_hex_size_is_preserved")
	verify(not field.facts().historical_landuse_survey and not field.facts().trees_or_water_added,"representative_ground_does_not_claim_historical_landcover")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"field":field.facts(),
		"primary_source_probes":probes.probes.size(),"maximum_quantized_weight_sum_error":maximum_sum_error,
		"source_map_sha256":file_before,"content_hash":content.content_hash,"shipping_exe":false,
		"physical_android_device_tested":false,"formal_art_approval":false}
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GEOGRAPHIC_GROUND_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
