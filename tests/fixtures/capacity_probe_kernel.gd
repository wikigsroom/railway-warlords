extends CommandKernel
const Probe=preload("res://tests/fixtures/capacity_probe.gd")

func resolve(state: Dictionary, command: Dictionary) -> Dictionary:
	var check=preview(state,command)
	if not check.valid:return check
	var next=Probe.clone_transaction(state);var events: Array=[];var owner=next.turn_order[next.phase_index]
	StateAccess.invalidate_occupancy()
	var u=StateAccess.find(next,"units",str(command.get("unit_id","")));var city=StateAccess.find(next,"cities",str(command.get("city_id","")));var type=command.type
	var previous=next.last_move_inverse;next.last_move_inverse=null
	match type:
		"Move":
			var old_unit=u.duplicate(true);var old_statuses=next.statuses.duplicate(true);var before_sight_count=0;var old_visible_enemies={}
			for enemy in next.units:
				if enemy.owner_id!=owner and VisibilityRules.unit_visible(next,owner,enemy):old_visible_enemies[enemy.id]=true
			for sight in next.visibility:
				if sight.faction_id==owner:before_sight_count=sight.explored_cell_ids.size()
			Probe.resolve_move(next,u,check.path,content,events);Probe.refresh(next,content)
			var after_sight=[]
			for sight in next.visibility:
				if sight.faction_id==owner:after_sight=sight.explored_cell_ids
			var new_enemy=next.units.any(func(enemy):return enemy.owner_id!=owner and VisibilityRules.unit_visible(next,owner,enemy) and not old_visible_enemies.has(enemy.id))
			if not new_enemy and after_sight.size()==before_sight_count and not events.any(func(e):return e.type in ["CityCaptured","UnitContact"]):next.last_move_inverse={"unit_id":u.id,"unit_before":old_unit,"statuses_before":old_statuses}
		"Attack":CombatRules.resolve(next,u,StateAccess.find(next,"units",str(check.target_id)),content,events,StateAccess.find(next,"cities",str(check.city_id)))
		"Recruit":EconomyRules.recruit(next,city,command,content,events)
		"Build","UpgradeCity":EconomyRules.construction(next,city,"city_level" if type=="UpgradeCity" else command.def_id,content,events)
		"CancelQueue":EconomyRules.cancel_queue(next,city,command.queue_id,command.get("construction",false),content,events)
		"DemolishBuilding":
			city.buildings=city.buildings.filter(func(b):return b.def_id!=command.def_id);city.construction_action_used=true
			city.fort_max_hp=mini(340,int(content.tables.city_levels[int(city.level)-1].fort_hp)+40*EconomyRules.building_level(city,"fortification"));city.fort_hp=mini(city.fort_hp,city.fort_max_hp)
			events.append({"type":"BuildingDemolished","city_id":city.id,"def_id":command.def_id})
		"Reinforce":EconomyRules.reinforce(next,u,StateAccess.find(next,"cities",check.city_id),content,events)
		"RepairFort":StateAccess.pay(next,owner,check.cost,events,"城防修复");city.fort_hp+=check.hp;city.erase("fort_breached_by");city.construction_action_used=true;events.append({"type":"FortRepaired","city_id":city.id,"amount":check.hp})
		"RailTransport":LogisticsRules.transport(next,u,StateAccess.find(next,"cities",command.destination_id),check.route,content,events)
		"EngineerWork":
			var edge=edge_by_id(next,command.edge_id)
			if command.get("action","repair")=="demolish":LogisticsRules.demolish(next,edge,owner,content,events)
			else:
				StateAccess.pay(next,owner,check.cost,events,"铁路抢修")
				next.engineer_jobs.append({"id":StateBuilder.next_id(next,"job"),"unit_id":u.id,"owner_id":owner,"edge_id":edge.id,"remaining_own_phases":check.phases,"total_own_phases":check.phases,"paid_cost":check.cost,"paused":false})
			u.ap_left=0;u.attack_ready=false;u.work_ready=false
		"CancelWork":
			var job=StateAccess.find(next,"engineer_jobs",command.job_id);var refund={}
			for key in job.paid_cost:refund[key]=int(job.paid_cost[key]*job.remaining_own_phases/maxi(1,job.total_own_phases)*.5)
			StateAccess.add_resources(next,owner,refund,events,"取消抢修");next.engineer_jobs.erase(job)
		"Embark":
			u.cargo_parent_id=command.ship_id;u.position=null;u.ap_left=0;u.attack_ready=false;u.cargo_actions_ready=false;u.cargo_sailed=false
			var ship=StateAccess.find(next,"units",command.ship_id);ship.ap_left=0;ship.attack_ready=false
			events.append({"type":"Embarked","unit_id":u.id,"ship_id":command.ship_id})
		"Disembark":
			var ship=StateAccess.find(next,"units",u.cargo_parent_id);ship.ap_left=0;ship.attack_ready=false
			u.position=command.target_hex.duplicate();u.cargo_parent_id=null;u.ap_left=0;u.attack_ready=false;u.moved_this_phase=true;u.cargo_actions_ready=false
			events.append({"type":"Disembarked","unit_id":u.id,"position":u.position})
		"AssignGeneral":GeneralRules.assign(next,u,StateAccess.find(next,"generals",command.general_id),content,events)
		"UnassignGeneral":GeneralRules.unassign(next,u,content,events)
		"ActivateSkill":GeneralRules.skill(next,u,command,content,events)
		"SetSupplyPriority":u.supply_priority=command.priority
		"AirRecon","AirBomb":GeneralRules.air(next,city,command.target_hex,type=="AirBomb",content,events)
		"Trade":
			StateAccess.pay(next,owner,check.cost,events,"军需交易")
			var income={command.resource:int(command.amount)} if command.get("buy",true) else {"cash":int(command.amount)*(2 if command.resource=="food" else 3)}
			StateAccess.add_resources(next,owner,income,events,"军需交易");StateAccess.faction(next,owner).trade_orders_left-=1
		"Diplomacy":DiplomacyRules.act(next,owner,command,events)
		"UndoMove":
			var undo=previous;var restored=StateAccess.find(next,"units",undo.unit_id)
			for key in undo.unit_before:restored[key]=undo.unit_before[key]
			next.statuses=undo.statuses_before;events.append({"type":"MoveUndone","unit_id":restored.id})
		"EndPhase":Probe.end_phase(next,content,events)
	for e in events:
		if e.type=="UnitMoved" and not u.is_empty() and u.def_id=="transport_ship":
			for passenger in next.units:
				if passenger.cargo_parent_id==u.id:passenger.cargo_sailed=true
		var ours=e.get("owner_id","")==next.player_faction_id
		match e.type:
			"UnitDefeated":
				if ours:next.metrics.losses+=1
				elif e.get("defeated_by","")==next.player_faction_id and StateAccess.hostile(state,next.player_faction_id,e.owner_id):next.metrics.kills+=1
			"CityCaptured":
				if ours:next.metrics.captures+=1
			"RailTransported":if owner==next.player_faction_id:next.metrics.rail_trips+=1
			"RailRepaired":if ours:next.metrics.rail_repairs+=1
			"AirRecon":if owner==next.player_faction_id:next.metrics.air_recon+=1
			"AirBombed":if owner==next.player_faction_id:next.metrics.air_bombs+=1
			"SkillActivated":if owner==next.player_faction_id:next.metrics.skills+=1
			"UnitReinforced":if owner==next.player_faction_id:next.metrics.reinforcements+=1
			"BuildingCompleted":if e.get("owner_id",owner)==next.player_faction_id:next.metrics.buildings+=1
			"DiplomacyChanged":if owner==next.player_faction_id:next.metrics.diplomacy+=1
		if owner==next.player_faction_id:
			var metric={"RailTransported":"rail_transfers_successful","SkillActivated":"general_active_skill_uses","Disembarked":"safe_transport_disembark"}.get(e.type,"")
			if not metric.is_empty():next.metrics[metric]=int(next.metrics.get(metric,0))+1
			if e.type=="DamageApplied" and int(e.get("amount",0))>0 and not e.get("counter",false):
				var attacker=StateAccess.find(state,"units",str(e.get("attacker_id")));var target=StateAccess.find(state,"units",str(e.get("unit_id")))
				if not attacker.is_empty() and not target.is_empty() and content.definition("units",attacker.def_id).family=="artillery":
					var observer=state.units.any(func(v):return v.owner_id==owner and v.id!=attacker.id and v.position!=null and HexGrid.distance(HexGrid.coordinate(v.position),HexGrid.coordinate(target.position))<=2 and not MovementRules.adjacent_hostile(state,v,HexGrid.coordinate(v.position),content))
					if observer:next.metrics.protected_observer_artillery_hits=int(next.metrics.get("protected_observer_artillery_hits",0))+1
	StateAccess.invalidate_occupancy()
	next.state_version=state.state_version+1
	if command.get("debug",false):next.debug_match=true
	Probe.refresh(next,content);Probe.victory_check(next,content,events)
	StateAccess.freeze_map(next.map)
	for e in events:
		e.round=next.round;e.sequence=next.state_version
		next.event_log.append(e)
	while next.event_log.size()>250:next.event_log.pop_front()
	return {"valid":true,"state":next,"events":events,"preview":check,"command":command.duplicate(true)}
