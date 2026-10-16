extends SceneTree

var checks: Array=[]
var failures: Array=[]
var content=ContentRegistry.new()

func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error("GEOGRAPHY: "+name)

func run() -> void:
	verify(content.load_all(),"load_frozen_geography_and_sources")
	var ids=content.geography_sources.sources.map(func(s):return s.id)
	for map_id in content.maps:
		var map=content.maps[map_id]
		verify(map.sources.all(func(s):return ids.has(s)),map_id+"_all_geography_sources_resolve")
		verify(map.render_extent.size()>=4,map_id+"_geographic_extent_limits_sea_rendering")
		var strategic=bool(map.get("strategic_scale",false))
		if strategic:
			# Physical continental samples replace the former rectangular relief
			# bands; their coarse support and archive must remain explicit.
			verify(str(map.get("geography_status","")).contains("real_natural_earth"),map_id+"_strategic_geometry_status_declared")
			verify(map.cells.all(func(c):return not str(c.get("terrain_source","")).is_empty()),map_id+"_strategic_terrain_source_declared")
			verify(str(map.get("physical_relief_source","")).contains("nine_point_100km") and map.terrain_classification.source_zoom==4,map_id+"_continental_dem_scale_is_explicit")
			verify(map.cells.all(func(c):return c.terrain_id=="sea" or c.elevation_m!=null),map_id+"_all_continental_land_has_archived_dem_elevations")
		else:
			verify(map.cells.all(func(c):return c.terrain_id=="sea" or c.region_id=="restricted" or c.elevation_m!=null),map_id+"_no_unsourced_land_elevations")
		verify(not map.cells.any(func(c):return c.natural_terrain_id=="forest"),map_id+"_no_invented_historical_forest_blocks")
		if strategic:
			verify(map.cells.all(func(c):return c.natural_terrain_id!="hill" or c.relief_sample_m>=400),map_id+"_continental_hills_require_measured_100km_relief")
		else:
			verify(map.cells.all(func(c):return c.natural_terrain_id!="hill" or c.relief_sample_m>=75),map_id+"_flat_highlands_not_automatically_hills")
		if map.admin_layers.is_empty():
			var classification=map.get("terrain_classification",{})
			verify(not bool(classification.get("historical_political_borders_claimed",true)),map_id+"_no_unsupported_admin_border_claim")
		else:
			for year in ["1920","1922","1924"]:
				if not map.admin_layers.has(year):continue
				var names=map.admin_layers[year].map(func(a):return a.name)
				verify(not names.has("河北") and not names.has("辽宁") and not names.has("宁夏") and not names.has("青海"),map_id+"_"+year+"_no_later_province_names")
	var map=content.maps.jingfeng
	var pass_city=map.cities.filter(func(c):return c.id=="jiumenkou")[0]
	verify(abs(pass_city.lat_e6-40116100)<1000 and abs(pass_city.lon_e6-119747500)<1000,"jiumenkou_uses_published_survey_location")
	verify(not map.rail_nodes.any(func(n):return n.city_id=="jiumenkou"),"jiumenkou_is_wall_pass_not_station")
	verify(not map.rail_edges.any(func(e):return e.path_hexes.has(pass_city.position)),"jingfeng_does_not_run_through_jiumenkou_pass")
	verify(content.scenarios.campaign_1924_02.anchor_date=="1924-10-06" and content.scenarios.campaign_1924_02.source_ids.has("bkzx_shanhaiguan_1924"),"jiumenkou_attack_uses_documented_october_window")
	var battle=StateBuilder.create(content,"campaign_1924_02","fengtian",{})
	verify(StateAccess.find(battle,"cities","jiumenkou").owner_id=="zhili" and StateAccess.find(battle,"cities","shanhaiguan").owner_id=="zhili","jiumenkou_and_shanhaiguan_start_under_zhili_defense")
	verify(StateAccess.find(battle,"cities","jinzhou").owner_id=="fengtian" and StateAccess.find(battle,"cities","qinhuangdao").is_empty(),"fengtian_rear_base_is_jinzhou_not_qinhuangdao")
	verify(battle.units.filter(func(u):return u.owner_id=="fengtian" and u.position!=null).all(func(u):return StateAccess.cell(battle,HexGrid.coordinate(u.position)).lon_e6>pass_city.lon_e6),"fengtian_attackers_start_east_of_jiumenkou")
	var defense=StateBuilder.create(content,"campaign_1924_03","zhili",{})
	verify(defense.date=="1924-10-06" and content.scenarios.campaign_1924_03.source_ids.has("bkzx_shanhaiguan_1924"),"shanhaiguan_defense_uses_supported_second_war_window")
	verify(StateAccess.find(defense,"cities","shanhaiguan").owner_id=="zhili" and StateAccess.find(defense,"cities","qinhuangdao").owner_id=="zhili" and StateAccess.find(defense,"cities","jinzhou").owner_id=="fengtian","shanhaiguan_defense_initial_city_control_corrected")
	verify(defense.objectives[0].type=="hold" and StateAccess.at(defense,"units",HexGrid.coordinate(StateAccess.find(defense,"cities","shanhaiguan").position)).owner_id=="zhili","shanhaiguan_is_defended_not_recaptured_from_fictitious_garrison")
	verify(defense.units.filter(func(u):return u.owner_id=="fengtian" and u.position!=null).all(func(u):return StateAccess.cell(defense,HexGrid.coordinate(u.position)).lon_e6>StateAccess.find(defense,"cities","shanhaiguan").lon_e6),"shanhaiguan_fengtian_deployment_is_east_of_pass")
	var jingjin=content.maps.jingjin
	verify(jingjin.cities.filter(func(c):return c.id=="zhuozhou")[0].name=="涿县","republican_zhuoxian_name")
	verify(map.cities.filter(func(c):return c.id=="luanzhou")[0].name=="滦县","republican_luanxian_name")
	verify(ContentRegistry.administration_name(jingjin.cities.filter(func(c):return c.id=="beijing")[0],"1921-06-01")=="京兆地方","jingzhao_independent_of_modern_beijing_province_label")
	verify(ContentRegistry.administration_year("1923-06-01")=="1922","intermediate_year_uses_covered_historical_period")
	verify(ids.has("scsqw_xikang_tunken_1925") and ids.has("guizhou_chuanbian_rename_1925"),"cross_year_region_name_has_archived_primary_sources")
	verify(ContentRegistry.administration_label("川边特别区","1925-01-31")=="川边特别区","chuanbian_name_not_changed_at_arbitrary_new_year")
	verify(ContentRegistry.administration_label("川边特别区","1925-02-06")=="川边地区","unresolved_early_february_uses_geographic_reference")
	verify(ContentRegistry.administration_label("川边特别区","1925-02-07")=="西康特别区","xikang_name_from_attested_february_appointment")
	verify(ContentRegistry.administration_name({"id":"reference","administration_by_year":{"1924":"川边特别区"}},"1926-03-01")=="西康特别区","1924_conquest_cannot_keep_stale_chuanbian_label_into_1926")
	verify(ContentRegistry.administration_label("四川","1926-03-01")=="四川","xikang_update_does_not_relabel_sichuan")
	for id in ["conq_1920","conq_1922"]:
		var state=StateBuilder.create(content,id,"zhili",{})
		verify(StateAccess.find(state,"cities","qingdao").is_empty(),id+"_no_fabricated_chinese_qingdao_garrison")
		var poi=state.map.reference_pois.filter(func(p):return p.id=="qingdao")[0]
		verify(poi.poi_reason=="historical_occupation" and StateAccess.cell(state,HexGrid.coordinate(poi.position)).region_id=="restricted",id+"_occupied_qingdao_is_protected_reference")
		verify(not state.turn_order.has("dongjiang"),id+"_no_premature_sun_chen_opposing_rosters")
		verify(StateAccess.find(state,"cities","changsha").is_empty() and state.map.reference_pois.any(func(p):return p.id=="changsha"),id+"_no_automatic_zhili_control_of_changsha")
	for id in ["conq_1922","conq_1924"]:
		var corrected=StateBuilder.create(content,id,"zhili",{})
		verify(StateAccess.find(corrected,"cities","bengbu").is_empty() and corrected.map.reference_pois.any(func(p):return p.id=="bengbu"),id+"_no_continuous_anhui_clique_bengbu_garrison")
	var early=StateBuilder.create(content,"conq_1920","anhui",{})
	verify(not early.is_empty() and StateAccess.find(early,"cities","bengbu").owner_id=="anhui","1920_anhui_bengbu_retained_in_documented_early_window")
	var state=StateBuilder.create(content,"conq_1922","zhili",{})
	state.date="1922-12-09";TurnRules.round_start(state,content,[])
	verify(StateAccess.find(state,"cities","qingdao").is_empty(),"qingdao_closed_day_before_handover")
	state.date="1922-12-10";var events: Array=[];TurnRules.round_start(state,content,events)
	var qingdao=StateAccess.find(state,"cities","qingdao")
	verify(not qingdao.is_empty() and events.any(func(e):return e.get("name","")=="青岛接收"),"qingdao_opens_at_historical_handover")
	verify(not state.map.reference_pois.any(func(p):return p.id=="qingdao") and StateAccess.cell(state,HexGrid.coordinate(qingdao.position)).region_id!="restricted","handover_updates_render_and_movement_together")
	verify(ContentRegistry.administration_name(qingdao,state.date)=="胶澳商埠","qingdao_administrative_exception_after_handover")
	var edge=state.map.rail_edges.filter(func(e):return e.id.begins_with("jiaoji"))[0]
	verify(not MovementRules.rail_available(state,edge),"city_handover_does_not_prematurely_unlock_rail_military_access")
	state.date="1923-05-01";verify(not MovementRules.rail_available(state,edge),"rail_military_access_closed_before_full_police_handover")
	state.date="1923-05-02";verify(MovementRules.rail_available(state,edge),"rail_military_access_opens_after_full_handover")
	TurnRules.round_start(state,content,[]);verify(state.cities.filter(func(c):return c.id=="qingdao").size()==1,"historical_handover_is_idempotent")
	for map_id in ["hankou","ningpu"]:
		verify(content.maps[map_id].rail_edges.is_empty(),map_id+"_no_anachronistic_cross_yangtze_rail_bridge")
		verify(content.maps[map_id].crossings.all(func(c):return c.kind=="ferry" and not c.rail_allowed),map_id+"_ferries_not_rail_connections")
	var kernel=CommandKernel.new(content)
	var cmd={"type":"EndPhase","actor_id":"zhili","expected_version":state.state_version}
	verify(kernel.resolve(state,cmd).valid,"historical_handover_state_remains_playable")
	var file=FileAccess.open("res://reports/geography_tests.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"checks":checks,"failures":failures,"content_hash":content.content_hash,"scope":"Historical geography and supported date corrections; not a complete archival OOB audit"},"\t"));file.close()
	print("GEOGRAPHY_TESTS ",checks.size()-failures.size()," passed / ",failures.size()," failed");quit(0 if failures.is_empty() else 1)
