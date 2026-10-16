class_name HistoricalRules
extends RefCounted

static func process(state: Dictionary, event: Dictionary, content: ContentRegistry, events: Array) -> void:
	event.fired=true
	if event.type!="coup":return
	var source=str(event.get("source_owner","zhili"));var actor_id=str(event.get("actor_id","feng_yuxiang"))
	var new_owner=str(event.get("new_owner","guominjun"));var city_id=str(event.get("city_id","beijing"))
	var faction=StateAccess.faction(state,source);var actor=StateAccess.find(state,"generals",actor_id)
	var city=StateAccess.find(state,"cities",city_id);var force={};var reason=""
	if faction.is_empty() or faction.eliminated:reason="原所属势力已退出战局"
	elif actor.is_empty() or actor.owner_id!=source or actor.get("injured_this_match",false) or actor.get("withdrawn_this_match",false):reason="相关人物已失去活动条件"
	elif actor.assigned_unit_id==null:reason="相关人物已无活动编队"
	else:
		force=StateAccess.find(state,"units",actor.assigned_unit_id)
		if force.is_empty() or force.owner_id!=source or force.position==null or force.cargo_parent_id!=null:reason="相关编队已失去活动条件"
	if reason.is_empty() and (city.is_empty() or city.owner_id!=source):reason="北京控制权已改变"
	var garrison={}
	if reason.is_empty():
		garrison=StateAccess.at(state,"units",HexGrid.coordinate(city.position))
		if not garrison.is_empty() and (garrison.owner_id!=source or (garrison.general_id!=null and garrison.general_id!=actor_id)):reason="北京驻军指挥归属已改变"
	if reason.is_empty() and not StateAccess.faction(state,new_owner).is_empty():reason="事件目标势力已经存在"
	if not reason.is_empty():
		event.outcome="not_triggered";event.condition_reason=reason
		events.append({"type":"HistoricalEventSkipped","name":event.name,"description":event.description,"historical_date":event.get("date","1924-10-23"),"source_ids":event.get("source_ids",[]).duplicate(),"reason":reason})
		return
	# Prerequisites are checked before any mutation. The command kernel owns the
	# transaction; neither units nor geography are teleported to restore history.
	var next=faction.duplicate(true);next.id=new_owner
	next.resources=event.get("new_faction_resources",{"cash":400,"food":300,"arms":160}).duplicate(true)
	next.own_phase_index=0;next.eliminated=false;next.transport_pool=0;next.general_whitelist=[actor_id]
	var air_access=faction.airfield_whitelist.has(city_id)
	next.airfield_whitelist=[city_id] if air_access else []
	next.transport_used_phase=false
	if state.date<event.get("designation_date","1924-10-25"):
		next.name_override="冯玉祥部";next.historical_named_from=event.get("designation_date","1924-10-25")
		next.designation_source_ids=event.get("designation_source_ids",[]).duplicate()
	state.factions.append(next);state.turn_order.append(new_owner)
	for old in state.turn_order:
		if old==new_owner:continue
		state.relations.append({"id":"rel_%s_%s"%[old,new_owner],"faction_a":old,"faction_b":new_owner,"state":"WAR" if old==source else "NEUTRAL","passage":false,"supply":false,"minimum_until_round":0,"break_at_round":0,"last_aid_round":-10,"betrayal_until_round":0})
	EconomyRules.cancel_city_orders(state,city,events,"政变时未完工订单返还")
	city.owner_id=new_owner;city.stability=40;city.construction_action_used=true
	for key in ["fort_breached_by","suppressed_by","suppressed_round","naval_supported_by","naval_supported_round"]:city.erase(key)
	var transferred=[force.id];force.owner_id=new_owner
	if not garrison.is_empty():
		garrison.owner_id=new_owner
		if not transferred.has(garrison.id):transferred.append(garrison.id)
	for unit_id in transferred:
		var unit=StateAccess.find(state,"units",unit_id)
		unit.ap_left=0;unit.attack_ready=false;unit.skill_ready=false;unit.work_ready=false
		for job in state.engineer_jobs.duplicate():
			if job.unit_id==unit_id:job.owner_id=new_owner
		for status in state.statuses:
			if status.target_id==unit_id and status.source_owner_id==source:status.source_owner_id=new_owner
	for f in state.factions:f.general_whitelist.erase(actor_id);f.airfield_whitelist.erase(city_id)
	next.general_whitelist.append(actor_id)
	if air_access:next.airfield_whitelist.append(city_id)
	actor.owner_id=new_owner;actor.unassign_cooldown=0
	event.outcome="triggered";StateAccess.invalidate_occupancy();MovementRules.invalidate_rail_cache()
	events.append({"type":"HistoricalEvent","name":event.name,"description":event.description,"historical_date":event.get("date","1924-10-23"),"source_ids":event.get("source_ids",[]).duplicate(),"city_id":city_id,"owner_id":new_owner,"unit_ids":transferred,"general_id":actor_id})

static func update_designations(state: Dictionary, events: Array) -> void:
	for faction in state.factions:
		if not faction.has("historical_named_from") or state.date<faction.historical_named_from:continue
		var date=faction.historical_named_from;var sources=faction.get("designation_source_ids",[]).duplicate()
		faction.erase("name_override");faction.erase("historical_named_from");faction.erase("designation_source_ids")
		if faction.eliminated:continue
		events.append({"type":"HistoricalEvent","name":"国民军改组","description":"1924年10月25日议决改组国民军；本次仅更新仍在场势力的名称。","historical_date":date,"source_ids":sources,"owner_id":faction.id})
