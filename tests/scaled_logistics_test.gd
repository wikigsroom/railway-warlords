extends SceneTree

const REFERENCE=preload("res://tests/fixtures/logistics_reference_v022.gd")
var checks: Array=[]
var failures: Array=[]
var measurements: Array=[]

func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error("SCALED_LOGISTICS: "+name)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"current_large_geography_loaded")
	for scenario in ["conq_1924","campaign_1924_02","legion_07","legion_08"]:
		var state=StateBuilder.create(content,scenario,content.scenarios[scenario].player_default,{})
		var owner=state.player_faction_id
		for mode in ["intact","blocked"]:
			if mode=="blocked":
				if not state.map.rail_edges.is_empty():state.map.rail_edges[0].damage="broken";MovementRules.invalidate_rail_cache()
				state.cities[0].blockaded=true
			var started=Time.get_ticks_usec();var original=REFERENCE.supply_reach(state,owner,content);var original_ms=(Time.get_ticks_usec()-started)/1000.0
			started=Time.get_ticks_usec();var current=LogisticsRules.supply_reach(state,owner,content);var current_ms=(Time.get_ticks_usec()-started)/1000.0
			verify(current==original,scenario+"_"+mode+"_every_supply_distance_matches_archived_dijkstra")
			verify(LogisticsRules.naval_supply_reach(state,owner,content)==REFERENCE.naval_supply_reach(state,owner,content),scenario+"_"+mode+"_naval_port_components_match_archived_rules")
			var a=StateAccess.clone_transaction(state);var b=StateAccess.clone_transaction(state);var old_events=[];var new_events=[]
			REFERENCE.distribute(a,owner,content,old_events);LogisticsRules.distribute(b,owner,content,new_events)
			verify(a.units==b.units and a.factions==b.factions and a.metrics==b.metrics and old_events==new_events,scenario+"_"+mode+"_food_ammo_attrition_cargo_and_events_identical")
			measurements.append({"scenario":scenario,"mode":mode,"cells":state.map.cells.size(),"reachable_cells":current.size(),"archived_search_ms":original_ms,"current_search_ms":current_ms})
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"measurements":measurements,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"reference_version":"0.2.2","physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/scaled_logistics_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("SCALED_LOGISTICS_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"measurements":measurements}));quit(0 if failures.is_empty() else 1)
