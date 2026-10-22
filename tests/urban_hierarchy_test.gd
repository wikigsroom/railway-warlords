extends SceneTree

var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var content=ContentRegistry.new()
	verify(content.load_all(),"production_content_loads")
	var active:Dictionary=MapArtBank.data().get("urban_active_families",{})
	verify(active.size()==4,"north_south_city_and_capital_families_have_explicit_bindings")
	var sources={};var uids={}
	for family in active:
		verify(active[family].size()==2,"two_independent_whole_sources:"+family)
		for id in active[family]:
			var row:Dictionary=MapArtBank.data().records[id]
			sources[row.source_sha256]=true
			var path="res://assets/building/"+id+".png"
			var image=load(path) as Texture2D
			verify(image!=null and image.get_width()<=384 and image.get_height()<=384,"native_import_within_city_memory_budget:"+id)
			var uid=ResourceLoader.get_resource_uid(path)
			verify(uid!=-1 and not uids.has(uid),"unique_normal_engine_import_identity:"+id)
			uids[uid]=true
			var bounds=Vector2(100,78) if family.begins_with("capital_") else Vector2(88,68)
			var rect=MapArtBank.source_rect(id,bounds)
			var body=MapComposition.alpha_rect(row,rect)
			verify(body.size.x<=bounds.x+.001 and body.size.y<=bounds.y+.001 and absf(body.end.y)<.001,
				"visible_model_fits_existing_rank_bounds_and_foot:"+id)
			verify(absf(rect.size.aspect()-float(row.dimensions[0])/row.dimensions[1])<.001,
				"whole_original_aspect_preserved:"+id)
	verify(sources.size()==8,"eight_unique_originals_no_recoloured_variants")
	var tianjin=StateAccess.find({"cities":content.maps.jingjin.cities},"cities","tianjin")
	verify(MapArtBank.settlement_family(tianjin,"1924-10-01")=="capital_north_china" and MapArtBank.settlement_family(tianjin,"1925-01-01")=="city_north_china",
		"tianjin_uses_dated_province_seat_role_not_a_permanent_capital_symbol")
	verify(MapArtBank.settlement_family({"id":"tokyo","kind":"city"},"1924-01-01")=="county_japan" and MapArtBank.settlement_family({"id":"lhasa","kind":"city"},"1924-01-01").is_empty(),
		"unproduced_regional_city_families_do_not_invent_local_architecture")
	var shijiazhuang=StateAccess.find({"cities":content.maps.conquest_china.cities},"cities","shijiazhuang")
	verify(not shijiazhuang.is_empty() and MapArtBank.settlement_family(shijiazhuang,"1924-01-01")=="market_north_china",
		"historical_market_is_not_upgraded_to_a_modern_large_city")
	for scenario_id in ["legion_07","legion_08","campaign_1924_05"]:
		var recipe=content.scenarios[scenario_id]
		var state=StateBuilder.create(content,scenario_id,recipe.player_default,{})
		var initial=ContentRegistry.fingerprint(state)
		var view=MapView.new();view.size=Vector2(1920,1080)
		view.setup(content,AssetLibrary.new());view.set_state(state)
		verify(ContentRegistry.fingerprint(state)==initial,"presentation_preserves_rules_geography_and_random_stream:"+scenario_id)
		var expected={"hankou":"city_south_china","hanyang":"county_south_china","wuchang":"capital_south_china"} if scenario_id=="legion_07" else {"nanjing":"capital_south_china"} if scenario_id=="legion_08" else {"beijing":"capital_north_china"}
		for city_id in expected:
			var city=StateAccess.find(state,"cities",city_id)
			if city.is_empty():verify(false,"mandatory_city_in_real_scenario:"+city_id);continue
			var visual=view.city_visual_record(city)
			verify(visual.asset_id in MapArtBank.ids(expected[city_id]),"real_city_draw_respects_historical_rank_and_region:"+city_id)
			var occupied=city.duplicate(true);occupied.owner_id="japan"
			verify(view.city_visual_record(occupied).asset_id==visual.asset_id,"occupation_keeps_source_architecture:"+city_id)
			if expected[city_id].begins_with("city_"):
				var station=city.duplicate(true);station.buildings=[{"def_id":"station","level":1,"damaged":false}]
				verify(EconomyRules.building_level(station,"station")==1 and view.city_visual_record(station).asset_id==visual.asset_id,
					"station_rules_remain_without_replacing_primary_urban_model:"+city_id)
		var choices=ContentRegistry.fingerprint(view.settlement_choices)
		view.camera+=Vector2(100,60);view.zoom=.32;view.prepare_place_sprites()
		verify(ContentRegistry.fingerprint(view.settlement_choices)==choices,"pan_zoom_and_reprepare_do_not_shuffle_whole_sources:"+scenario_id)
		if scenario_id=="legion_07":
			verify(view.settlement_choices["hankou:"]!=view.settlement_choices["hanyang:"],"urban_hankou_and_county_hanyang_retain_distinct_historical_ranks")
			var city=StateAccess.find(state,"cities","hankou")
			view.camera=HexGrid.to_world(HexGrid.coordinate(city.position));view.zoom=1.05
			var facts=view.map_bank_capture_facts()
			verify(facts.settlement_sources.get("hankou","")==view.city_visual_record(city).asset_id,"capture_metadata_reports_the_actual_drawn_urban_source")
			view.zoom=.32;view.selected_city_id=""
			verify(not view.map_bank_capture_facts().settlement_sources.has("hankou"),"regional_counter_does_not_claim_an_undrawn_city_model")
			verify(view.separate_harbor(city) and view.harbor_visual_record(city).asset_id not in active.city_south_china,
				"source_harbor_stays_separate_from_the_primary_city")
		view.free()
	verify(HexGrid.RADIUS==48 and MapComposition.unit_bounds(false)==Vector2(76,68) and MapComposition.settlement_bounds(4)==Vector2(88,68),
		"operation_grid_unit_size_and_city_size_are_preserved")
	var output="res://reports/urban_hierarchy_v0235/rules_tests.json"
	var args=OS.get_cmdline_user_args()
	for i in range(args.size()-1):
		if args[i]=="--report-output":output=args[i+1]
	var file=FileAccess.open(output,FileAccess.WRITE)
	file.store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,
		"physical_android_device_tested":false,"formal_art_approval":false},"\t"));file.close()
	print("URBAN_HIERARCHY_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}))
	quit(0 if failures.is_empty() else 1)
