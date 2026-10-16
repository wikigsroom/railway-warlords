extends SceneTree

var content=ContentRegistry.new()
var checks:Array=[]
var failures:Array=[]

func _init() -> void:
	run.call_deferred()

func verify(ok: bool, id: String) -> void:
	checks.append({"id":id,"passed":ok})
	if not ok:
		failures.append(id);push_error("ASIA_CONTENT: "+id)

func run() -> void:
	verify(content.load_all(),"content_loads_with_asia_catalog")
	var timeline=content.read_json("res://content/history/asia_timeline.json")
	var oob=content.read_json("res://content/history/asia_order_of_battle.json")
	var source_ids=[]
	for source in timeline.get("sources",[]):source_ids.append(str(source.id))
	verify(source_ids.size()>=19,"asia_source_registry_complete")
	var ids=["asia_1840","asia_1860","asia_1890","asia_1900","asia_1917","asia_1927","asia_1940"]
	for id in ids:
		var record=timeline.get("timelines",[]).filter(func(v):return v.id==id)
		verify(record.size()==1,id+"_timeline_record")
		if record.is_empty():continue
		verify(content.scenarios.has(id),id+"_free_world_scenario")
		verify(record[0].anchor_date==content.scenarios[id].anchor_date,id+"_anchor_date_matches_scenario")
		for conflict in record[0].conflicts:
			verify(conflict.province_scope.size()<=3,conflict.id+"_scope_at_most_three_provinces")
			for source in conflict.source_ids:verify(source_ids.has(source),conflict.id+"_source_resolves_"+str(source))
	var map=content.maps.get("asia_strategic",{})
	verify(not map.is_empty(),"asia_map_loaded")
	verify(map.cells.size()>=6500 and map.cells.size()<=9000,"asia_map_cell_capacity")
	verify(map.cities.size()>=75,"asia_real_city_nodes")
	verify(map.geographic_bounds==[20,-10,180,80],"asia_realistic_geographic_bounds")
	verify(map.render_land.size()>100 and map.render_rivers.size()>20,"asia_physical_geometry_present")
	verify(map.cells.all(func(c):return c.region_id=="theater"),"asia_cells_are_playable_theater")
	var city_ids={}
	for city in map.cities:
		verify(not city_ids.has(city.id),"unique_city_"+str(city.id));city_ids[city.id]=true
		verify(city.lon_e6>=20000000 and city.lon_e6<=180000000 and city.lat_e6>=-10000000 and city.lat_e6<=80000000,"city_coordinate_in_asia_"+str(city.id))
		verify(city.reference_owner_by_scenario.size()==7,"city_has_seven_timeline_owners_"+str(city.id))
	var control_corrections={
		"asia_1840":{"taipei":"qing","hong_kong":"qing","shanghai":"qing","ningbo":"qing","macau":"portugal","rangoon":"burmese_kingdom","mandalay":"burmese_kingdom","lahore":"sikh_empire"},
		"asia_1860":{"taipei":"qing","saigon":"french_empire","rangoon":"british_india","mandalay":"burmese_kingdom","lahore":"british_india"},
		"asia_1890":{"taipei":"qing","hong_kong":"british_empire","macau":"portugal","hanoi":"french_empire","rangoon":"british_india","lahore":"british_india"},
		"asia_1900":{"qingdao":"germany","port_arthur":"russian_empire","dalian":"russian_empire","manila":"usa","macau":"portugal"},
		"asia_1917":{"hong_kong":"british_empire","macau":"portugal","taipei":"japan","seoul":"japan","manila":"usa"},
		"asia_1927":{"qingdao":"fengtian","hong_kong":"british_empire","macau":"portugal","taipei":"japan","seoul":"japan","manila":"usa"},
		"asia_1940":{"taipei":"japanese_occupied","seoul":"japanese_occupied","manila":"usa","hong_kong":"british_empire","macau":"portugal"}
	}
	for scenario_id in control_corrections:
		for city_id in control_corrections[scenario_id]:
			var corrected=map.cities.filter(func(c):return c.id==city_id)
			verify(corrected.size()==1 and corrected[0].reference_owner_by_scenario.get(scenario_id,"")==control_corrections[scenario_id][city_id],scenario_id+"_historical_control_"+city_id)
	for formation in oob.get("formations",[]):
		verify(not formation.source_ids.is_empty(),"formation_has_source_"+str(formation.id))
		verify(formation.strength_min<=formation.strength_max,"formation_range_order_"+str(formation.id))
		for source in formation.source_ids:verify(source_ids.has(source),"formation_source_resolves_"+str(formation.id)+"_"+str(source))
	verify(oob.get("formations",[]).size()>=30,"asia_order_of_battle_has_named_formations")
	for id in ids:
		var playable=content.playable_factions(id)
		verify(playable.size()>=2,id+"_has_two_playable_factions")
		var year=int(str(content.scenarios[id].anchor_date).substr(0,4))
		var roster=content.scenarios[id].get("equipment_whitelist",[])
		verify(roster.size()>0,id+"_period_equipment_roster_present")
		for equipment_id in roster:
			var equipment_def=content.definition("units",str(equipment_id))
			verify(year>=int(equipment_def.get("historical_era_min",0)),id+"_no_anachronistic_equipment_"+str(equipment_id))
		if not playable.is_empty():
			var state=StateBuilder.create(content,id,playable[0],{})
			verify(not state.is_empty(),id+"_state_builds")
			verify(state.play_mode=="free_world",id+"_free_world_runtime_flag")
			for faction in state.factions:
				verify(faction.equipment_whitelist.all(func(e):return year>=int(content.definition("units",str(e)).get("historical_era_min",0))),id+"_runtime_faction_period_roster_"+str(faction.id))
			for city in map.cities:
				var historical_owner=str(city.reference_owner_by_scenario.get(id,""))
				verify(state.turn_order.has(historical_owner),id+"_city_owner_in_runtime_roster_"+str(city.id))
			for general in state.generals:
				verify(state.turn_order.has(general.owner_id),id+"_general_owner_in_runtime_roster_"+str(general.id))
				var general_def=content.definition("generals",str(general.id))
				verify(year>=int(general_def.get("active_year_min",0)) and year<=int(general_def.get("active_year_max",9999)),id+"_general_activity_window_"+str(general.id))
			var expected_generals={"asia_1840":["lin_zexu"],"asia_1860":["hong_xiuquan","li_hongzhang"],"asia_1890":["li_hongzhang"],"asia_1900":["li_hongzhang"],"asia_1917":["sun_yat_sen"],"asia_1927":["chiang_kai_shek"],"asia_1940":["chiang_kai_shek","tojo_hideki","yamashita_tomoyuki"]}
			for general_id in expected_generals.get(id,[]):
				verify(state.generals.any(func(g):return g.id==general_id),id+"_historical_general_loaded_"+general_id)
	var catalog=content.read_json("res://content/scenarios/catalog.json")
	var campaign_prefixes=["campaign_1840_","campaign_1860_","campaign_1890_","campaign_1900_","campaign_1917_","campaign_1927_","campaign_1940_"]
	var campaign_ids=catalog.scenarios.filter(func(id):
		for prefix in campaign_prefixes:
			if str(id).begins_with(prefix):return true
		return false
	)
	for id in campaign_ids:
		var recipe=content.scenarios.get(id,{})
		verify(recipe.get("province_scope",[]).size()<=3,id+"_mission_scope_at_most_three")
		verify(content.maps.has(recipe.get("map_id","")),id+"_mission_map_resolves")
		var state=StateBuilder.create(content,id,recipe.get("player_default",""),{})
		verify(not state.is_empty(),id+"_mission_builds")
		if recipe.get("objective_type","")=="destroy":
			verify(oob.get("formations",[]).any(func(f):return str(f.id)==str(recipe.get("destroy_formation_id",""))),id+"_destroy_formation_source_resolves")
			verify(state.objectives.any(func(o):return o.type=="destroy" and o.target_ids.size()>0),id+"_destroy_objective_has_named_targets")
			var destroy_objective=state.objectives.filter(func(o):return o.type=="destroy")[0]
			var simulated=state.units.filter(func(u):return not destroy_objective.target_ids.has(u.id))
			state.units=simulated
			StateAccess.invalidate_occupancy()
			var victory_events:Array=[]
			VictoryRules.check(state,content,victory_events)
			verify(state.status=="won",id+"_destroy_objective_resolves_after_target_elimination")
	var report={"passed":checks.filter(func(v):return v.passed).size(),"failed":failures.size(),"checks":checks,"failures":failures,"timeline_count":ids.size(),"formations":oob.get("formations",[]).size(),"content_hash":content.content_hash}
	var file=FileAccess.open("res://reports/asia_content_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("ASIA_CONTENT_TESTS ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
