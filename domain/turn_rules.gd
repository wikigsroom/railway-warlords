class_name TurnRules
extends RefCounted

static func round_start(state: Dictionary, content: ContentRegistry, events: Array) -> void:
	HistoricalRules.update_designations(state,events)
	for poi in state.map.get("reference_pois",[]).duplicate():
		if poi.get("poi_reason","")!="historical_occupation" or state.date<poi.protected_before:continue
		var city=poi.duplicate(true);city.owner_id=poi.reference_owner
		StateBuilder.initialize_city(state,city,content)
		var cell=StateAccess.mutable_cell(state,HexGrid.coordinate(city.position));cell.region_id=cell.get("region_before_protection","theater")
		state.map.reference_pois.erase(poi);MovementRules.invalidate_rail_cache()
		events.append({"type":"HistoricalEvent","name":"青岛接收","description":"1922年12月10日中方接收青岛；胶济铁路仍按各阶段接收日期单独限制军运。","historical_date":poi.protected_before,"source_ids":poi.historical_control_sources})
	for e in state.map.rail_edges:e.capacity_left=e.capacity_max
	for u in state.units:u.counter_left=2 if u.def_id=="machine_gun" else 1
	for r in state.relations:
		if r.break_at_round>0 and r.break_at_round<=state.round:r.state="NEUTRAL";r.passage=false;r.supply=false;r.break_at_round=0
	state.weather.current=weather_at(state,state.date,state.round)
	state.weather.forecast=[]
	var timestamp=Time.get_unix_time_from_datetime_string(state.date+"T00:00:00")
	for offset in range(1,4):
		var date=Time.get_date_string_from_unix_time(timestamp+86400*offset*int(content.scenarios[state.scenario_id].days_per_round))
		state.weather.forecast.append({"round":state.round+offset,"date":date,"weather":weather_at(state,date,state.round+offset)})
	for event in state.authored_events:
		if (int(event.get("round",-1))==state.round or (event.has("date") and state.date>=event.date)) and not event.get("fired",false):
			HistoricalRules.process(state,event,content,events)
	events.append({"type":"RoundStarted","round":state.round,"weather":state.weather.current})

static func weather_at(state: Dictionary, date: String, round_index: int) -> String:
	var month=int(date.substr(5,2));var bounds=state.map.get("geographic_bounds",[0,38,0,40])
	var northern=float(bounds[1]+bounds[3])*.5>=35
	if northern and month in [11,12,1,2,3] and round_index%8==0:return "snow"
	return "rain" if round_index%8 in [4,0] else "clear"

static func own_start(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var f=StateAccess.faction(state,owner);f.own_phase_index+=1
	# Free-world campaigns expose political pressure alongside food/arms/supply.
	# Exhaustion rises during war and decays in a quiet turn; legitimacy softens
	# the economic hit. These are game variables, not historical measurements.
	var at_war=state.relations.any(func(rel):return rel.state=="WAR" and (rel.faction_a==owner or rel.faction_b==owner))
	f.war_exhaustion=clampi(int(f.get("war_exhaustion",0))+(2 if at_war else -1),0,100)
	f.legitimacy=clampi(int(f.get("legitimacy",50))+(1 if not at_war else -1),0,100)
	f.income_penalty_permille=clampi(1000-int(f.war_exhaustion)*3+int(f.legitimacy-50)*2,550,1100)
	if f.war_exhaustion>=70:
		for unit in state.units:
			if unit.owner_id==owner:unit.morale=maxi(0,int(unit.morale)-2)
	var ports=state.cities.filter(func(city):return city.owner_id==owner and city.port).size()
	f.colonial_influence=mini(100,int(f.get("colonial_influence",0))+ports)
	EconomyRules.process_queues(state,owner,content,events)
	LogisticsRules.process_jobs(state,owner,content,events)
	DiplomacyRules.settle_aid(state,owner,events)
	EconomyRules.collect_income(state,owner,content,events)
	EconomyRules.salary(state,owner,content,events)
	LogisticsRules.distribute(state,owner,content,events)
	for i in range(state.statuses.size()-1,-1,-1):
		var status=state.statuses[i]
		if status.source_owner_id==owner and status.expires_owner_phase>=0 and status.expires_owner_phase<=f.own_phase_index:state.statuses.remove_at(i)
	GeneralRules.refresh(state,owner,content)
	var telegraph=false
	for city in state.cities:
		if city.owner_id!=owner:continue
		city.stability=mini(100,city.stability+10+(5 if EconomyRules.building_level(city,"supply_depot")>0 else 0))
		city.construction_action_used=false
		city.air_sorties_left=mini(4,EconomyRules.building_level(city,"airfield")+1+EffectRules.technology(state,owner,"air_sorties_flat",{},content)) if EconomyRules.building_level(city,"airfield")>0 else 0
		telegraph=telegraph or EconomyRules.building_level(city,"telegraph")>0
	for u in state.units:
		if u.owner_id!=owner:continue
		if not u.moved_this_phase and not u.attacked_this_phase and u.position!=null and content.definition("units",u.def_id).family=="infantry":
			var old=EffectRules.status_bonus(state,u,"defense_flat")
			for i in range(state.statuses.size()-1,-1,-1):
				if state.statuses[i].target_id==u.id and state.statuses[i].def_id=="entrenched":state.statuses.remove_at(i)
			state.statuses.append({"id":StateBuilder.next_id(state,"status"),"def_id":"entrenched","target_id":u.id,"source_owner_id":owner,"value":mini(8,old+4),"expires_owner_phase":-1})
		u.suppression=maxi(0,u.suppression-25-(10 if u.supply_state=="FULL" else 0))
		u.ap_left=mini(8,int(content.definition("units",u.def_id).ap)+EffectRules.technology(state,owner,"ap_flat",u,content))-int(content.rules.combat.suppression_ap_penalties[CombatRules.suppression_tier(u.suppression,content.rules)])
		u.ap_left=maxi(0,u.ap_left)
		u.attack_ready=u.cargo_parent_id==null;u.skill_ready=u.cargo_parent_id==null;u.work_ready=u.cargo_parent_id==null
		if u.cargo_parent_id!=null:u.ap_left=0
		u.moved_this_phase=false;u.attacked_this_phase=false;u.transported_this_phase=false;u.general_assignment_lock=false
		u.cargo_actions_ready=true
	f.command_points=mini(5,3+(1 if telegraph else 0)+EffectRules.technology(state,owner,"command_flat",{},content))
	f.trade_orders_left=2;f.diplomacy_orders_left=1;f.war_orders_left=1;f.aid_orders_left=1;f.air_sorties_left=5;f.transport_used_phase=false
	LogisticsRules.refresh_transport(state,owner,content)
	VisibilityRules.refresh(state,content)
	events.append({"type":"PhaseStarted","owner_id":owner})

static func end_phase(state: Dictionary, content: ContentRegistry, events: Array) -> void:
	var owner=state.turn_order[state.phase_index]
	state.phase_index+=1
	var steps=0
	while steps<state.turn_order.size():
		if state.phase_index>=state.turn_order.size():
			state.phase_index=0;state.round+=1;state.metrics.rounds=state.round
			var timestamp=Time.get_unix_time_from_datetime_string(state.date+"T00:00:00")
			state.date=Time.get_date_string_from_unix_time(timestamp+86400*int(content.scenarios[state.scenario_id].days_per_round))
			round_start(state,content,events)
		if not StateAccess.faction(state,state.turn_order[state.phase_index]).eliminated:break
		state.phase_index+=1;steps+=1
	state.last_move_inverse=null
	if steps<state.turn_order.size():own_start(state,state.turn_order[state.phase_index],content,events)
	events.append({"type":"PhaseEnded","owner_id":owner})
