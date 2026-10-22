extends SceneTree

var checks: Array=[]
var failures: Array=[]
var output=""

func _init() -> void:
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()-1):
		if args[i]=="--report-output":output=args[i+1]
	run.call_deferred()

func verify(value: bool,name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var path="res://content/maps/asia_strategic.json"
	var before=FileAccess.get_sha256(path)
	var content=ContentRegistry.new();verify(content.load_all(),"full_playable_content_loads")
	var map: Dictionary=content.maps.asia_strategic
	var state_before=ContentRegistry.fingerprint(map)
	var marine=MapCoastGeometry.for_map(map)
	var source: ArrayMesh=MapCoastGeometry.land(marine,768).mesh
	var field=GeographicReliefField.new();field.build(map,source)
	verify(field.mesh!=null and field.image!=null,"source_land_can_receive_detail_without_adjacent_land_rule_hexes")
	if field.mesh==null:quit(1);return
	verify(field.dimensions==Vector2i(3201,1801) and field.facts().node_samples==5765001,"declared_full_asia_node_grid_is_loaded")
	verify(field.image.get_format()==Image.FORMAT_RG8 and not field.image.has_mipmaps(),"numeric_heights_use_linear_rg8_without_art_mip_or_srgb_conversion")
	var probes=JSON.parse_string(FileAccess.get_file_as_string("res://reports/geographic_relief_v0236/source_probes01.json"))
	var exact=true;var native_max_error=0.0;var coordinate_error=0.0
	for probe in probes.probes:
		var height=field.elevation_node(int(probe.node[0]),int(probe.node[1]))
		native_max_error=maxf(native_max_error,absf(height-float(probe.stored_metres)))
		exact=exact and absf(height-float(probe.original_bilinear_metres))<=.50001
		var world=Vector2((float(probe.lon)-20.0)*48.0,(80.0-float(probe.lat))*64.0)
		var uv=field.world_to_uv(world)
		var node=uv*Vector2(field.dimensions)-Vector2(.5,.5)
		coordinate_error=maxf(coordinate_error,node.distance_to(Vector2(probe.node[0],probe.node[1])))
	verify(exact and native_max_error==0,"independent_original_geotiff_probes_survive_decompression_signed_bias_and_native_decode")
	verify(coordinate_error<.001,"east_west_and_north_south_source_nodes_align_at_native_float32_texel_centres")
	verify(field.world_to_uv(Vector2.ZERO).is_equal_approx(Vector2(.5/3201.0,.5/1801.0)),"northwest_endpoint_is_first_texel_centre")
	verify(field.world_to_uv(field.world_extent).is_equal_approx(Vector2(3200.5/3201.0,1800.5/1801.0)),"southeast_endpoint_is_last_texel_centre")
	var mesh_exact=true;var total=0;var tags=true
	for surface in range(source.get_surface_count()):
		var original=source.surface_get_arrays(surface);var actual=field.mesh.surface_get_arrays(surface)
		mesh_exact=mesh_exact and original[Mesh.ARRAY_VERTEX]==actual[Mesh.ARRAY_VERTEX] and original[Mesh.ARRAY_INDEX]==actual[Mesh.ARRAY_INDEX]
		for uv in actual[Mesh.ARRAY_TEX_UV]:tags=tags and uv==Vector2(0,GeographicReliefField.UV_MARKER)
		total+=actual[Mesh.ARRAY_VERTEX].size()
	verify(mesh_exact and total>0,"all_native_land_vertices_indices_islands_and_existing_water_holes_are_reused_exactly")
	verify(tags,"height_mode_uses_a_distinct_exact_mesh_tag")
	var geometry=MapCoastGeometry.land_queries(marine)
	var island_points=[Vector2((137.7-20)*48,(80-36.25)*64),Vector2((135.6-20)*48,(80-34.7)*64),Vector2((133.8-20)*48,(80-33.8)*64)]
	verify(island_points.all(func(p):return MapCoastGeometry.query_land(geometry,p)),"honshu_alps_osaka_and_shikoku_receive_the_same_sourced_land_coverage")
	var signed_filter=true
	for pair in [[-2,2],[-256,256],[255,256],[-1,0],[-10517,6863]]:
		var a=int(pair[0])+32768;var b=int(pair[1])+32768
		for weight in [.1,.25,.5,.75,.9]:
			var r=lerpf(float(a>>8),float(b>>8),weight)
			var g=lerpf(float(a&255),float(b&255),weight)
			var filtered=r*256.0+g-32768.0
			signed_filter=signed_filter and absf(filtered-lerpf(pair[0],pair[1],weight))<.00001
	verify(signed_filter,"biased_channel_filtering_preserves_real_sea_level_and_byte_carry_transitions")
	var no_map=GeographicReliefField.new();no_map.build({"id":"jingjin"},source)
	verify(no_map.mesh==null and no_map.image==null,"unsupported_local_projection_retains_its_existing_surveyed_relief")
	var wrong_projection=map.duplicate(false);wrong_projection.projection="unsupported"
	no_map.build(wrong_projection,source)
	verify(no_map.mesh==null,"unsupported_projection_does_not_display_misregistered_heights")
	verify(ContentRegistry.fingerprint(map)==state_before and FileAccess.get_sha256(path)==before,"presentation_keeps_every_rule_cell_city_rail_and_geographic_source_unchanged")
	verify(HexGrid.RADIUS==48 and int(map.hex_radius_m)==150000,"operation_hex_and_rule_scale_are_unchanged")
	var coastal=MapCoastalControl.for_map(map)
	verify(coastal.get("supplement_cells",0)==915 and coastal.get("source_land_triangles",0)==48181,"coastal_control_supplement_loads_its_archived_real_land_fragments")
	var keys: Dictionary={}
	for cell in map.cells:keys[HexGrid.key(HexGrid.coordinate(cell.position))]=cell
	var omitted_rule_cells=true;var coastal_mesh_finite=true;var native_triangles=0
	for key in coastal.get("field_clips",{}):
		var cell: Dictionary=keys[key]
		omitted_rule_cells=omitted_rule_cells and (not cell.get("render_land_covered",false) or cell.get("natural_terrain_id",cell.terrain_id)=="sea")
		var record: Dictionary=coastal.field_clips[key];var vertices=MapControlLandClip.vertices(record)
		native_triangles+=vertices.size()/3
		coastal_mesh_finite=coastal_mesh_finite and not vertices.is_empty() and vertices.size()%3==0 and record.edges.size()==3
		for vertex in vertices:coastal_mesh_finite=coastal_mesh_finite and vertex.is_finite()
	verify(omitted_rule_cells and native_triangles==48181,"new_control_geometry_only_covers_previously_omitted_rule_cells")
	verify(coastal_mesh_finite,"every_native_coastal_control_triangle_and_clipped_border_is_finite")
	verify(MapCoastalControl.for_map({"id":"jingjin"}).is_empty(),"local_theatre_control_uses_its_existing_geometry")
	var scenario: Dictionary=content.scenarios.asia_1927
	var state=StateBuilder.create(content,"asia_1927",scenario.player_default,{})
	var state_identity=ContentRegistry.fingerprint(state)
	var view=MapView.new();view.size=Vector2(1920,1080);view.setup(content,AssetLibrary.new());view.set_state(state)
	verify(view.territory_field_diagnostics.get("coastal_cells_assigned",0)>0,"ordinary_playable_map_assigns_control_to_source_coastal_fragments")
	var coastal_japan=0
	for key in coastal.field_clips:
		var cell: Dictionary=keys[key]
		if int(cell.lon_e6)>130000000 and int(cell.lon_e6)<142000000 and int(cell.lat_e6)>32000000 and int(cell.lat_e6)<41000000:
			if view.territory_field_cells.has(HexGrid.from_key(key)):coastal_japan+=1
	verify(coastal_japan>=10,"japanese_coastal_land_fragments_no_longer_leave_large_uncoloured_rule_hexes")
	verify(ContentRegistry.fingerprint(state)==state_identity,"coastal_ownership_display_does_not_change_any_playable_state_or_random_stream")
	var coastal_facts=view.territory_field_diagnostics.duplicate(true);view.free()
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,
		"build_version":ContentRegistry.APP_VERSION,"field":field.facts(),"independent_probes":probes.probes.size(),
		"maximum_native_decode_error_m":native_max_error,"maximum_node_coordinate_error":coordinate_error,
		"source_map_sha256":before,"content_hash":content.content_hash,"coastal_control":coastal_facts,
		"coastal_japan_fragments_with_control":coastal_japan,"scope":"Native runtime-normalized numerical source decoding, coordinate alignment, clipped topology and unchanged gameplay state; not physical Android or art approval."}
	if output.is_empty():output="res://reports/geographic_relief_v0236/native_rules.json"
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GEOGRAPHIC_RELIEF_TEST ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
