class_name CombatRules
extends RefCounted

static func gcd(a: int, b: int) -> int:
	while b != 0:
		var remainder: int = a % b
		a = b
		b = remainder
	return maxi(1, a)

static func rational_round(factors: Array) -> int:
	var numerators: Array = []
	var denominators: Array = []
	for pair in factors:
		numerators.append(int(pair[0]))
		denominators.append(int(pair[1]))
	for i in range(numerators.size()):
		for j in range(denominators.size()):
			var divisor = gcd(numerators[i], denominators[j])
			numerators[i] = int(numerators[i] / divisor)
			denominators[j] = int(denominators[j] / divisor)
	var n: int = 1
	var d: int = 1
	for value in numerators:
		n *= int(value)
	for value in denominators:
		d *= int(value)
	return int((2*n+d)/(2*d))

static func suppression_tier(value: int, rules: Dictionary) -> int:
	var tier: int = 0
	for threshold in rules.combat.suppression_thresholds:
		if value >= int(threshold):
			tier += 1
	return tier

static func attack_bonus(state: Dictionary, attacker: Dictionary, content: ContentRegistry, skill_id: String = "") -> int:
	var result = mini(150, EffectRules.technology(state, attacker.owner_id, "attack_bonus", attacker, content))
	result += EffectRules.general_bonus(state, attacker, "attack_bonus", content)
	result += VeterancyRules.bonus(attacker)
	var c = content.rules.combat
	result += int(c.suppression_attack_penalties_permille[suppression_tier(attacker.suppression, content.rules)])
	if not skill_id.is_empty():
		var skill = content.definition("skills", skill_id)
		if skill.effect == "attack_bonus":
			var general = StateAccess.find(state, "generals", str(attacker.general_id))
			var rank = int(general.get("skill_ranks", {}).get(skill_id, 1))
			result += rational_round([[skill.value,1],[skill.rank_scale_permille[rank-1],1000]])
	if state.difficulty == "hard" and attacker.owner_id != state.player_faction_id:
		result += 100
	return clampi(result, int(c.attack_bonus_cap_min), int(c.attack_bonus_cap_max))

static func defense(state: Dictionary, defender: Dictionary, content: ContentRegistry) -> int:
	var definition = EffectRules.scaled_definition(defender, content)
	var result = int(definition.defense)
	result += EffectRules.technology(state, defender.owner_id, "defense_flat", defender, content)
	result += EffectRules.general_bonus(state, defender, "defense_flat", content)
	if defender.position != null:
		var cell = StateAccess.cell(state, HexGrid.coordinate(defender.position))
		result += int(content.definition("terrains", cell.get("terrain_id", "plain")).get("cover_defense", 0))
	result += mini(12, EffectRules.status_bonus(state, defender, "defense_flat"))
	return clampi(result, 0, int(content.rules.combat.defense_cap))

static func damage(state: Dictionary, attacker: Dictionary, target: Dictionary, content: ContentRegistry, counter: bool = false, fort: bool = false, skill_id: String = "") -> int:
	var definition = EffectRules.scaled_definition(attacker, content)
	if definition.attack == 0:
		return 0
	var c = content.rules.combat
	var affinity = int(content.tables.counter_matrix.fort_multiplier_permille[attacker.def_id]) if fort else int(content.tables.counter_matrix.values_permille[attacker.def_id][target.def_id])
	if fort:
		affinity = mini(2400, affinity + EffectRules.technology(state, attacker.owner_id, "fort_bonus", attacker, content))
	var target_defense = int(c.fort_defense) if fort else defense(state, target, content)
	var factors: Array = [
		[int(definition.attack),1],
		[int(c.base_damage_permille),1000],
		[1000+int(c.stack_attack_increment_permille)*(int(attacker.stack)-1),1000],
		[1000+attack_bonus(state,attacker,content,skill_id),1000],
		[affinity,1000],
		[int(c.health_base_permille)*int(attacker.max_hp)+int(c.health_scaled_permille)*int(attacker.hp),1000*int(attacker.max_hp)],
		[int(c.supply_permille[attacker.supply_state]),1000],
		[int(c.morale_base_permille)+int(c.morale_per_point_permille)*int(attacker.morale),1000],
		[int(c.defense_divisor),int(c.defense_divisor)+target_defense]]
	if counter:
		factors.append([int(c.counter_permille),1000])
	return maxi(1, rational_round(factors))

static func in_range(attacker: Dictionary, target_position: Dictionary, content: ContentRegistry) -> bool:
	if attacker.position == null:
		return false
	var d = HexGrid.distance(HexGrid.coordinate(attacker.position), HexGrid.coordinate(target_position))
	var definition = content.definition("units", attacker.def_id)
	return d >= int(definition.range_min) and d <= int(definition.range_max)

static func can_counter(state: Dictionary, defender: Dictionary, attacker: Dictionary, content: ContentRegistry) -> bool:
	return defender.hp > 0 and defender.ammo > 0 and defender.counter_left > 0 and defender.suppression < 90 and in_range(defender, attacker.position, content)

static func preview(state: Dictionary, attacker: Dictionary, target: Dictionary, content: ContentRegistry, city: Dictionary = {}, skill_id: String = "", attack_modifier: int = 1000, counter_modifier: int = 1000) -> Dictionary:
	var is_fort: bool = not city.is_empty() and city.fort_hp > 0
	var base_hit = damage(state, attacker, target, content, false, is_fort, skill_id)
	var hit = CombatRandom.scaled(base_hit,attack_modifier)
	var result = {"damage":hit,"counter":0,"suppression":0,"fort_damage":0,"garrison_damage":0}
	result.damage_min=CombatRandom.scaled(base_hit,825);result.damage_max=CombatRandom.scaled(base_hit,1175)
	result.counter_min=0;result.counter_max=0;result.fort_damage_min=0;result.fort_damage_max=0
	if is_fort:
		result.fort_damage = mini(hit, city.fort_hp)
		result.garrison_damage = rational_round([[result.fort_damage,1],[content.rules.combat.garrison_collateral_permille,1000]])
		result.damage = result.garrison_damage
		result.fort_damage_min=mini(city.fort_hp,result.damage_min);result.fort_damage_max=mini(city.fort_hp,result.damage_max)
		result.damage_min=rational_round([[result.fort_damage_min,1],[content.rules.combat.garrison_collateral_permille,1000]])
		result.damage_max=rational_round([[result.fort_damage_max,1],[content.rules.combat.garrison_collateral_permille,1000]])
		if not target.is_empty():
			result.damage=mini(target.hp,result.damage);result.damage_min=mini(target.hp,result.damage_min);result.damage_max=mini(target.hp,result.damage_max)
		return result
	if target.is_empty():
		return result
	result.damage = mini(hit, target.hp)
	result.damage_min=mini(result.damage_min,target.hp);result.damage_max=mini(result.damage_max,target.hp)
	var suppression = int(content.definition("units", attacker.def_id).suppression)
	suppression += EffectRules.technology(state, attacker.owner_id, "suppression_flat", attacker, content)
	suppression += EffectRules.general_bonus(state, attacker, "suppression_flat", content)
	if not skill_id.is_empty():
		for effect in content.definition("skills", skill_id).extra_effects:
			if effect.effect == "suppression_flat":
				suppression += int(effect.value)
	result.suppression = mini(100-target.suppression, suppression)
	var after = target.duplicate(true)
	after.hp -= result.damage
	after.suppression = mini(100, after.suppression + result.suppression)
	if can_counter(state, after, attacker, content):
		result.counter = mini(attacker.hp, CombatRandom.scaled(damage(state, after, attacker, content, true),counter_modifier))
	var healthiest=target.duplicate(true);healthiest.hp-=result.damage_min;healthiest.suppression=after.suppression
	if can_counter(state,healthiest,attacker,content):result.counter_max=mini(attacker.hp,CombatRandom.scaled(damage(state,healthiest,attacker,content,true),1175))
	var weakest=target.duplicate(true);weakest.hp-=result.damage_max;weakest.suppression=after.suppression
	if can_counter(state,weakest,attacker,content):result.counter_min=mini(attacker.hp,CombatRandom.scaled(damage(state,weakest,attacker,content,true),825))
	return result

static func resolve(state: Dictionary, attacker: Dictionary, target: Dictionary, content: ContentRegistry, events: Array, city: Dictionary = {}, skill_id: String = "") -> void:
	var target_position=target.position if not target.is_empty() else city.position
	var target_id=target.get("id",city.get("id"))
	var modifier=CombatRandom.roll(state,attacker,target_id,target_position,events,false,str(city.id) if not city.is_empty() and city.fort_hp>0 else "")
	var result = preview(state, attacker, target, content, city, skill_id,modifier)
	attacker.ammo -= 1
	attacker.attack_ready = false
	attacker.attacked_this_phase = true
	attacker.ap_left = 0
	for i in range(state.statuses.size()-1,-1,-1):
		if state.statuses[i].target_id == attacker.id and state.statuses[i].def_id == "entrenched":
			state.statuses.remove_at(i)
	if result.fort_damage > 0:
		city.fort_hp -= result.fort_damage
		if city.fort_hp==0:city.fort_breached_by=attacker.owner_id
		if MovementRules.domain_of(attacker,content)!="land":city.naval_supported_by=attacker.owner_id;city.naval_supported_round=state.round
		events.append({"type":"FortDamaged","city_id":city.id,"attacker_id":attacker.id,"position":city.position.duplicate(),"from":attacker.position.duplicate(),"amount":result.fort_damage})
	if not target.is_empty():
		target.hp -= result.damage
		target.suppression = mini(100, target.suppression + result.suppression)
		var target_city=StateAccess.at(state,"cities",HexGrid.coordinate(target.position))
		if not target_city.is_empty() and target.suppression>=60:target_city.suppressed_by=attacker.owner_id;target_city.suppressed_round=state.round
		if not target_city.is_empty() and result.damage>0 and MovementRules.domain_of(attacker,content)!="land":target_city.naval_supported_by=attacker.owner_id;target_city.naval_supported_round=state.round
		events.append({"type":"DamageApplied","unit_id":target.id,"attacker_id":attacker.id,"position":target.position.duplicate(),"from":attacker.position.duplicate(),"amount":result.damage,"suppression":result.suppression,"counter":false})
		if result.counter > 0:
			var counter_modifier=CombatRandom.roll(state,target,attacker.id,attacker.position,events,true)
			result.counter=mini(attacker.hp,CombatRandom.scaled(damage(state,target,attacker,content,true),counter_modifier))
			target.ammo -= 1
			target.counter_left -= 1
			attacker.hp -= result.counter
			events.append({"type":"DamageApplied","unit_id":attacker.id,"attacker_id":target.id,"position":attacker.position.duplicate(),"from":target.position.duplicate(),"amount":result.counter,"counter":true})
	if result.damage > 0 or result.fort_damage > 0:
		VeterancyRules.credit(attacker,2,events)
		add_general_xp(state, attacker, 2, content)
	if not target.is_empty() and result.counter>0:VeterancyRules.credit(target,1,events)
	if not target.is_empty() and target.hp <= 0:
		if attacker.owner_id==state.player_faction_id and attacker.def_id=="cavalry" and content.definition("units",target.def_id).family=="artillery":state.metrics.cavalry_destroyed_artillery=int(state.metrics.get("cavalry_destroyed_artillery",0))+1
		attacker.morale = mini(100, attacker.morale+8)
		VeterancyRules.credit(attacker,4,events)
		add_general_xp(state, attacker, 4, content)
		defeat(state, target, events, content,attacker.owner_id)
	if attacker.hp <= 0:
		defeat(state, attacker, events, content,target.owner_id)

static func add_general_xp(state: Dictionary, unit: Dictionary, amount: int, content: ContentRegistry) -> void:
	if unit.get("general_id") == null:
		return
	var g = StateAccess.find(state,"generals",unit.general_id)
	if g.is_empty():
		return
	var bonus = EffectRules.technology(state, unit.owner_id, "general_xp_bonus", unit, content)
	g.earned_xp = mini(80, int(g.get("earned_xp",0)) + int(amount*(1000+bonus)/1000))

static func defeat(state: Dictionary, unit: Dictionary, events: Array, content: ContentRegistry, defeated_by: String = "") -> void:
	if unit.get("general_id") != null:
		var general = StateAccess.find(state, "generals", unit.general_id)
		if not general.is_empty():
			general.injured_this_match = true
			general.assigned_unit_id = null
		for friendly in state.units:
			if friendly.owner_id == unit.owner_id and friendly.position != null and unit.position != null and HexGrid.distance(HexGrid.coordinate(friendly.position),HexGrid.coordinate(unit.position)) <= 2:
				friendly.morale = maxi(0, friendly.morale-10)
	if unit.def_id == "transport_ship" and unit.position != null:
		var cargo: Array = []
		for passenger in state.units:
			if passenger.cargo_parent_id == unit.id:
				cargo.append(passenger)
		cargo.sort_custom(func(a,b):return str(a.id)<str(b.id))
		for passenger in cargo:
			var candidates: Array = []
			for cell in state.map.cells:
				var hex = HexGrid.coordinate(cell.position)
				var land = not content.definition("terrains",cell.terrain_id).water
				if land and cell.region_id!="restricted" and VisibilityRules.hex_visible(state,unit.owner_id,hex) and HexGrid.distance(hex,HexGrid.coordinate(unit.position)) <= 2 and StateAccess.at(state,"units",hex).is_empty():
					candidates.append(cell)
			candidates.sort_custom(func(a,b):
				var da=HexGrid.distance(HexGrid.coordinate(a.position),HexGrid.coordinate(unit.position))
				var db=HexGrid.distance(HexGrid.coordinate(b.position),HexGrid.coordinate(unit.position))
				return da < db if da != db else (a.position.q < b.position.q if a.position.q != b.position.q else a.position.r < b.position.r))
			if candidates.is_empty():
				defeat(state,passenger,events,content,defeated_by)
			else:
				passenger.position = candidates[0].position.duplicate()
				StateAccess.invalidate_occupancy()
				passenger.cargo_parent_id = null
				var rate=mini(700,500+EffectRules.technology(state,passenger.owner_id,"cargo_survival_bonus",passenger,content))
				passenger.hp=maxi(1,rational_round([[passenger.hp,1],[rate,1000]]))
				passenger.suppression=100
				passenger.ap_left=0
				passenger.attack_ready=false
				events.append({"type":"EmergencyDisembark","unit_id":passenger.id,"position":passenger.position})
	events.append({"type":"UnitDefeated","unit_id":unit.id,"owner_id":unit.owner_id,"general_id":unit.general_id,"position":unit.position,"defeated_by":defeated_by})
	StateAccess.remove_by_id(state,"units",unit.id)
