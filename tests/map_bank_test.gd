extends SceneTree

var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func helper_fixture() -> Dictionary:
	var result={"records":{},"families":{}}
	for family in ["foothill_ew","foothill_ns","ridge_ew","ridge_ns","peak_ew","peak_ns","pine_dense","pine_sparse","deciduous_dense","deciduous_sparse","forest_edge","wetland_reeds","riverbank","shore","rocky_outcrop","meadow","dry_grass","woodland_floor","rocky_ground","wetland_ground","sea_water","county_north_china","capital_north_china","village_south_china"]:
		result.families[family]=[]
		for index in range(48):
			var id="fixture_"+family+"_"+str(index)
			result.families[family].append(id)
			result.records[id]={"dimensions":[1024,768],"alpha_bounds":[96,80,930,700],"category":"scenery","family":family,"variant":index+1}
	return result

func run() -> void:
	var helper_only="--helper-only" in OS.get_cmdline_user_args()
	var geometry_probe="--geometry-probe" in OS.get_cmdline_user_args()
	var actual=MapArtBank.data().duplicate(true)
	if helper_only:MapArtBank.catalog=helper_fixture()
	verify(MapArtBank.available(),"complete_map_bank_metadata_available")
	if not MapArtBank.available():write_report(helper_only);return
	var bank=MapArtBank.data()
	if not helper_only:
		verify(bank.records.size()==804 and bank.additional_count==804 and bank.baseline_count==74 and bank.total_map_assets==878,"74_baseline_plus_804_independent_sources_exceed_tenfold_map_count")
		var counts={"tile":0,"scenery":0,"building":0};var sources: Dictionary={};var resources=true;var metadata=true
		for id in bank.records:
			var row=bank.records[id];counts[row.category]+=1;sources[row.source_sha256]=true
			resources=resources and ResourceLoader.exists("res://assets/%s/%s.png"%[row.category,id])
			metadata=metadata and row.dimensions.size()==2 and row.alpha_bounds.size()==4 and row.alpha_bounds[2]>row.alpha_bounds[0] and row.alpha_bounds[3]>row.alpha_bounds[1]
		verify(counts=={"tile":176,"scenery":480,"building":148},"runtime_counts_are_176_materials_480_scenery_148_settlements")
		verify(sources.size()==804,"every_additional_runtime_record_has_a_unique_original_png_hash")
		verify(resources and metadata,"all_804_whole_source_resources_and_foot_metadata_exist")
		var catalog_ids: Dictionary={}
		for family in bank.families:
			for id in bank.families[family]:catalog_ids[id]=true
		verify(catalog_ids.size()==804 and bank.records.keys().all(func(id):return catalog_ids.has(id)),"every_original_is_addressable_through_a_runtime_family")
		verify(bank.families.village_north_china.size()==26 and bank.families.village_south_china.size()==10,"settlement_extension_expands_actual_campaign_village_silhouettes")
	var items: Array=[]
	for q in range(-8,9):
		for r in range(-8,9):items.append({"key":"%d:%d"%[q,r],"position":HexGrid.to_world(Vector2i(q,r)),"family":"foothill_ew"})
	var before=ContentRegistry.fingerprint(items);var choices=MapArtBank.assign(items,235.0)
	items.reverse();var reversed=MapArtBank.assign(items,235.0)
	verify(ContentRegistry.fingerprint(choices)==ContentRegistry.fingerprint(reversed),"assignment_is_independent_of_iteration_and_viewport_order")
	items.reverse();verify(ContentRegistry.fingerprint(items)==before,"assignment_does_not_mutate_source_candidate_records")
	var collisions=0
	for a in items:
		for b in items:
			if a.key<b.key and a.position.distance_to(b.position)<235 and choices[a.key]==choices[b.key]:collisions+=1
	verify(collisions==0,"no_same_silhouette_within_235_world_units_in_independent_dense_patch")
	var unique: Dictionary={}
	for id in choices.values():unique[id]=true
	verify(unique.size()>=30,"dense_patch_uses_at_least_30_distinct_original_silhouettes")
	var valid_rects=true
	for id in bank.records:
		var row=bank.records[id];var rectangle=MapArtBank.source_rect(id,Vector2(160,120))
		var factor=rectangle.size.x/float(row.dimensions[0]);var alpha=row.alpha_bounds
		var foot=rectangle.position+Vector2((alpha[0]+alpha[2])*.5,alpha[3])*factor
		valid_rects=valid_rects and foot.length()<.001 and absf(rectangle.size.x/rectangle.size.y-float(row.dimensions[0])/row.dimensions[1])<.001
	verify(valid_rects,"all_original_aspects_and_alpha_feet_are_preserved_without_cropping_or_mirroring")
	verify(MapArtBank.material_family({"id":"a","terrain_id":"forest","natural_terrain_id":"plain"})=="woodland_floor" and MapArtBank.material_family({"id":"b","terrain_id":"sea"})=="sea_water" and MapArtBank.material_family({"id":"c","terrain_id":"road","natural_terrain_id":"forest"})=="","materials_follow_real_feature_precedence_and_never_cover_roads_with_woodland")
	var beijing={"id":"beijing","kind":"capital","lon_e6":116407000,"lat_e6":39904000,"owner_id":"qing"}
	var architecture=MapArtBank.settlement_id(beijing,"1900-01-01");beijing.owner_id="japan"
	verify(not architecture.is_empty() and architecture==MapArtBank.settlement_id(beijing,"1900-01-01"),"occupation_never_replaces_a_source_city_architecture")
	verify(MapArtBank.region_for({"id":"seoul"})=="korea" and MapArtBank.region_for({"id":"tokyo"})=="japan" and MapArtBank.region_for({"id":"lhasa"}).is_empty(),"explicit_regional_bindings_do_not_invent_unreviewed_local_reconstructions")
	var detail=MapDetails.new();var hex=Vector2i.ZERO
	var low_bank=detail.eligible_edge_ids("riverbank","plain")
	verify(low_bank.size()==6 and low_bank.all(func(id):return bank.records[id].variant>=1 and bank.records[id].variant<=6),"flat_floodplain_banks_only_use_the_six_visually_reviewed_low_grass_originals")
	verify(detail.eligible_edge_ids("shore","plain").is_empty() and detail.eligible_edge_ids("riverbank","sea").is_empty() and not detail.eligible_edge_ids("shore","hill").is_empty(),"waterline_alone_never_invents_a_rocky_coast_or_rock_hummocks_on_flat_land")
	var marsh_ids=detail.eligible_marsh_ids()
	verify(marsh_ids.size()==18 and marsh_ids.all(func(id):return bank.records[id].variant not in [7,14,15,20,22,23]),"marsh_cells_exclude_the_six_inspected_prominent_rock_mound_outputs")
	var restricted=[{"key":"river_a","family":"riverbank","position":Vector2.ZERO,"candidate_ids":low_bank},{"key":"river_b","family":"riverbank","position":Vector2(20,10),"candidate_ids":low_bank}]
	var restricted_choices=MapArtBank.assign(restricted)
	verify(restricted_choices.values().all(func(id):return id in low_bank) and restricted_choices.river_a!=restricted_choices.river_b,"local_silhouette_exclusion_respects_the_actual_geography_eligible_source_pool")
	detail.surfaces[HexGrid.key(hex)]=MapArtBank.pick("meadow","mesh_fixture")
	var material=detail.surface_meshes([{"hex":hex,"kind":"plain","cell":{"id":"plain","terrain_id":"plain"}}],false)
	verify(material.count==1 and material.batches.size()==1,"feathered_ground_materials_are_batched_by_whole_source_texture")
	var arrays=material.batches[0].mesh.surface_get_arrays(0);var colors=arrays[Mesh.ARRAY_COLOR];var feathered=true
	for index in range(colors.size()):feathered=feathered and (colors[index].a==0 if index%9 in [4,5,7] else colors[index].a>.40)
	verify(arrays[Mesh.ARRAY_VERTEX].size()==54 and feathered,"broad_visible_material_interiors_have_zero_alpha_outer_edges_without_opaque_hex_slabs")
	verify(MapArtBank.material_family({"id":"arbitrary_a","terrain_id":"plain"})==MapArtBank.material_family({"id":"arbitrary_b","terrain_id":"plain"}),"source_geography_not_random_identity_selects_the_ground_material")
	verify(MapArtBank.material_family({"terrain_id":"plain","presentation_surface_family":"sandy_ground"})=="sandy_ground" and MapArtBank.material_family({"terrain_id":"river","presentation_surface_family":"sandy_ground"}).is_empty(),"sourced_sand_material_never_replaces_a_real_river_feature")
	if not helper_only or geometry_probe:
		var content=ContentRegistry.new();verify(content.load_all(),"game_content_loads_with_expanded_bank")
		var recipe=content.scenarios["campaign_1924_03"];var state=StateBuilder.create(content,recipe.id,recipe.player_default,{})
		var initial=ContentRegistry.fingerprint(state);var library=AssetLibrary.new();var view=MapView.new()
		view.size=Vector2(1200,760);view.setup(content,library);view.set_state(state)
		verify(ContentRegistry.fingerprint(state)==initial,"full_map_bank_preparation_preserves_rules_geography_and_combat_random_stream")
		verify(view.map_details.diagnostics.active and view.map_details.surfaces.size()>10000,"expanded_material_families_are_installed_on_the_actual_campaign_map")
		var families: Dictionary={};var ids_used: Dictionary={}
		for feature in view.relief.features:families[feature.family]=true;ids_used[feature.asset_id]=true
		verify(ids_used.size()>=90 and families.size()>=4,"real_campaign_relief_uses_many_independent_hill_and_ridge_sources")
		var culled=true
		for area in [Rect2(15800,6300,1600,1000),Rect2(14000,3200,1000,800),Rect2(3500,1900,1600,1000)]:
			for z in [.27,.60,1.10]:
				var brute=view.map_details.features.filter(func(feature):return z>=feature.min_zoom and area.intersects(feature.footprint))
				culled=culled and ContentRegistry.fingerprint(brute)==ContentRegistry.fingerprint(view.map_details.visible_features(area,z))
		verify(culled,"detail_spatial_culling_matches_independent_whole_footprint_filter_and_depth_order")
		var features_valid=true
		var edge_landforms_valid=true
		for feature in view.map_details.features:
			if feature.source_kind in ["shore","riverbank"]:
				features_valid=features_valid and feature.has("source_vector_position") and feature.position.distance_to(feature.source_vector_position)<=62.001
				edge_landforms_valid=edge_landforms_valid and feature.asset_id in view.map_details.eligible_edge_ids(feature.family,feature.source_terrain)
		verify(features_valid,"shore_and_riverbank_symbols_keep_actual_source_vector_anchors")
		verify(edge_landforms_valid,"actual_campaign_bank_and_coast_symbols_do_not_add_rock_landforms_to_sourced_flat_cells")
		verify(view.map_details.diagnostics.invented_waterways==0 and not view.map_details.diagnostics.rule_cells_changed,"detail_expansion_does_not_invent_waterways_or_change_terrain_rules")
		view.free()
	MapArtBank.catalog=actual
	write_report(helper_only)

func write_report(helper_only: bool) -> void:
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"helper_fixture_only":helper_only,"scope":"Independent original catalog, source-gated presentation, deterministic local diversity, whole-source anchoring and actual campaign integration; formal art approval and physical Android test remain separate."}
	var output="res://reports/map_bank"+("_helper" if helper_only else "")+"_tests.json"
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()-1):
		if args[i]=="--report-output":output=args[i+1]
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_BANK_TEST ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
