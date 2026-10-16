class_name VictoryRules
extends RefCounted

static func check(state: Dictionary, content: ContentRegistry, events: Array) -> void:
	if state.status!="playing":return
	var recipe=content.scenarios[state.scenario_id];var player=state.player_faction_id
	if state.get("protected_commander_id")!=null:
		var formation=StateAccess.find(state,"units",state.protected_commander_id)
		if formation.is_empty():finish(state,"",events,"主将所属编队损失");return
		if formation.owner_id!=player:finish(state,"",events,"主将所属编队脱离本方指挥");return
	if state.get("protected_general_id")!=null:
		var commander=StateAccess.find(state,"generals",state.protected_general_id)
		if commander.get("injured_this_match",false):finish(state,"",events,"主将战败");return
		if commander.is_empty() or commander.get("owner_id","")!=player or commander.get("withdrawn_this_match",false):finish(state,"",events,"主将脱离本方指挥");return
	for o in state.objectives:
		if o.get("protected",false):
			for id in o.target_ids:
				var formation=StateAccess.find(state,"units",id)
				if formation.is_empty():finish(state,"",events,"保护编队损失");return
				if formation.owner_id!=player:finish(state,"",events,"保护编队脱离本方指挥");return
	if state.mode!="conquest":
		for o in state.objectives:
			match o.type:
				"capture":o.progress=o.target_ids.filter(func(id):return StateAccess.find(state,"cities",id).get("owner_id","")==player).size()
				"hold":
					var phase=StateAccess.faction(state,player).own_phase_index
					if phase!=o.get("last_checked_phase",phase):
						o.progress=o.progress+1 if o.target_ids.all(func(id):return StateAccess.find(state,"cities",id).get("owner_id","")==player) else 0
					o.last_checked_phase=phase
				"repair":
					o.progress=0
					for edge in state.map.rail_edges:
						if o.target_ids.has(edge.id) and edge.damage=="intact":o.progress+=1
				"escort":
					var u=StateAccess.find(state,"units",o.target_ids[0])
					o.progress=1 if u.position!=null and HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(o.destination))<=1 else 0
				"disembark":
					var u=StateAccess.find(state,"units",o.target_ids[0])
					o.progress=1 if u.cargo_parent_id==null and u.position!=null and HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(o.destination))<=1 else 0
				"destroy":
					var surviving_targets=0
					for target_id in o.target_ids:
						if not StateAccess.find(state,"units",str(target_id)).is_empty():surviving_targets+=1
					o.progress=1 if not o.target_ids.is_empty() and surviving_targets==0 else 0
				"capture_commander":
					var commander=StateAccess.find(state,"generals",str(o.target_ids[0]) if not o.target_ids.is_empty() else "")
					if commander.is_empty():o.progress=1 if o.get("optional_if_absent",false) else 0
					else:o.progress=1 if commander.get("injured_this_match",false) or commander.get("withdrawn_this_match",false) or commander.get("owner_id","")==player else 0
				"metric":o.progress=int(state.metrics.get(o.metric,0))
				"survive":o.progress=1 if state.round>=mini(8,int(recipe.round_limit)) else 0
		if state.objectives.all(func(o):return o.progress>=o.required):finish(state,player,events,"任务完成");return
		if state.round>recipe.round_limit:finish(state,"",events,"任务期限已过");return
		if not state.units.any(func(u):return u.owner_id==player):finish(state,"",events,"部队全部损失")
		return
	var defeated: Array=[]
	for f in state.factions:
		if f.eliminated:continue
		var cities=state.cities.filter(func(c):return c.owner_id==f.id and (c.level>=2 or c.get("command_center",false)))
		if cities.is_empty():
			var effective=false
			var targets=state.cities.filter(func(c):return c.key_city and StateAccess.hostile(state,f.id,c.owner_id))
			for u in state.units:
				if u.owner_id!=f.id or u.position==null or u.cargo_parent_id!=null or u.hp*1000<u.max_hp*int(content.rules.victory.effective_counterattack_min_hp_permille) or not content.definition("units",u.def_id).can_occupy:continue
				if MovementRules.counterattack_reaches(state,u,targets,content,int(content.rules.victory.counterattack_max_movement_phases)):effective=true;break
			if not effective:defeated.append(f.id)
	defeated.sort()
	for owner in defeated:withdraw(state,owner,events)
	if StateAccess.faction(state,player).eliminated:finish(state,"",events,"失去战略反击能力");return
	var keys=state.cities.filter(func(c):return c.key_city)
	var groups=alliance_groups(state)
	for group in groups:
		if not keys.is_empty() and keys.all(func(c):return group.has(c.owner_id)):
			finish(state,group[0],events,"同盟战略节点统一" if group.size()>1 else "战略节点统一",group);return
	if state.round>recipe.round_limit:
		var scores: Array=[]
		var weights=content.rules.victory
		for group in groups:
			var key_count=0;var hp=0;var score=0
			for c in state.cities:
				if group.has(c.owner_id):
					var i=EconomyRules.income(c,content);score+=i.cash*int(weights.score_income_cash)+i.food*int(weights.score_income_food)+i.arms*int(weights.score_income_arms)
					if c.key_city:key_count+=1
			for u in state.units:
				if group.has(u.owner_id):hp+=u.hp
			score+=key_count*int(weights.score_key_city)+int(hp/int(weights.score_surviving_hp_divisor));scores.append({"id":group[0],"members":group.duplicate(),"score":score,"keys":key_count,"hp":hp})
		scores.sort_custom(func(a,b):
			if a.score!=b.score:return a.score>b.score
			if a.keys!=b.keys:return a.keys>b.keys
			if a.hp!=b.hp:return a.hp>b.hp
			return str(a.id)<str(b.id))
		state.result_scores=scores.duplicate(true)
		finish(state,scores[0].id if not scores.is_empty() else "",events,"征服期限积分结算",scores[0].members if not scores.is_empty() else [])

static func alliance_groups(state: Dictionary) -> Array:
	var pending: Array=state.factions.filter(func(f):return not f.eliminated).map(func(f):return f.id)
	pending.sort();var groups: Array=[]
	while not pending.is_empty():
		var group: Array=[pending.pop_front()];var frontier: Array=group.duplicate()
		while not frontier.is_empty():
			var owner=frontier.pop_front()
			for candidate in pending.duplicate():
				if StateAccess.allied(state,owner,candidate):pending.erase(candidate);group.append(candidate);frontier.append(candidate)
		group.sort()
		# Contradictory treaties may exist in edited/legacy states. Enemy factions
		# never share a result merely because both are allied to a third party.
		var conflict=false
		for a in group:
			for b in group:
				if StateAccess.hostile(state,a,b):conflict=true
		if conflict:
			for owner in group:groups.append([owner])
		else:groups.append(group)
	return groups

static func withdraw(state: Dictionary, owner: String, events: Array) -> void:
	var faction=StateAccess.faction(state,owner);faction.eliminated=true
	var unit_ids: Array=state.units.filter(func(u):return u.owner_id==owner).map(func(u):return u.id)
	var changed=true
	while changed:
		changed=false
		for unit in state.units:
			if unit.cargo_parent_id!=null and unit_ids.has(unit.cargo_parent_id) and not unit_ids.has(unit.id):unit_ids.append(unit.id);changed=true
	unit_ids.sort()
	for unit_id in unit_ids:
		var unit=StateAccess.find(state,"units",unit_id)
		if unit.general_id!=null:
			var general=StateAccess.find(state,"generals",unit.general_id)
			if not general.is_empty():general.assigned_unit_id=null;general.withdrawn_this_match=true
		events.append({"type":"UnitWithdrawn","unit_id":unit_id,"owner_id":unit.owner_id,"reason":"势力失去战略反击能力"})
	state.units=state.units.filter(func(u):return not unit_ids.has(u.id))
	for general in state.generals:
		if general.owner_id==owner:general.assigned_unit_id=null;general.withdrawn_this_match=true
	state.statuses=state.statuses.filter(func(s):return not unit_ids.has(s.target_id) and s.source_owner_id!=owner)
	state.engineer_jobs=state.engineer_jobs.filter(func(j):return j.owner_id!=owner and not unit_ids.has(j.unit_id))
	for city in state.cities:
		if city.owner_id==owner:city.recruit_queue.clear();city.construction_queue.clear()
	for aid in state.pending_aid.duplicate():
		if aid.receiver_id==owner:
			var sender=StateAccess.faction(state,aid.sender_id)
			if not sender.is_empty() and not sender.eliminated:
				var refund={}
				for key in aid.resources:refund[key]=int(aid.resources[key]/2)
				StateAccess.add_resources(state,aid.sender_id,refund,events,"援助对象撤离退回")
		if aid.receiver_id==owner or aid.sender_id==owner:state.pending_aid.erase(aid)
	StateAccess.invalidate_occupancy()
	events.append({"type":"FactionEliminated","owner_id":owner,"withdrawn_unit_ids":unit_ids})

static func finish(state: Dictionary, winner: String, events: Array, reason: String, members: Array = []) -> void:
	if members.is_empty() and not winner.is_empty():members=[winner]
	state.status="won" if members.has(state.player_faction_id) else "lost";state.winner_id=winner if not winner.is_empty() else null;state.result_reason=reason
	state.winning_faction_ids=members.duplicate()
	state.result_stars=1
	if state.status=="won":
		var speed=state.round<=int(state.get("star_rounds_at_most",ceil(float(state.get("round_limit",20))*.7)))
		if speed:state.result_stars+=1
		if state.metrics.losses*1000<=state.initial_player_count*int(state.get("star_loss_ratio_permille_at_most",300)):state.result_stars+=1
	events.append({"type":"MatchFinished","winner_id":state.winner_id,"winning_faction_ids":members.duplicate(),"reason":reason,"stars":state.result_stars})
