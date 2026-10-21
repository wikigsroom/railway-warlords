extends SceneTree

var checks: Array=[]
var failures: Array=[]
var map_facts: Array=[]

func _init() -> void:run.call_deferred()

func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func group() -> Dictionary:
	return {"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}

func run() -> void:
	var regions=MapTerrainSurfaces.geography()
	var supported=0;var unsupported=0;var clips_checked=0
	for id in regions.maps:
		var path="res://content/maps/"+id+".json";var before=FileAccess.get_sha256(path)
		var source: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(path))
		var cells: Dictionary={}
		for cell in source.cells:cells[HexGrid.coordinate(cell.position)]=cell.duplicate(true)
		MapTerrainSurfaces.apply(cells,id)
		var coverage=MapGroundCoverage.for_map(source)
		var details=MapDetails.new();details.ground_families=coverage.families.duplicate();details.ground_clips=coverage.clips
		details.source_ground_coverage=coverage
		var valid=true;var count=0
		for key in details.ground_families:
			var cell: Dictionary=cells.get(HexGrid.from_key(key),{})
			var original_family=str(details.ground_families[key]);var choice=MapTerrainSurfaces.relief_underlay(cell,original_family)
			if choice.is_empty():unsupported+=1;continue
			var region: Dictionary=regions.ecoregions[str(int(cell.presentation_terrain_ecoregion))]
			valid=valid and original_family=="weathered_rock" and int(region.biome) in [4,8]
			valid=valid and cell.get("natural_terrain_id",cell.terrain_id) in ["hill","mountain"]
			valid=valid and choice.family in ["temperate_meadow","subtropical_humus","dry_steppe"] and not choice.historical_landcover_claimed
			valid=valid and choice.rock_opacity>0 and choice.rock_opacity<1
			var changed=cell.duplicate(true);changed["owner_id"]="different_faction";changed["id"]="different_identity"
			valid=valid and choice==MapTerrainSurfaces.relief_underlay(changed,original_family)
			details.relief_underlays[key]=choice.family;details.relief_opacities[key]=choice.rock_opacity
			count+=1;supported+=1
		verify(valid,"actual_underlays_require_existing_relief_and_archived_ecology_independent_of_faction_or_identity:"+id)
		var same_geometry=true;var same_ids=true;var clipped_supported=0
		var original=MapDetails.new();original.source_ground_coverage=coverage;original.ground_families=coverage.families;original.ground_clips=coverage.clips
		for key in coverage.clips:
			var first=group();var base=group();var legacy=group();var h=HexGrid.from_key(key)
			details.append_continuous_ground(first,h,details.ground_family(key))
			details.append_continuous_ground(base,h,details.underlay_family(key),true)
			original.append_continuous_ground(legacy,h,original.ground_family(key))
			same_geometry=same_geometry and first.vertices==legacy.vertices and base.vertices==legacy.vertices and first.uvs==legacy.uvs and base.uvs==legacy.uvs
			for i in first.colors.size():
				var a: Color=first.colors[i];var b: Color=legacy.colors[i]
				same_ids=same_ids and Vector3(a.r,a.g,a.b)==Vector3(b.r,b.g,b.b) and a.a>0 and a.a<=1 and absf(base.colors[i].a-1)<.00001
			if details.needs_relief_underlay(h):clipped_supported+=1
			clips_checked+=1
		verify(same_geometry,"every_clipped_shore_vertex_and_weight_is_identical_in_both_passes_and_original_partition:"+id)
		verify(same_ids,"rock_pass_preserves_source_material_identity_and_both_passes_have_bounded_alpha:"+id)
		verify(FileAccess.get_sha256(path)==before,"geography_elevation_terrain_cities_rivers_and_rules_retain_source_bytes:"+id)
		map_facts.append({"map":id,"supported_underlays":count,"clipped_hexes":coverage.clips.size(),"supported_shore_neighborhoods":clipped_supported})
		await process_frame
	verify(supported>0 and unsupported>supported,"supported_relief_is_used_without_repainting_all_other_regions")
	verify(clips_checked>0,"real_coastal_and_lake_clips_traverse_both_production_passes")
	for cell in [{"terrain_id":"hill"},{"terrain_id":"plain","presentation_terrain_ecoregion":665},{"terrain_id":"peak","presentation_terrain_ecoregion":665}]:
		verify(MapTerrainSurfaces.relief_underlay(cell,"weathered_rock").is_empty(),"missing_ecology_or_noneligible_terrain_is_not_filled:"+str(cell.terrain_id))
	verify(MapTerrainSurfaces.relief_underlay({"terrain_id":"hill","presentation_terrain_ecoregion":665},"alpine_scree").is_empty(),"existing_peak_mineral_material_is_not_replaced")
	var fixture=MapDetails.new();fixture.source_ground_coverage={"synthetic_partition":true}
	for q in range(-4,5):
		for r in range(-4,5):fixture.ground_families[HexGrid.key(Vector2i(q,r))]="temperate_meadow"
	for h in [Vector2i(-1,0),Vector2i.ZERO,Vector2i(1,1)]:
		var key=HexGrid.key(h);fixture.ground_families[key]="weathered_rock";fixture.relief_underlays[key]="temperate_meadow";fixture.relief_opacities[key]=.28 if h.x<0 else .50
	var first=fixture.continuous_macro_meshes(Rect2(-1000,-1000,2000,2000));var repeated=fixture.continuous_macro_meshes(Rect2(-1000,-1000,2000,2000))
	var shared: Dictionary={};var seamless=true;var duplicates=0;var base_seen=false;var overlay_seen=false;var ordered=true
	for batch in first.batches:
		if batch.layer=="relief_underlay":base_seen=true;ordered=ordered and not overlay_seen;continue
		overlay_seen=true
		var arrays=batch.mesh.surface_get_arrays(0);var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
		for i in vertices.size():
			var point=Vector2(vertices[i].x,vertices[i].y)
			if point.length()>180:continue
			var key=Vector2i(roundi(point.x*1000),roundi(point.y*1000))
			if shared.has(key):seamless=seamless and absf(float(shared[key])-colors[i].a)<.00001;duplicates+=1
			else:shared[key]=colors[i].a
	verify(seamless and duplicates>100,"shared_edges_and_three_way_vertices_have_identical_alpha_across_negative_axial_cells")
	verify(base_seen and overlay_seen and ordered,"all_substrates_are_submitted_before_their_mineral_overlays")
	verify(first.count==81 and first.underlay_batches>0,"additional_pass_does_not_double_count_game_hexes")
	verify(repeated.chunks_created==0 and first.batches.map(func(row):return row.mesh.get_instance_id())==repeated.batches.map(func(row):return row.mesh.get_instance_id()),"panning_reuses_both_passes_without_geometry_rebuild_or_source_reselection")
	var empty=fixture.continuous_macro_meshes(Rect2(10000,10000,100,100))
	verify(empty.batches.is_empty() and empty.count==0,"both_passes_cull_together_outside_the_view")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"maps":map_facts,"actual_supported_cells":supported,"clipped_hexes_checked":clips_checked,"new_rasters":0,"historical_rock_cover_measured":false,"formal_art_approval":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_02/component_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RELIEF_GROUNDING_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures,"supported_cells":supported}));quit(0 if failures.is_empty() else 1)
