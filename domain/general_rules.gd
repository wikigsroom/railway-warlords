class_name GeneralRules
extends RefCounted

static func active_skill(general: Dictionary, content: ContentRegistry) -> String:
	return str(general.get("active_skill_id",content.definition("generals",general.id).active_skill))

static func assign(state: Dictionary, u: Dictionary, general: Dictionary, content: ContentRegistry, events: Array) -> void:
	var rate=1000+30*int(general.rank)
	var hp_rate=float(u.hp)/u.max_hp
	u.general_id=general.id;general.assigned_unit_id=u.id
	u.max_hp=CombatRules.rational_round([[int(EffectRules.scaled_definition(u,content).hp)*u.stack,1],[rate,1000]])
	u.hp=maxi(1,int(round(hp_rate*u.max_hp)));u.attack_ready=false;u.general_assignment_lock=true
	events.append({"type":"GeneralAssigned","unit_id":u.id,"general_id":general.id})

static func unassign(state: Dictionary, u: Dictionary, content: ContentRegistry, events: Array) -> void:
	var general=StateAccess.find(state,"generals",u.general_id);var fraction=float(u.hp)/u.max_hp
	general.assigned_unit_id=null;general.unassign_cooldown=1;u.general_id=null
	u.max_hp=int(EffectRules.scaled_definition(u,content).hp)*u.stack;u.hp=maxi(1,int(round(fraction*u.max_hp)))
	u.attack_ready=false;u.general_assignment_lock=true
	events.append({"type":"GeneralUnassigned","unit_id":u.id,"general_id":general.id})

static func skill(state: Dictionary, caster: Dictionary, command: Dictionary, content: ContentRegistry, events: Array) -> void:
	var general=StateAccess.find(state,"generals",caster.general_id)
	var id=active_skill(general,content);var d=content.definition("skills",id)
	var rank=int(general.skill_ranks.get(id,1));var value=CombatRules.rational_round([[d.value,1],[d.rank_scale_permille[rank-1],1000]])
	StateAccess.faction(state,caster.owner_id).command_points-=d.command_cost
	StateAccess.pay(state,caster.owner_id,d.resource_cost,events,"将领战法")
	general.cooldowns[id]=d.cooldown_own_phases;caster.skill_ready=false
	var target=StateAccess.find(state,"units",str(command.get("target_id",caster.id)))
	if d.consumes_main_attack:
		var city=StateAccess.at(state,"cities",HexGrid.coordinate(command.target_hex))
		CombatRules.resolve(state,caster,target,content,events,city,id)
		if id=="cavalry_sweep" and caster.hp>0:caster.ap_left=mini(2,int(content.definition("units",caster.def_id).ap))
	else:
		match d.effect:
			"food_reserve_restore":target.food_reserve=mini(3+EffectRules.technology(state,target.owner_id,"reserve_cap_flat",target,content),target.food_reserve+value)
			"defense_flat","transport_cost_reduction":
				state.statuses.append({"id":StateBuilder.next_id(state,"status"),"def_id":"fortified_order" if d.effect=="defense_flat" else "rail_priority_order","target_id":target.id,"source_owner_id":caster.owner_id,"value":value,"expires_owner_phase":StateAccess.faction(state,caster.owner_id).own_phase_index+1})
			"reveal_radius":
				for sight in state.visibility:
					if sight.faction_id==caster.owner_id:sight.temporary_reveals.append({"center":command.get("target_hex",caster.position).duplicate(),"radius":value,"expires_owner_phase":StateAccess.faction(state,caster.owner_id).own_phase_index+1})
			"heal_hp":target.hp=mini(target.max_hp,target.hp+value)
	events.append({"type":"SkillActivated","unit_id":caster.id,"owner_id":caster.owner_id,"position":command.get("target_hex",target.get("position",caster.position)),"skill_id":id,"target_id":target.get("id")})

static func refresh(state: Dictionary, owner: String, content: ContentRegistry) -> void:
	for g in state.generals:
		if g.owner_id!=owner:continue
		g.unassign_cooldown=maxi(0,g.unassign_cooldown-1)
		for key in g.cooldowns:g.cooldowns[key]=maxi(0,g.cooldowns[key]-1)

static func air_bonus(state: Dictionary, city: Dictionary, content: ContentRegistry) -> int:
	var bonus=0
	for g in state.generals:
		if g.owner_id!=city.owner_id or g.assigned_unit_id==null:continue
		var u=StateAccess.find(state,"units",g.assigned_unit_id)
		if u.is_empty() or u.position==null or HexGrid.distance(HexGrid.coordinate(u.position),HexGrid.coordinate(city.position))>1:continue
		var d=content.definition("generals",g.id);var amount=int(d.stars.aviation)*20
		var skill=content.definition("skills",d.passive_skill)
		if skill.effect=="support_damage_bonus":amount+=CombatRules.rational_round([[skill.value,1],[skill.rank_scale_permille[int(g.skill_ranks.get(skill.id,1))-1],1000]])
		bonus=maxi(bonus,amount)
	return mini(400,bonus+EffectRules.technology(state,city.owner_id,"support_damage_bonus",{},content))

static func air(state: Dictionary, city: Dictionary, hex: Dictionary, bomb: bool, content: ContentRegistry, events: Array) -> void:
	StateAccess.pay(state,city.owner_id,content.rules.logistics.bomb_cost if bomb else content.rules.logistics.recon_cost,events,"航空轰炸" if bomb else "航空侦察")
	city.air_sorties_left-=1;StateAccess.faction(state,city.owner_id).air_sorties_left-=1
	if not bomb:
		for sight in state.visibility:
			if sight.faction_id==city.owner_id:sight.temporary_reveals.append({"center":hex.duplicate(),"radius":2+EffectRules.technology(state,city.owner_id,"recon_radius_flat",{},content),"expires_owner_phase":StateAccess.faction(state,city.owner_id).own_phase_index+1})
	else:
		var amount=CombatRules.rational_round([[28,1],[1000+air_bonus(state,city,content),1000]])
		var target_city=StateAccess.at(state,"cities",HexGrid.coordinate(hex));var target=StateAccess.at(state,"units",HexGrid.coordinate(hex))
		if not target_city.is_empty() and target_city.fort_hp>0:
			var fort_hit=mini(target_city.fort_hp,CombatRules.rational_round([[amount,1],[600,1000]]));target_city.fort_hp-=fort_hit
			events.append({"type":"FortDamaged","city_id":target_city.id,"position":target_city.position.duplicate(),"from":city.position.duplicate(),"source_city_id":city.id,"amount":fort_hit})
			amount=CombatRules.rational_round([[fort_hit,1],[150,1000]])
		if not target.is_empty():
			amount=mini(target.hp,amount);target.hp-=amount;target.suppression=mini(100,target.suppression+20)
			events.append({"type":"DamageApplied","unit_id":target.id,"position":target.position.duplicate(),"from":city.position.duplicate(),"source_city_id":city.id,"amount":amount,"suppression":20,"counter":false})
			if target.hp<=0:CombatRules.defeat(state,target,events,content,city.owner_id)
	events.append({"type":"AirBombed" if bomb else "AirRecon","city_id":city.id,"owner_id":city.owner_id,"from":city.position.duplicate(),"position":hex.duplicate()})
