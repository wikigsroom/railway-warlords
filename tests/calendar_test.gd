extends SceneTree

var checks: Array=[]
var failures: Array=[]
var content=ContentRegistry.new()
var base: Dictionary={}

func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func fixture(date: String) -> Dictionary:
	var state=base.duplicate(true);state.date=date
	StateAccess.invalidate_occupancy();MovementRules.invalidate_rail_cache()
	return state

func run() -> void:
	verify(content.load_all(),"native_content_loaded")
	verify(TurnRules.DAYS_PER_ROUND==1,"one_complete_round_is_one_day")
	verify(int(content.rules.scenario.conquest_days_per_round)==1,"registered_conquest_default_matches_daily_calendar")
	verify(int(content.rules.scenario.campaign_days_per_round)==1,"registered_campaign_default_matches_daily_calendar")
	for recipe in content.tables.scenarios:
		verify(int(recipe.get("days_per_round",0))==1,"definition_calendar_matches_daily_rule:"+str(recipe.id))
	for id in content.scenarios:
		verify(int(content.scenarios[id].get("days_per_round",0))==1,"daily_calendar_is_authored:"+id)
	base=StateBuilder.create(content,"campaign_1920_01","zhili",{},"normal")
	base.units=[];base.generals=[];base.cities=[];base.statuses=[];base.visibility=[]
	base.authored_events=[];base.engineer_jobs=[];base.pending_aid=[];base.event_log=[]
	base.map.cells=[{"id":"calendar_cell","position":{"q":0,"r":0},"terrain_id":"plain","region_id":"theater"}]
	base.map.reference_pois=[];base.map.rail_edges=[];base.map.rail_nodes=[];base.map.crossings=[]
	base.round=1;base.phase_index=0;base.status="playing";base.last_move_inverse=null
	for faction in base.factions:faction.eliminated=false
	var state=fixture("1917-09-01");var events: Array=[]
	TurnRules.end_phase(state,content,events)
	verify(state.date=="1917-09-01" and state.round==1,"one_faction_phase_does_not_consume_a_whole_day")
	TurnRules.end_phase(state,content,events)
	verify(state.date=="1917-09-02" and state.round==2,"all_factions_complete_exactly_one_calendar_day")
	for example in [["1840-01-31","1840-02-01"],["1860-12-31","1861-01-01"],["1900-02-28","1900-03-01"],["1920-02-28","1920-02-29"],["1920-02-29","1920-03-01"],["2000-02-28","2000-02-29"]]:
		state=fixture(example[0]);state.phase_index=state.turn_order.size()-1
		TurnRules.end_phase(state,content,[])
		verify(state.date==example[1] and state.round==2,"gregorian_boundary:"+example[0])
	state=fixture("1924-12-31")
	for faction in state.factions:
		if faction.id!=state.turn_order[0]:faction.eliminated=true
	TurnRules.end_phase(state,content,[])
	verify(state.date=="1925-01-01" and state.round==2 and state.phase_index==0,"skipping_eliminated_factions_does_not_add_extra_days")
	state=fixture("1940-02-27");state.round=99
	TurnRules.round_start(state,content,[])
	verify(state.weather.forecast.map(func(day):return day.date)==["1940-02-28","1940-02-29","1940-03-01"],"three_day_weather_forecast_crosses_leap_day")
	var dated={"type":"calendar_fixture","date":"1924-10-23","round":3,"fired":false}
	verify(not TurnRules.event_due(dated,"1924-10-22",300),"old_round_hint_cannot_fire_a_dated_event_early")
	verify(TurnRules.event_due(dated,"1924-10-23",2),"historical_date_can_fire_before_an_obsolete_round_hint")
	verify(TurnRules.event_due(dated,"1924-10-24",2),"overdue_dated_event_is_evaluated_on_next_round_start")
	verify(TurnRules.event_due({"round":4},"1924-10-01",4) and not TurnRules.event_due({"round":4},"1924-10-01",3),"undated_training_triggers_keep_their_round_semantics")
	state=fixture("1924-10-22");state.round=300;state.authored_events=[dated.duplicate(true)]
	TurnRules.round_start(state,content,[])
	verify(not state.authored_events[0].fired,"runtime_does_not_fire_before_the_historical_date")
	state.phase_index=state.turn_order.size()-1;TurnRules.end_phase(state,content,[])
	verify(state.date=="1924-10-23" and state.authored_events[0].fired,"daily_wrap_fires_the_dated_event")
	state.authored_events[0].outcome="already_processed";TurnRules.round_start(state,content,[])
	verify(state.authored_events[0].outcome=="already_processed","already_fired_event_is_not_processed_twice")
	var saves=SaveService.new("user://calendar_test_"+str(Time.get_ticks_msec()))
	verify(saves.write("test",state,content.content_hash),"daily_date_and_trigger_state_saved:"+saves.error)
	var loaded=saves.load_slot("test",content.content_hash)
	verify(loaded.get("date","")==state.date and loaded.get("round",0)==state.round and loaded.get("authored_events",[])==state.authored_events,"saved_calendar_and_fired_events_restore_without_skipping_days")
	if not loaded.is_empty():
		loaded.phase_index=loaded.turn_order.size()-1;TurnRules.end_phase(loaded,content,[])
	verify(loaded.get("date","")=="1924-10-24","loaded_match_continues_the_next_day")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"daily_scenarios":content.scenarios.size(),"days_per_round":1}
	var file=FileAccess.open("res://reports/calendar_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CALENDAR_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if report.passed else 1)
