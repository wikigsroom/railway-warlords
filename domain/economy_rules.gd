class_name EconomyRules
extends RefCounted

static func building_level(city: Dictionary, id: String) -> int:
	for b in city.buildings:
		if b.def_id==id and not b.get("damaged",false):return int(b.level)
	return 0

static func income(city: Dictionary, content: ContentRegistry) -> Dictionary:
	var result=content.tables.city_levels[int(city.level)-1].income.duplicate()
	for b in city.buildings:
		if b.get("damaged",false):continue
		var d=content.definition("buildings",b.def_id)
		var extra=d.level_definitions[int(b.level)-1].income
		for resource in result:result[resource]+=int(extra.get(resource,0))
	for resource in result:result[resource]=int(result[resource]*city.stability/100)
	return result

static func recruit_cost(state: Dictionary, owner: String, def_id: String, stack: int, elite_id: Variant, content: ContentRegistry) -> Dictionary:
	var u={"def_id":def_id,"elite_id":elite_id}
	var d=EffectRules.scaled_definition(u,content)
	var result=d.cost.duplicate()
	for key in result:result[key]*=stack
	return EffectRules.reduced_cost(result,EffectRules.technology(state,owner,"recruit_cost_reduction",u,content))

static func recruit(state: Dictionary, city: Dictionary, command: Dictionary, content: ContentRegistry, events: Array) -> void:
	var elite=command.get("elite_id")
	var cost=recruit_cost(state,city.owner_id,command.def_id,command.stack,elite,content)
	StateAccess.pay(state,city.owner_id,cost,events,"征募")
	city.recruit_reserve-=int(command.stack)*10
	var u={"def_id":command.def_id,"elite_id":elite}
	var d=EffectRules.scaled_definition(u,content)
	city.recruit_queue.append({"id":StateBuilder.next_id(state,"queue"),"target_def_id":command.def_id,"elite_id":elite,"stack":command.stack,"remaining_own_phases":d.build_turns,"total_own_phases":d.build_turns,"paid_cost":cost,"ready":false,"deploy_hex":command.get("deploy_hex",city.position).duplicate()})
	events.append({"type":"RecruitQueued","city_id":city.id,"def_id":command.def_id})

static func deployment_hex(state: Dictionary, city: Dictionary, queued: Dictionary, content: ContentRegistry) -> Variant:
	var d=content.definition("units",queued.target_def_id)
	var origin=HarborRules.land_hex(city) if d.movement_profile in ["river","water","sea"] else HexGrid.coordinate(city.position)
	var positions: Array=[HexGrid.coordinate(queued.deploy_hex),origin]
	for dir in HexGrid.DIRECTIONS:positions.append(origin+dir)
	for h in positions:
		if HexGrid.distance(origin,h)>1:continue
		var cell=StateAccess.cell(state,h)
		if cell.is_empty() or cell.region_id=="restricted" or not StateAccess.at(state,"units",h).is_empty():continue
		var other_city=StateAccess.at(state,"cities",h)
		if not other_city.is_empty() and other_city.owner_id!=city.owner_id:continue
		var terrain=content.definition("terrains",cell.terrain_id)
		if d.movement_profile=="rail":
			if state.map.rail_edges.any(func(e):return e.damage=="intact" and MovementRules.rail_available(state,e) and e.path_hexes.has(HexGrid.position(h))):return HexGrid.position(h)
		elif d.movement_profile in ["river","water","sea"]:
			if terrain.water:return HexGrid.position(h)
		elif terrain.get("cost_"+d.movement_profile,0)>0:return HexGrid.position(h)
	return null

static func process_queues(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	for city in state.cities:
		if city.owner_id!=owner:continue
		for queued in city.recruit_queue.duplicate():
			queued.remaining_own_phases=maxi(0,queued.remaining_own_phases-1)
			queued.ready=queued.remaining_own_phases==0
			if queued.ready:
				var hex=deployment_hex(state,city,queued,content)
				if hex!=null:
					var u=StateBuilder.unit(StateBuilder.next_id(state,"u"),queued.target_def_id,owner,hex,content,queued.stack,queued.elite_id)
					state.units.append(u);city.recruit_queue.erase(queued)
					StateAccess.invalidate_occupancy()
					events.append({"type":"UnitDeployed","unit_id":u.id,"city_id":city.id,"position":hex})
		for queued in city.construction_queue.duplicate():
			queued.remaining_own_phases=maxi(0,queued.remaining_own_phases-1)
			if queued.remaining_own_phases>0:continue
			if queued.target_def_id=="city_level":city.level=queued.target_level
			else:
				var b={}
				for record in city.buildings:
					if record.def_id==queued.target_def_id:b=record
				if b.is_empty():city.buildings.append({"def_id":queued.target_def_id,"level":queued.target_level,"damaged":false})
				else:b.level=queued.target_level;b.damaged=false
			city.fort_max_hp=mini(340,int(content.tables.city_levels[int(city.level)-1].fort_hp)+40*building_level(city,"fortification"))
			city.construction_queue.erase(queued)
			events.append({"type":"BuildingCompleted","city_id":city.id,"def_id":queued.target_def_id,"owner_id":owner})

static func construction(state: Dictionary, city: Dictionary, def_id: String, content: ContentRegistry, events: Array) -> void:
	var level=building_level(city,def_id)+1
	var cost:Dictionary={};var phases=1
	if def_id=="city_level":
		level=city.level+1;var d=content.tables.city_levels[level-1]
		cost={"cash":d.upgrade_cost_cash,"arms":d.upgrade_cost_arms};phases=d.upgrade_turns
	else:
		for b in city.buildings:
			if b.def_id==def_id and b.get("damaged",false):level=int(b.level)
		var d=content.definition("buildings",def_id).level_definitions[level-1]
		cost=d.cost.duplicate();phases=d.build_own_phases
	StateAccess.pay(state,city.owner_id,cost,events,"建设")
	city.construction_queue.append({"id":StateBuilder.next_id(state,"build"),"target_def_id":def_id,"target_level":level,"remaining_own_phases":phases,"total_own_phases":phases,"paid_cost":cost})
	city.construction_action_used=true
	events.append({"type":"ConstructionQueued","city_id":city.id,"def_id":def_id})

static func cancel_queue(state: Dictionary, city: Dictionary, queue_id: String, construction_queue: bool, content: ContentRegistry, events: Array) -> void:
	var list=city.construction_queue if construction_queue else city.recruit_queue
	for q in list:
		if q.id!=queue_id:continue
		var rate=500 if construction_queue or q.get("ready",false) else 750
		var refund={}
		for key in q.paid_cost:
			var amount=int(q.paid_cost[key])
			if construction_queue:amount=int(amount*q.remaining_own_phases/maxi(1,q.total_own_phases))
			refund[key]=int(amount*rate/1000)
		StateAccess.add_resources(state,city.owner_id,refund,events,"撤销队列")
		if not construction_queue and not q.ready:
			city.recruit_reserve=mini(int(content.tables.city_levels[int(city.level)-1].recruit_reserve_cap),city.recruit_reserve+q.stack*10)
		list.erase(q);return

static func cancel_city_orders(state: Dictionary, city: Dictionary, events: Array, reason: String = "失城返还") -> void:
	var old=city.owner_id
	for queued in city.recruit_queue:
		var refund={}
		for key in queued.paid_cost:refund[key]=int(queued.paid_cost[key]*queued.remaining_own_phases/maxi(1,queued.total_own_phases)*.5)
		StateAccess.add_resources(state,old,refund,events,reason)
	for queued in city.construction_queue:
		var refund={}
		for key in queued.paid_cost:refund[key]=int(queued.paid_cost[key]*queued.remaining_own_phases/maxi(1,queued.total_own_phases)*.5)
		StateAccess.add_resources(state,old,refund,events,reason)
	city.recruit_queue.clear();city.construction_queue.clear()

static func capture_city(state: Dictionary, city: Dictionary, captor: Dictionary, content: ContentRegistry, events: Array) -> void:
	var old=city.owner_id
	cancel_city_orders(state,city,events)
	city.owner_id=captor.owner_id;city.stability=40;city.recruit_reserve=int(city.recruit_reserve*.4);city.construction_action_used=true
	if captor.owner_id==state.player_faction_id:
		if city.get("fort_breached_by")==captor.owner_id:state.metrics.fort_breach_then_occupation=int(state.metrics.get("fort_breach_then_occupation",0))+1
		if city.get("suppressed_by")==captor.owner_id and city.get("suppressed_round",-1)==state.round:state.metrics.suppressed_target_capture_city=int(state.metrics.get("suppressed_target_capture_city",0))+1
		if city.get("naval_supported_by")==captor.owner_id and city.get("naval_supported_round",-1)==state.round:state.metrics.naval_shore_support_then_capture=int(state.metrics.get("naval_shore_support_then_capture",0))+1
	for key in ["fort_breached_by","suppressed_by","suppressed_round","naval_supported_by","naval_supported_round"]:city.erase(key)
	for b in city.buildings:
		if b.def_id in ["arsenal","station"]:b.damaged=true;b.level=1
	captor.morale=mini(100,captor.morale+6);captor.ap_left=0;captor.attack_ready=false
	events.append({"type":"CityCaptured","city_id":city.id,"old_owner_id":old,"owner_id":city.owner_id})

static func reinforce_preview(state: Dictionary, u: Dictionary, content: ContentRegistry) -> Dictionary:
	var d=EffectRules.scaled_definition(u,content)
	var rate=250*(1000+EffectRules.technology(state,u.owner_id,"reinforce_efficiency_bonus",u,content))
	var hp=mini(u.max_hp-u.hp,int(ceil(float(u.max_hp)*rate/1000000.0)))
	if MovementRules.adjacent_hostile(state,u,HexGrid.coordinate(u.position),content):hp=int(hp/2)
	var cost={"cash":int(ceil(float(d.cost.cash)*.7*hp/d.hp)),"arms":int(ceil(float(d.cost.arms)*.7*hp/d.hp)),"food":int(ceil(hp/10.0))}
	return {"hp":hp,"cost":cost,"population":int(ceil(hp/10.0))}

static func reinforce(state: Dictionary, u: Dictionary, city: Dictionary, content: ContentRegistry, events: Array) -> void:
	var p=reinforce_preview(state,u,content)
	StateAccess.pay(state,u.owner_id,p.cost,events,"补充兵员");city.recruit_reserve-=p.population
	u.hp+=p.hp;u.ap_left=0;u.attack_ready=false;u.work_ready=false
	events.append({"type":"UnitReinforced","unit_id":u.id,"amount":p.hp})

static func fort_repair_preview(state: Dictionary, city: Dictionary, content: ContentRegistry) -> Dictionary:
	var hp=mini(20,city.fort_max_hp-city.fort_hp)
	var probe={"owner_id":city.owner_id,"position":city.position}
	if MovementRules.adjacent_hostile(state,probe,HexGrid.coordinate(city.position),content):hp=int(hp/2)
	return {"hp":hp,"cost":{"cash":int(ceil(12.0*hp/20)),"arms":int(ceil(6.0*hp/20))}}

static func collect_income(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var total={"cash":0,"food":0,"arms":0,"fuel":0,"silver":0};var f=StateAccess.faction(state,owner)
	for c in state.cities:
		if c.owner_id!=owner:continue
		var amount=income(c,content)
		for key in ["cash","food","arms"]:total[key]+=int(amount[key]*f.income_penalty_permille/1000)
		# Fuel and silver are strategic resources used by the Asia free-world layer.
		# Their yields are game economy values; city coordinates and history remain
		# source-tagged records in content/history.
		total.fuel+=int((4 if c.port else 1 if building_level(c,"station")>0 else 0)*f.income_penalty_permille/1000)
		total.silver+=int((3 if c.level>=2 else 1)*f.income_penalty_permille/1000)
		var regen=int(content.tables.city_levels[int(c.level)-1].recruit_reserve_regen)+2*building_level(c,"granary")
		c.recruit_reserve=mini(int(content.tables.city_levels[int(c.level)-1].recruit_reserve_cap),c.recruit_reserve+regen)
	StateAccess.add_resources(state,owner,total,events,"城市税收")
	f.income_penalty_permille=1000

static func salary(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var f=StateAccess.faction(state,owner)
	var troops=state.units.filter(func(u):return u.owner_id==owner)
	troops.sort_custom(func(a,b):return str(a.id)<str(b.id))
	for u in troops:
		var d=EffectRules.scaled_definition(u,content)
		if not StateAccess.pay(state,owner,{"cash":int(d.upkeep.cash)*int(u.stack)},events,"军饷"):
			u.morale=maxi(0,u.morale-5);f.income_penalty_permille=750
	for c in state.cities:
		if c.owner_id!=owner:continue
		for q in c.recruit_queue:
			if q.ready:
				var d=EffectRules.scaled_definition({"def_id":q.target_def_id,"elite_id":q.elite_id},content)
				StateAccess.pay(state,owner,{"cash":int(ceil(float(d.upkeep.cash)*q.stack*.25))},events,"待部署维持")
