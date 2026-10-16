extends SceneTree

var content=ContentRegistry.new()
var passed: Array=[]
var failed: Array=[]

func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	if ok:passed.append(name)
	else:failed.append(name);push_error("FAIL: "+name)

func board() -> Dictionary:
	# Deliberately artificial rule fixture. Historical event checks below use the
	# actual dated map; this line of cells is not shipped as geographic content.
	var s=StateBuilder.create(content,"conq_1924","zhili",{})
	s.units=[];s.cities=[];s.generals=[];s.statuses=[];s.visibility=[];s.engineer_jobs=[];s.pending_aid=[];s.authored_events=[]
	s.factions=s.factions.filter(func(f):return f.id in ["zhili","fengtian","shanxi"]);s.turn_order=["zhili","fengtian","shanxi"]
	s.relations=[];s.map.cells=[];s.map.rail_edges=[];s.map.crossings=[];s.weather.current="clear"
	for q in range(19):s.map.cells.append({"id":"line_%d"%q,"position":{"q":q,"r":0},"terrain_id":"plain","region_id":"theater"})
	for a in range(3):
		for b in range(a+1,3):s.relations.append({"id":"test_%d_%d"%[a,b],"faction_a":s.turn_order[a],"faction_b":s.turn_order[b],"state":"WAR","passage":false,"supply":false})
	StateAccess.invalidate_occupancy();return s

func city(s: Dictionary, id: String, q: int, owner: String, key: bool = true, level: int = 3) -> Dictionary:
	var c={"id":id,"name":id,"position":{"q":q,"r":0},"owner_id":owner,"level":level,"fort_hp":100,"fort_max_hp":100,"stability":100,"recruit_reserve":100,"key_city":key,"port":false,"buildings":[],"recruit_queue":[],"construction_queue":[],"construction_action_used":false,"air_sorties_left":0,"blockaded":false}
	s.cities.append(c);StateAccess.invalidate_occupancy();return c

func unit(s: Dictionary, id: String, q: int, owner: String = "zhili", def_id: String = "rifle") -> Dictionary:
	var u=StateBuilder.unit(id,def_id,owner,{"q":q,"r":0},content);s.units.append(u);StateAccess.invalidate_occupancy();return u

func dated_coup(date: String = "1924-10-23") -> Dictionary:
	var s=StateBuilder.create(content,"conq_1924","zhili",{});s.date=date;s.round=9
	# Keep the authored Feng force and an unassigned Zhili guard at Beijing.
	var beijing=StateAccess.find(s,"cities","beijing");var occupant=StateAccess.at(s,"units",HexGrid.coordinate(beijing.position))
	if not occupant.is_empty() and occupant.general_id=="feng_yuxiang":
		var standby=StateBuilder.deploy(s,beijing.position,"zhili","rifle",content,4)
		if not standby.is_empty():occupant.position=standby.position.duplicate();standby.position=beijing.position.duplicate();StateAccess.invalidate_occupancy()
		occupant=standby
	if not occupant.is_empty() and occupant.general_id!=null and occupant.general_id!="feng_yuxiang":
		var g=StateAccess.find(s,"generals",occupant.general_id)
		if not g.is_empty():g.assigned_unit_id=null
		occupant.general_id=null
	return s

func run() -> void:
	verify(content.load_all(),"content_loaded")
	var s=board();var target=city(s,"enemy_key",12,"fengtian");var u=unit(s,"remnant",0)
	unit(s,"guard",12,"fengtian")
	verify(MovementRules.counterattack_reaches(s,u,[target],content,3),"fortified_garrison_is_legal_terminal_at_three_phase_limit")
	verify(not MovementRules.counterattack_reaches(s,u,[target],content,2),"counterattack_cannot_use_fourth_phase")
	StateAccess.remove_by_id(s,"units","guard");target.position.q=13;StateAccess.invalidate_occupancy()
	verify(not MovementRules.counterattack_reaches(s,u,[target],content,3),"one_cell_beyond_three_phases_is_ineffective")
	target.position.q=12;StateAccess.invalidate_occupancy();unit(s,"hidden_blocker",5,"fengtian")
	verify(not MovementRules.counterattack_reaches(s,u,[target],content,3),"hidden_enemy_intermediate_cell_blocks_strategic_route")
	StateAccess.remove_by_id(s,"units","hidden_blocker");var neutral=city(s,"neutral_gate",5,"shanxi",false)
	StateAccess.relation(s,"zhili","shanxi").state="NEUTRAL"
	verify(not MovementRules.counterattack_reaches(s,u,[target],content,3),"route_cannot_borrow_ungranted_neutral_passage")
	StateAccess.relation(s,"zhili","shanxi").passage=true
	verify(MovementRules.counterattack_reaches(s,u,[target],content,3),"explicit_neutral_passage_allows_normal_ground_route")
	var original_count=s.units.size();var hp=u.hp;u.hp=int(ceil(u.max_hp*.25));var events: Array=[]
	VictoryRules.check(s,content,events)
	verify(not StateAccess.faction(s,"zhili").eliminated and s.units.size()==original_count,"exactly_25_percent_occupying_remnant_keeps_faction_active")
	s=board();city(s,"enemy_key",12,"fengtian");city(s,"neutral_major",18,"shanxi",false);u=unit(s,"remnant",0);u.hp=int(ceil(u.max_hp*.25))-1
	s.generals=[{"id":"feng_yuxiang","owner_id":"zhili","assigned_unit_id":u.id,"injured_this_match":false}];u.general_id="feng_yuxiang"
	s.engineer_jobs=[{"id":"job","unit_id":u.id,"owner_id":"zhili"}];s.statuses=[{"id":"status","target_id":u.id,"source_owner_id":"zhili"}]
	var low=city(s,"low_town",1,"zhili",false,1);low.recruit_queue=[{"id":"queued"}]
	s.pending_aid=[{"id":"aid","sender_id":"shanxi","receiver_id":"zhili","resources":{"cash":100,"food":20,"arms":0}}]
	var cash=StateAccess.faction(s,"shanxi").resources.cash;events=[];VictoryRules.check(s,content,events)
	verify(s.status=="lost" and s.units.is_empty() and events.any(func(e):return e.type=="UnitWithdrawn"),"ineffective_remnant_withdraws_without_cell_cleanup")
	verify(s.engineer_jobs.is_empty() and s.statuses.is_empty() and low.recruit_queue.is_empty(),"withdrawal_clears_dangling_jobs_statuses_and_training")
	verify(s.generals[0].assigned_unit_id==null and s.generals[0].get("withdrawn_this_match",false) and not s.generals[0].injured_this_match,"strategic_withdrawal_unassigns_general_without_faking_combat_loss")
	verify(s.metrics.kills==0 and s.metrics.losses==0 and not events.any(func(e):return e.type=="UnitDefeated"),"withdrawal_never_credits_kills_or_combat_losses")
	verify(s.pending_aid.is_empty() and StateAccess.faction(s,"shanxi").resources.cash==cash+50,"eliminated_recipient_returns_half_inflight_aid_immediately")
	s=board();target=city(s,"enemy_key",5,"fengtian");city(s,"other",18,"shanxi",false);u=unit(s,"artillery_remnant",0,"zhili","field_artillery")
	VictoryRules.check(s,content,[]);verify(StateAccess.faction(s,"zhili").eliminated,"artillery_without_occupation_capability_cannot_keep_faction_active")
	s=board();city(s,"enemy_key",5,"fengtian");city(s,"other",18,"shanxi",false);u=unit(s,"loaded_remnant",0);var ship=unit(s,"transport",1,"zhili","transport_ship");u.position=null;u.cargo_parent_id=ship.id
	VictoryRules.check(s,content,[]);verify(s.units.is_empty() and StateAccess.faction(s,"zhili").eliminated,"loaded_infantry_and_carrier_withdraw_as_one_group")
	s=board();city(s,"command",0,"zhili",false,1).command_center=true;city(s,"enemy",12,"fengtian");city(s,"other",18,"shanxi",false)
	VictoryRules.check(s,content,[]);verify(not StateAccess.faction(s,"zhili").eliminated,"explicit_low_level_command_center_counts_as_strategic_base")
	# Co-operative ownership and aggregate score must credit an allied player,
	# including when the canonical group ID belongs to a different faction.
	s=board();city(s,"a",0,"zhili");city(s,"b",6,"fengtian");city(s,"c",18,"shanxi",false)
	StateAccess.relation(s,"zhili","fengtian").state="ALLIANCE";events=[];VictoryRules.check(s,content,events)
	verify(s.status=="won" and s.winner_id=="fengtian" and s.winning_faction_ids.has("zhili"),"allied_city_control_grants_shared_victory")
	s=board();city(s,"a",0,"zhili");city(s,"b",6,"fengtian");city(s,"c",18,"shanxi")
	StateAccess.relation(s,"zhili","fengtian").state="ALLIANCE";StateAccess.relation(s,"fengtian","shanxi").state="ALLIANCE"
	verify(VictoryRules.alliance_groups(s).size()==3,"hostile_factions_cannot_share_result_through_third_party")
	StateAccess.relation(s,"zhili","shanxi").state="NEUTRAL"
	verify(VictoryRules.alliance_groups(s)==[["fengtian","shanxi","zhili"]],"consistent_alliance_chain_has_deterministic_group_id")
	s=board();city(s,"a",0,"zhili");city(s,"b",6,"fengtian");city(s,"c",18,"shanxi");s.round=81
	StateAccess.relation(s,"zhili","fengtian").state="ALLIANCE";unit(s,"first",1).hp=45;unit(s,"second",7,"fengtian").hp=55
	VictoryRules.check(s,content,[])
	var score=s.result_scores[0];var expected=210
	for c in s.cities:
		if c.owner_id in ["zhili","fengtian"]:
			var income=EconomyRules.income(c,content);expected+=income.cash*2+income.food+income.arms*2
	verify(s.status=="won" and score.members==["fengtian","zhili"] and score.score==expected,"80_round_score_uses_fixed_baseline_weights_and_allied_total_hp")
	s.protected_general_id="lost_commander";s.generals=[{"id":"lost_commander","injured_this_match":true}];s.status="playing"
	VictoryRules.check(s,content,[]);verify(s.status=="lost" and s.result_reason=="主将战败","protected_commander_failure_precedes_alliance_score")
	# Dated events use the real map and real recipe, with explicit changed-state cases.
	s=dated_coup("1924-10-22");events=[];TurnRules.round_start(s,content,events)
	verify(not s.turn_order.has("guominjun") and not s.authored_events[0].get("fired",false),"coup_never_fires_before_historical_date")
	s=dated_coup();var actor=StateAccess.find(s,"generals","feng_yuxiang");u=StateAccess.find(s,"units",actor.assigned_unit_id);var position=u.position.duplicate();var air_access=StateAccess.faction(s,"zhili").airfield_whitelist.has("beijing")
	var old_hash=ContentRegistry.fingerprint(s);var next=StateAccess.clone_transaction(s);events=[];TurnRules.round_start(next,content,events)
	verify(ContentRegistry.fingerprint(s)==old_hash and StateAccess.find(s,"cities","beijing").owner_id=="zhili","coup_transaction_preserves_previous_snapshot")
	verify(next.turn_order.has("guominjun") and StateAccess.find(next,"cities","beijing").owner_id=="guominjun" and StateAccess.find(next,"units",u.id).position==position,"coup_transfers_ownership_without_teleporting_force")
	verify(StateAccess.faction_name(next,"guominjun",content)=="冯玉祥部","october_23_uses_force_name_before_national_army_designation")
	verify(StateAccess.find(next,"generals",actor.id).owner_id=="guominjun" and not StateAccess.faction(next,"zhili").general_whitelist.has(actor.id) and StateAccess.faction(next,"guominjun").general_whitelist==[actor.id],"general_unit_and_deployment_whitelist_transfer_atomically")
	verify(StateAccess.relation(next,"zhili","guominjun").state=="WAR" and StateAccess.faction(next,"guominjun").airfield_whitelist.has("beijing")==air_access and not StateAccess.faction(next,"zhili").airfield_whitelist.has("beijing"),"event_creates_relations_and_transfers_only_existing_airfield_authorization")
	verify(events.any(func(e):return e.type=="HistoricalEvent" and e.historical_date=="1924-10-23" and e.source_ids.has("gz_beijing_coup_1924")),"trigger_log_distinguishes_historical_date_and_sources")
	next.date="1924-10-25";events=[];TurnRules.round_start(next,content,events)
	verify(StateAccess.faction_name(next,"guominjun",content)=="国民军" and events.any(func(e):return e.type=="HistoricalEvent" and e.name=="国民军改组"),"october_25_updates_name_from_separate_historical_record")
	var size=next.factions.size();events=[];TurnRules.round_start(next,content,events)
	verify(next.factions.size()==size and not events.any(func(e):return e.type=="HistoricalEvent"),"historical_transfer_and_designation_do_not_repeat")
	s=dated_coup();StateAccess.faction(s,"zhili").airfield_whitelist.clear();TurnRules.round_start(s,content,[])
	verify(StateAccess.faction(s,"guominjun").airfield_whitelist.is_empty(),"coup_does_not_create_missing_airfield_permission")
	for condition in ["missing_actor","injured_actor","eliminated_source","changed_city","foreign_guard","loaded_actor","commander_guard"]:
		s=dated_coup();actor=StateAccess.find(s,"generals","feng_yuxiang");u=StateAccess.find(s,"units",actor.assigned_unit_id)
		var beijing=StateAccess.find(s,"cities","beijing");var guard=StateAccess.at(s,"units",HexGrid.coordinate(beijing.position))
		match condition:
			"missing_actor":StateAccess.remove_by_id(s,"generals",actor.id)
			"injured_actor":actor.injured_this_match=true
			"eliminated_source":StateAccess.faction(s,"zhili").eliminated=true
			"changed_city":beijing.owner_id="fengtian"
			"foreign_guard":
				if guard.is_empty():guard=unit(s,"foreign_guard",0,"fengtian");guard.position=beijing.position.duplicate()
				guard.owner_id="fengtian"
			"loaded_actor":u.cargo_parent_id="changed_transport"
			"commander_guard":
				if guard.is_empty():guard=unit(s,"commander_guard",0);guard.position=beijing.position.duplicate()
				guard.general_id="wu_peifu"
		StateAccess.invalidate_occupancy();var owner_before=beijing.owner_id;var units_before=ContentRegistry.fingerprint(s.units);events=[]
		TurnRules.round_start(s,content,events)
		# Counter refresh is a round rule, so compare ownership and positions only.
		verify(not s.turn_order.has("guominjun") and beijing.owner_id==owner_before and u.owner_id=="zhili" and s.authored_events[0].outcome=="not_triggered" and events.any(func(e):return e.type=="HistoricalEventSkipped"),"changed_condition_skips_coup_"+condition)
	s=StateBuilder.create(content,"campaign_1924_05","zhili",{});s.date="1924-10-23";s.round=5;events=[];TurnRules.round_start(s,content,events)
	verify(s.turn_order.has("guominjun") and StateAccess.find(s,"cities","beijing").owner_id=="guominjun" and StateAccess.faction_name(s,"guominjun",content)=="冯玉祥部","campaign_coup_targets_feng_force_instead_of_fengtian")
	var recipe=content.scenarios.campaign_1924_05
	verify(recipe.events[0].forecast_round==3 and recipe.events[0].round==5 and recipe.events[0].date=="1924-10-23","campaign_warning_precedes_fixed_event_by_two_rounds")
	for protected_kind in ["formation","general","escort"]:
		s=dated_coup();actor=StateAccess.find(s,"generals","feng_yuxiang");var force=StateAccess.find(s,"units",actor.assigned_unit_id)
		s.protected_commander_id=null;s.protected_general_id=null;s.objectives=[]
		match protected_kind:
			"formation":s.protected_commander_id=force.id
			"general":s.protected_general_id=actor.id
			"escort":s.objectives=[{"id":"escort_fixture","type":"escort","protected":true,"target_ids":[force.id],"progress":0,"required":1}]
		TurnRules.round_start(s,content,[]);VictoryRules.check(s,content,[])
		verify(s.status=="lost" and not StateAccess.find(s,"units",force.id).is_empty() and s.result_reason.contains("脱离本方指挥"),"coup_transfer_of_protected_"+protected_kind+"_fails_without_fake_death")
	for condition in ["missing","withdrawn","foreign"]:
		s=StateBuilder.create(content,"campaign_1924_05","zhili",{});s.protected_commander_id=null
		var protected_general=StateAccess.find(s,"generals",s.protected_general_id)
		match condition:
			"missing":StateAccess.remove_by_id(s,"generals",protected_general.id)
			"withdrawn":protected_general.withdrawn_this_match=true
			"foreign":protected_general.owner_id="fengtian"
		VictoryRules.check(s,content,[])
		verify(s.status=="lost" and s.result_reason=="主将脱离本方指挥","protected_general_"+condition+"_cannot_count_as_preserved")
	var report={"passed":passed.size(),"failed":failed.size(),"checks":passed,"failures":failed,"content_hash":content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"scope":"Strategic rule fixtures and dated event transactions on the actual maps; not full historical military deployment or human balance approval."}
	var file=FileAccess.open("res://reports/strategic_history_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("STRATEGIC_HISTORY_TESTS ",JSON.stringify(report));quit(0 if failed.is_empty() else 1)
