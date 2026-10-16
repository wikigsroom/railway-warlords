class_name SnapshotReferenceKernel023
extends RefCounted

var content: ContentRegistry

func _init(registry: ContentRegistry) -> void:content=registry

func fail(reason: String) -> Dictionary:return {"valid":false,"reason":reason}

func preview(state: Dictionary, command: Dictionary) -> Dictionary:
	if state.is_empty() or state.status!="playing":return fail("本局已经结束")
	if int(command.get("expected_version",-1))!=int(state.state_version):return fail("战局已经更新，请重新选择")
	var owner=state.turn_order[state.phase_index]
	if command.get("actor_id","")!=owner:return fail("尚未轮到本方行动")
	var f=SnapshotReferenceAccess023.faction(state,owner)
	var type=str(command.get("type",""))
	var u=SnapshotReferenceAccess023.find(state,"units",str(command.get("unit_id","")))
	var city=SnapshotReferenceAccess023.find(state,"cities",str(command.get("city_id","")))
	var unit_commands=["Move","Attack","Reinforce","RailTransport","EngineerWork","Embark","Disembark","AssignGeneral","UnassignGeneral","ActivateSkill","SetSupplyPriority"]
	if type in unit_commands and (u.is_empty() or u.owner_id!=owner):return fail("请选择本方部队")
	if type in unit_commands and u.position==null and type!="Disembark":return fail("装载部队须先下船")
	if type in ["Recruit","Build","UpgradeCity","Trade","RepairFort","AirRecon","AirBomb","CancelQueue","DemolishBuilding"] and (city.is_empty() or city.owner_id!=owner):return fail("请选择本方城市")
	match type:
		"EndPhase":return {"valid":true,"reason":"结束本方阶段"}
		"Move":
			if not valid_hex(command.get("target_hex")):return fail("目标格无效")
			if u.ap_left<=0:return fail("行动点已用尽")
			var target=HexGrid.coordinate(command.target_hex)
			if not SnapshotReferenceAccess023.at(state,"units",target).is_empty():return fail("目标格已有部队")
			var graph=MovementRules.reachable(state,u,content)
			var path=MovementRules.route_from_graph(graph,HexGrid.coordinate(u.position),target)
			if path.size()<2:return fail("目标无法在本阶段抵达")
			return {"valid":true,"path":path,"cost":graph.costs[HexGrid.key(target)]}
		"Attack":return attack_preview(state,u,command)
		"Recruit":
			var d=content.definition("units",str(command.get("def_id","")))
			var stack=int(command.get("stack",0));var elite=command.get("elite_id")
			if d.is_empty() or stack<1 or stack>int(d.max_stack):return fail("编队层数无效")
			if not f.equipment_whitelist.has(d.id):return fail("本剧本未开放此装备")
			var facility=str(d.facility);var required=2 if facility.ends_with("_2") else 1
			facility=facility.trim_suffix("_2")
			if EconomyRules.building_level(city,facility)<required:return fail("需要设施：%s %d级"%[content.definition("buildings",facility).name,required])
			if not elite==null:
				var e=content.definition("elite_variants",str(elite))
				if e.is_empty() or e.base_unit!=d.id or stack>e.max_stack:return fail("精锐编队无效")
				if not f.profile_snapshot.elite_unlocks.has(elite) or int(f.profile_snapshot.tech_ranks.get(e.required_tech,0))<e.required_rank:return fail("尚未解锁精锐兵种")
				if SnapshotReferenceAccess023.count_units(state,owner,d.id,elite)>=e.per_faction_cap:return fail("精锐数量已达上限")
				if state.mode=="legion" and LegionRules.elite_count(state,owner)>=int(content.scenarios[state.scenario_id].elite_slots):return fail("精锐数量超过本题名额")
			elif d.per_faction_cap>0 and SnapshotReferenceAccess023.count_units(state,owner,d.id)>=d.per_faction_cap:return fail("装备数量已达上限")
			if city.recruit_queue.size()>=3:return fail("征募队列已满")
			if city.recruit_reserve<10*stack:return fail("本地兵源不足")
			var cost=EconomyRules.recruit_cost(state,owner,d.id,stack,elite,content)
			if not SnapshotReferenceAccess023.can_pay(state,owner,cost):return fail("征募资源不足")
			return {"valid":true,"cost":cost,"phases":d.build_turns}
		"Build","UpgradeCity":
			if not city.construction_queue.is_empty() or city.construction_action_used:return fail("本城建设行动已占用")
			var id="city_level" if type=="UpgradeCity" else str(command.get("def_id",""));var cost={};var phases=1
			if id=="city_level":
				if city.level>=3:return fail("城市已到最高等级")
				var d=content.tables.city_levels[int(city.level)]
				cost={"cash":d.upgrade_cost_cash,"arms":d.upgrade_cost_arms};phases=d.upgrade_turns
			else:
				var d=content.definition("buildings",id)
				if d.is_empty():return fail("设施无效")
				var level=EconomyRules.building_level(city,id)+1
				for b in city.buildings:
					if b.def_id==id and b.damaged:level=b.level
				if level>2:return fail("设施已到最高等级")
				var occupied=0
				for b in city.buildings:occupied+=int(content.definition("buildings",b.def_id).slot_cost)
				if level==1 and occupied+int(d.slot_cost)>4:return fail("城市四个设施槽已满")
				var ld=d.level_definitions[level-1]
				if city.level<ld.min_city_level:return fail("需要更高等级城市")
				if id=="station" and not state.map.rail_nodes.any(func(n):return n.city_id==city.id):return fail("只能在既有铁路节点修车站")
				if id=="port" and not city.port:return fail("此城不是史实港口节点")
				if id=="airfield" and not f.airfield_whitelist.has(city.id):return fail("本剧本未开放此城机场")
				cost=ld.cost;phases=ld.build_own_phases
			if not SnapshotReferenceAccess023.can_pay(state,owner,cost):return fail("建设资源不足")
			return {"valid":true,"cost":cost,"phases":phases}
		"CancelQueue":
			var group=city.construction_queue if command.get("construction",false) else city.recruit_queue
			return {"valid":true} if group.any(func(q):return q.id==command.get("queue_id")) else fail("队列已经变化")
		"DemolishBuilding":
			if city.construction_action_used or not city.construction_queue.is_empty():return fail("须先结束本城建设任务")
			return {"valid":true} if city.buildings.any(func(b):return b.def_id==command.get("def_id","")) else fail("设施不存在")
		"Reinforce":
			if not u.attack_ready or not u.work_ready or u.ap_left<=0:return fail("本阶段已执行终结行动")
			var home=SnapshotReferenceAccess023.at(state,"cities",HexGrid.coordinate(u.position))
			if home.is_empty() or home.owner_id!=owner or u.supply_state!="FULL":return fail("须在本方城市且补给充足")
			var p=EconomyRules.reinforce_preview(state,u,content)
			if p.hp<=0:return fail("兵力完整")
			if home.recruit_reserve<p.population or not SnapshotReferenceAccess023.can_pay(state,owner,p.cost):return fail("补员资源或兵源不足")
			p.valid=true;p.city_id=home.id;return p
		"RepairFort":
			if city.construction_action_used or not city.construction_queue.is_empty():return fail("本城建设行动已占用")
			var p=EconomyRules.fort_repair_preview(state,city,content)
			if p.hp<=0:return fail("城防完整")
			if not SnapshotReferenceAccess023.can_pay(state,owner,p.cost):return fail("修复资源不足")
			p.valid=true;return p
		"RailTransport":
			if u.moved_this_phase or u.attacked_this_phase or u.transported_this_phase or not u.attack_ready or u.ap_left<=0:return fail("铁路运输须由尚未行动的部队执行")
			if u.def_id=="armored_train" or MovementRules.domain_of(u,content)!="land":return fail("该兵种不使用抽象铁路运输")
			var source=SnapshotReferenceAccess023.at(state,"cities",HexGrid.coordinate(u.position));var dest=SnapshotReferenceAccess023.find(state,"cities",str(command.get("destination_id","")))
			if source.is_empty() or dest.is_empty() or source.id==dest.id or source.owner_id!=owner or EconomyRules.building_level(source,"station")==0:return fail("请选择起点与终点车站")
			if not SnapshotReferenceAccess023.at(state,"units",HexGrid.coordinate(dest.position)).is_empty():return fail("终点车站已有部队")
			var cost=LogisticsRules.rail_cost(state,u,content)
			if f.transport_pool<cost:return fail("铁路运力不足")
			var route=LogisticsRules.rail_route(state,owner,source.id,dest.id,cost,content)
			if route.is_empty():return fail("线路受损、封锁或区间运力不足")
			return {"valid":true,"cost":cost,"route":route}
		"EngineerWork":
			if u.def_id!="engineer" or not u.work_ready or not u.attack_ready or u.ap_left<=0:return fail("需要尚可工作的工兵")
			var edge=edge_by_id(state,str(command.get("edge_id","")))
			if edge.is_empty() or not edge.path_hexes.any(func(p):return HexGrid.distance(HexGrid.coordinate(p),HexGrid.coordinate(u.position))<=1):return fail("工兵须靠近目标线路")
			if state.engineer_jobs.any(func(j):return j.unit_id==u.id or j.edge_id==edge.id):return fail("线路或工兵已有抢修任务")
			if command.get("action","repair")=="demolish":return {"valid":edge.damage=="intact","reason":"线路已经损坏"}
			if edge.damage=="intact":return fail("线路完整")
			var cost=content.rules.economy.bridge_repair_cost.duplicate() if edge.is_bridge else content.rules.economy.rail_repair_cost.duplicate()
			var phases=int(cost.own_phases);cost.erase("own_phases");cost=EffectRules.reduced_cost(cost,EffectRules.technology(state,owner,"repair_cost_reduction",u,content))
			if not SnapshotReferenceAccess023.can_pay(state,owner,cost):return fail("抢修资源不足")
			return {"valid":true,"cost":cost,"phases":phases}
		"CancelWork":
			var job=SnapshotReferenceAccess023.find(state,"engineer_jobs",str(command.get("job_id","")))
			return {"valid":true} if not job.is_empty() and job.owner_id==owner else fail("抢修任务无效")
		"Embark":
			var ship=SnapshotReferenceAccess023.find(state,"units",str(command.get("ship_id","")))
			if ship.is_empty() or ship.def_id!="transport_ship" or ship.owner_id!=owner or ship.position==null:return fail("请选择本方运输船")
			if ship.ap_left<=0 or not ship.attack_ready:return fail("运输船本阶段已执行终结行动")
			if MovementRules.domain_of(u,content)!="land" or u.def_id=="armored_train" or u.ap_left<=0 or not u.attack_ready:return fail("部队无法装载")
			var home=SnapshotReferenceAccess023.nearest_city(state,HexGrid.coordinate(u.position),owner)
			if home.is_empty() or not home.port or HexGrid.distance(HexGrid.coordinate(home.position),HexGrid.coordinate(u.position))>1 or HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(ship.position))>1:return fail("装船须在本方港口的相邻陆水格")
			var cargo=0
			for passenger in state.units:
				if passenger.cargo_parent_id==ship.id:cargo+=passenger.stack
			return {"valid":true} if cargo+u.stack<=3 else fail("船舱容量三层编队已满")
		"Disembark":
			if u.cargo_parent_id==null or not u.get("cargo_actions_ready",true) or not valid_hex(command.get("target_hex")):return fail("请选择尚可卸载的部队与登陆格")
			if state.objectives.any(func(o):return o.type=="disembark" and o.target_ids.has(u.id)) and not u.get("cargo_sailed",false):return fail("跨江演习须先驾驶运输船航行，再卸载")
			var ship=SnapshotReferenceAccess023.find(state,"units",u.cargo_parent_id);var hex=HexGrid.coordinate(command.target_hex);var cell=SnapshotReferenceAccess023.cell(state,hex)
			if ship.is_empty() or ship.position==null or cell.is_empty() or HexGrid.distance(hex,HexGrid.coordinate(ship.position))!=1 or not VisibilityRules.hex_visible(state,owner,hex):return fail("登陆格须为可见相邻陆地")
			if content.definition("terrains",cell.terrain_id).get("cost_foot",0)==0 or not SnapshotReferenceAccess023.at(state,"units",hex).is_empty():return fail("登陆格无法停驻")
			var port=SnapshotReferenceAccess023.nearest_city(state,hex,owner)
			return {"valid":true} if port.get("port",false) and HexGrid.distance(hex,HexGrid.coordinate(port.position))<=1 else fail("须在本方港口卸载")
		"AssignGeneral":
			var g=SnapshotReferenceAccess023.find(state,"generals",str(command.get("general_id","")))
			if g.is_empty() or g.owner_id!=owner or g.injured_this_match or g.get("withdrawn_this_match",false) or g.assigned_unit_id!=null or g.unassign_cooldown>0 or not f.general_whitelist.has(g.id):return fail("将领本局无法任命")
			return {"valid":true} if u.general_id==null and not u.moved_this_phase and not u.attacked_this_phase and not u.general_assignment_lock and u.ap_left>0 else fail("需要尚未行动且没有将领的部队")
		"UnassignGeneral":
			var home=SnapshotReferenceAccess023.at(state,"cities",HexGrid.coordinate(u.position))
			return {"valid":true} if u.general_id!=null and not home.is_empty() and home.owner_id==owner and u.supply_state=="FULL" and not u.general_assignment_lock else fail("解除任命须在本方补给城市")
		"ActivateSkill":return skill_preview(state,u,command)
		"SetSupplyPriority":return {"valid":true} if int(command.get("priority",-1)) in [0,1,2] else fail("补给优先级无效")
		"AirRecon","AirBomb":
			if EconomyRules.building_level(city,"airfield")==0 or not f.airfield_whitelist.has(city.id) or city.air_sorties_left<=0 or f.air_sorties_left<=0:return fail("机场或出动次数不可用")
			if not valid_hex(command.get("target_hex")) or SnapshotReferenceAccess023.cell(state,HexGrid.coordinate(command.target_hex)).is_empty():return fail("航空目标无效")
			if HexGrid.distance(HexGrid.coordinate(city.position),HexGrid.coordinate(command.target_hex))>8:return fail("超出机场八格作战范围")
			if type=="AirBomb":
				if state.weather.current=="rain":return fail("雨天停飞轰炸任务")
				if not VisibilityRules.hex_visible(state,owner,HexGrid.coordinate(command.target_hex)):return fail("须先侦察目标")
				var target=SnapshotReferenceAccess023.at(state,"units",HexGrid.coordinate(command.target_hex));var tc=SnapshotReferenceAccess023.at(state,"cities",HexGrid.coordinate(command.target_hex))
				if not ((not target.is_empty() and SnapshotReferenceAccess023.hostile(state,owner,target.owner_id)) or (not tc.is_empty() and SnapshotReferenceAccess023.hostile(state,owner,tc.owner_id) and tc.fort_hp>0)):return fail("轰炸目标须为敌军或敌方城防")
			var cost=content.rules.logistics.bomb_cost if type=="AirBomb" else content.rules.logistics.recon_cost
			return {"valid":true,"cost":cost} if SnapshotReferenceAccess023.can_pay(state,owner,cost) else fail("航空资源不足")
		"Trade":
			var resource=str(command.get("resource",""));var amount=int(command.get("amount",0))
			if f.trade_orders_left<=0 or (EconomyRules.building_level(city,"market")==0 and EconomyRules.building_level(city,"port")==0):return fail("需要市场或港口与剩余交易次数")
			if resource not in ["food","arms"] or amount<1 or amount>40:return fail("单次交易须为1–40单位粮食或军械")
			var price=4 if resource=="food" else 6;var cost={"cash":price*amount} if command.get("buy",true) else {resource:amount}
			return {"valid":true,"cost":cost} if SnapshotReferenceAccess023.can_pay(state,owner,cost) else fail("交易资源不足")
		"Diplomacy":return diplomacy_preview(state,command)
		"UndoMove":return {"valid":true} if state.last_move_inverse!=null else fail("仅未发现新情报的最近一次移动可撤销")
	return fail("未知行动")

func valid_hex(value: Variant) -> bool:return value is Dictionary and value.get("q") is int and value.get("r") is int

func edge_by_id(state: Dictionary, id: String) -> Dictionary:
	for edge in state.map.rail_edges:
		if edge.id==id:return edge
	return {}

func attack_preview(state: Dictionary, u: Dictionary, command: Dictionary, skill_id: String = "") -> Dictionary:
	if not u.attack_ready or u.ammo<=0 or u.cargo_parent_id!=null or u.general_assignment_lock:return fail("主攻击已消耗、无弹药或将领刚任命")
	if not valid_hex(command.get("target_hex")):return fail("攻击目标无效")
	var hex=HexGrid.coordinate(command.target_hex)
	if not VisibilityRules.hex_visible(state,u.owner_id,hex):return fail("目标尚未侦察")
	var target=SnapshotReferenceAccess023.at(state,"units",hex);var city=SnapshotReferenceAccess023.at(state,"cities",hex)
	var fort=not city.is_empty() and city.fort_hp>0 and SnapshotReferenceAccess023.hostile(state,u.owner_id,city.owner_id)
	if not fort and (target.is_empty() or not SnapshotReferenceAccess023.hostile(state,u.owner_id,target.owner_id)):return fail("请选择交战阵营目标")
	if not CombatRules.in_range(u,command.target_hex,content):return fail("目标不在武器射程内")
	var d=content.definition("units",u.def_id)
	var target_domain="land" if target.is_empty() else MovementRules.domain_of(target,content)
	if not d.target_domains.has(target_domain):return fail("武器无法攻击此目标类型")
	if d.shore_target_required and target_domain=="land":
		var near=false
		for direction in HexGrid.DIRECTIONS:
			var c=SnapshotReferenceAccess023.cell(state,hex+direction)
			if not c.is_empty() and content.definition("terrains",c.terrain_id).water:near=true
		if not near:return fail("舰炮陆地目标须临水")
	var result=CombatRules.preview(state,u,target,content,city if fort else {},skill_id);result.valid=true;result.target_id=target.get("id");result.city_id=city.get("id") if fort else null
	return result

func skill_preview(state: Dictionary, u: Dictionary, command: Dictionary) -> Dictionary:
	if u.general_id==null or not u.skill_ready or u.general_assignment_lock:return fail("本阶段无可用将领战法")
	var g=SnapshotReferenceAccess023.find(state,"generals",u.general_id);var id=GeneralRules.active_skill(g,content);var d=content.definition("skills",id);var f=SnapshotReferenceAccess023.faction(state,u.owner_id)
	if int(g.cooldowns.get(id,0))>0:return fail("战法冷却中")
	if f.command_points<d.command_cost or not SnapshotReferenceAccess023.can_pay(state,u.owner_id,d.resource_cost):return fail("指挥点或战法资源不足")
	if not EffectRules.scope_matches(d.caster_scope,u,content):return fail("将领战法不适用于此兵种")
	var target=SnapshotReferenceAccess023.find(state,"units",str(command.get("target_id",u.id)))
	if d.consumes_main_attack:
		var attack=attack_preview(state,u,command,id)
		if not attack.valid:return attack
		if id=="assault_order" and (target.is_empty() or target.suppression<60):return fail("强攻目标压制须达60")
		if id=="coordinated_fire":
			var observer=state.units.any(func(v):return v.owner_id==u.owner_id and v.id!=u.id and v.position!=null and HexGrid.distance(HexGrid.coordinate(v.position),HexGrid.coordinate(command.target_hex))<=2 and VisibilityRules.clear_line(state,HexGrid.coordinate(v.position),HexGrid.coordinate(command.target_hex)))
			if not observer:return fail("需要另一支友军近距观察目标")
		attack.skill_id=id;return attack
	if id=="recon_order":
		if not valid_hex(command.get("target_hex")) or HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(command.target_hex))>3:return fail("侦察中心须在施放者三格内")
	else:
		if target.is_empty() or target.owner_id!=u.owner_id or target.position==null or HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(target.position))>1:return fail("战法目标须为相邻本方部队")
		if not EffectRules.scope_matches(d.target_scope,target,content):return fail("战法目标兵种不符")
		if id=="ration_order" and (MovementRules.domain_of(target,content)!="land" or target.food_reserve>=3+EffectRules.technology(state,target.owner_id,"reserve_cap_flat",target,content)):return fail("目标须在可征粮陆地且储粮未满")
		if id=="field_repair" and (target.def_id not in ["armored_car","armored_train"] or target.hp>=target.max_hp):return fail("需要受损装甲车或装甲列车")
		if id=="entrench_order" and target.attacked_this_phase:return fail("目标本阶段已攻击")
		if id=="rail_priority" and target.transported_this_phase:return fail("目标本阶段已运输")
	return {"valid":true,"skill_id":id}

func diplomacy_preview(state: Dictionary, c: Dictionary) -> Dictionary:
	var owner=state.turn_order[state.phase_index];var target=str(c.get("target_faction_id",""));var f=SnapshotReferenceAccess023.faction(state,owner);var other=SnapshotReferenceAccess023.faction(state,target)
	if other.is_empty() or owner==target or other.eliminated:return fail("外交对象无效")
	var relation=SnapshotReferenceAccess023.relation(state,owner,target);var action=c.get("action","")
	if action=="declare_war":
		if f.war_orders_left<=0 or f.transport_used_phase:return fail("本阶段已宣战或借道运输")
		if relation.state!="NEUTRAL":return fail("须先解除或等候条约结束")
	elif action=="aid":
		if f.aid_orders_left<=0 or state.round-relation.last_aid_round<3:return fail("援助次数或三回合间隔不足")
		var amount=c.get("resources",{});var total=0
		for key in amount:
			if key not in ["cash","food","arms"] or amount[key]<0:return fail("援助数额无效")
			total+=int(amount[key])
		if total<=0 or (amount.get("cash",0)>0 and amount.cash<50) or (amount.get("food",0)>0 and amount.food<20) or (amount.get("arms",0)>0 and amount.arms<20):return fail("援助最低现金50、粮食或军械20")
		if not SnapshotReferenceAccess023.can_pay(state,owner,amount):return fail("援助资源不足")
	elif action in ["truce","alliance","break"]:
		if f.diplomacy_orders_left<=0:return fail("本阶段外交提案已用完")
		if action=="break" and (relation.state not in ["TRUCE","ALLIANCE"] or state.round<relation.minimum_until_round or relation.break_at_round>0):return fail("条约最低期限未到或已通知解除")
		if action=="truce" and relation.state!="WAR":return fail("停战仅适用于交战双方")
		if action=="alliance" and relation.state not in ["NEUTRAL","TRUCE"]:return fail("结盟须先停止交战")
	else:return fail("外交行动无效")
	return {"valid":true,"response":DiplomacyRules.acceptance(state,owner,target)}

func resolve(state: Dictionary, command: Dictionary) -> Dictionary:
	var check=preview(state,command)
	if not check.valid:return check
	var next=SnapshotReferenceAccess023.clone_transaction(state);var events: Array=[];var owner=next.turn_order[next.phase_index]
	SnapshotReferenceAccess023.invalidate_occupancy()
	var u=SnapshotReferenceAccess023.find(next,"units",str(command.get("unit_id","")));var city=SnapshotReferenceAccess023.find(next,"cities",str(command.get("city_id","")));var type=command.type
	var previous=next.last_move_inverse;next.last_move_inverse=null
	match type:
		"Move":
			var old_unit=u.duplicate(true);var old_statuses=next.statuses.duplicate(true);var before_sight=[];var old_visible_enemies={}
			for enemy in next.units:
				if enemy.owner_id!=owner and VisibilityRules.unit_visible(next,owner,enemy):old_visible_enemies[enemy.id]=true
			for sight in next.visibility:
				if sight.faction_id==owner:before_sight=sight.explored_cell_ids.duplicate()
			MovementRules.resolve_move(next,u,check.path,content,events);VisibilityRules.refresh(next,content)
			var after_sight=[]
			for sight in next.visibility:
				if sight.faction_id==owner:after_sight=sight.explored_cell_ids
			var new_enemy=next.units.any(func(enemy):return enemy.owner_id!=owner and VisibilityRules.unit_visible(next,owner,enemy) and not old_visible_enemies.has(enemy.id))
			if not new_enemy and after_sight.size()==before_sight.size() and not events.any(func(e):return e.type in ["CityCaptured","UnitContact"]):next.last_move_inverse={"unit_id":u.id,"unit_before":old_unit,"statuses_before":old_statuses}
		"Attack":CombatRules.resolve(next,u,SnapshotReferenceAccess023.find(next,"units",str(check.target_id)),content,events,SnapshotReferenceAccess023.find(next,"cities",str(check.city_id)))
		"Recruit":EconomyRules.recruit(next,city,command,content,events)
		"Build","UpgradeCity":EconomyRules.construction(next,city,"city_level" if type=="UpgradeCity" else command.def_id,content,events)
		"CancelQueue":EconomyRules.cancel_queue(next,city,command.queue_id,command.get("construction",false),content,events)
		"DemolishBuilding":
			city.buildings=city.buildings.filter(func(b):return b.def_id!=command.def_id);city.construction_action_used=true
			city.fort_max_hp=mini(340,int(content.tables.city_levels[int(city.level)-1].fort_hp)+40*EconomyRules.building_level(city,"fortification"));city.fort_hp=mini(city.fort_hp,city.fort_max_hp)
			events.append({"type":"BuildingDemolished","city_id":city.id,"def_id":command.def_id})
		"Reinforce":EconomyRules.reinforce(next,u,SnapshotReferenceAccess023.find(next,"cities",check.city_id),content,events)
		"RepairFort":SnapshotReferenceAccess023.pay(next,owner,check.cost,events,"城防修复");city.fort_hp+=check.hp;city.erase("fort_breached_by");city.construction_action_used=true;events.append({"type":"FortRepaired","city_id":city.id,"amount":check.hp})
		"RailTransport":LogisticsRules.transport(next,u,SnapshotReferenceAccess023.find(next,"cities",command.destination_id),check.route,content,events)
		"EngineerWork":
			var edge=edge_by_id(next,command.edge_id)
			if command.get("action","repair")=="demolish":LogisticsRules.demolish(next,edge,owner,content,events)
			else:
				SnapshotReferenceAccess023.pay(next,owner,check.cost,events,"铁路抢修")
				next.engineer_jobs.append({"id":StateBuilder.next_id(next,"job"),"unit_id":u.id,"owner_id":owner,"edge_id":edge.id,"remaining_own_phases":check.phases,"total_own_phases":check.phases,"paid_cost":check.cost,"paused":false})
			u.ap_left=0;u.attack_ready=false;u.work_ready=false
		"CancelWork":
			var job=SnapshotReferenceAccess023.find(next,"engineer_jobs",command.job_id);var refund={}
			for key in job.paid_cost:refund[key]=int(job.paid_cost[key]*job.remaining_own_phases/maxi(1,job.total_own_phases)*.5)
			SnapshotReferenceAccess023.add_resources(next,owner,refund,events,"取消抢修");next.engineer_jobs.erase(job)
		"Embark":
			u.cargo_parent_id=command.ship_id;u.position=null;u.ap_left=0;u.attack_ready=false;u.cargo_actions_ready=false;u.cargo_sailed=false
			var ship=SnapshotReferenceAccess023.find(next,"units",command.ship_id);ship.ap_left=0;ship.attack_ready=false
			events.append({"type":"Embarked","unit_id":u.id,"ship_id":command.ship_id})
		"Disembark":
			var ship=SnapshotReferenceAccess023.find(next,"units",u.cargo_parent_id);ship.ap_left=0;ship.attack_ready=false
			u.position=command.target_hex.duplicate();u.cargo_parent_id=null;u.ap_left=0;u.attack_ready=false;u.moved_this_phase=true;u.cargo_actions_ready=false
			events.append({"type":"Disembarked","unit_id":u.id,"position":u.position})
		"AssignGeneral":GeneralRules.assign(next,u,SnapshotReferenceAccess023.find(next,"generals",command.general_id),content,events)
		"UnassignGeneral":GeneralRules.unassign(next,u,content,events)
		"ActivateSkill":GeneralRules.skill(next,u,command,content,events)
		"SetSupplyPriority":u.supply_priority=command.priority
		"AirRecon","AirBomb":GeneralRules.air(next,city,command.target_hex,type=="AirBomb",content,events)
		"Trade":
			SnapshotReferenceAccess023.pay(next,owner,check.cost,events,"军需交易")
			var income={command.resource:int(command.amount)} if command.get("buy",true) else {"cash":int(command.amount)*(2 if command.resource=="food" else 3)}
			SnapshotReferenceAccess023.add_resources(next,owner,income,events,"军需交易");SnapshotReferenceAccess023.faction(next,owner).trade_orders_left-=1
		"Diplomacy":DiplomacyRules.act(next,owner,command,events)
		"UndoMove":
			var undo=previous;var restored=SnapshotReferenceAccess023.find(next,"units",undo.unit_id)
			for key in undo.unit_before:restored[key]=undo.unit_before[key]
			next.statuses=undo.statuses_before;events.append({"type":"MoveUndone","unit_id":restored.id})
		"EndPhase":TurnRules.end_phase(next,content,events)
	for e in events:
		if e.type=="UnitMoved" and not u.is_empty() and u.def_id=="transport_ship":
			for passenger in next.units:
				if passenger.cargo_parent_id==u.id:passenger.cargo_sailed=true
		var ours=e.get("owner_id","")==next.player_faction_id
		match e.type:
			"UnitDefeated":
				if ours:next.metrics.losses+=1
				elif e.get("defeated_by","")==next.player_faction_id and SnapshotReferenceAccess023.hostile(state,next.player_faction_id,e.owner_id):next.metrics.kills+=1
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
				var attacker=SnapshotReferenceAccess023.find(state,"units",str(e.get("attacker_id")));var target=SnapshotReferenceAccess023.find(state,"units",str(e.get("unit_id")))
				if not attacker.is_empty() and not target.is_empty() and content.definition("units",attacker.def_id).family=="artillery":
					var observer=state.units.any(func(v):return v.owner_id==owner and v.id!=attacker.id and v.position!=null and HexGrid.distance(HexGrid.coordinate(v.position),HexGrid.coordinate(target.position))<=2 and not MovementRules.adjacent_hostile(state,v,HexGrid.coordinate(v.position),content))
					if observer:next.metrics.protected_observer_artillery_hits=int(next.metrics.get("protected_observer_artillery_hits",0))+1
	SnapshotReferenceAccess023.invalidate_occupancy()
	next.state_version=state.state_version+1
	if command.get("debug",false):next.debug_match=true
	VisibilityRules.refresh(next,content);VictoryRules.check(next,content,events)
	SnapshotReferenceAccess023.freeze_map(next.map)
	for e in events:
		e.round=next.round;e.sequence=next.state_version
		next.event_log.append(e)
	while next.event_log.size()>250:next.event_log.pop_front()
	return {"valid":true,"state":next,"events":events,"preview":check,"command":command.duplicate(true)}
