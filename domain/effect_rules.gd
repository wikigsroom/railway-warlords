class_name EffectRules
extends RefCounted

static func scope_matches(scope: String, unit: Dictionary, content: ContentRegistry) -> bool:
	var definition = content.definition("units", unit.def_id)
	var family = definition.get("family", "")
	match scope:
		"all", "eligible_weapon", "faction", "all_assigned_generals":
			return true
		"family_infantry_or_engineer":
			return family == "infantry" or family == "engineer"
		"infantry", "artillery", "cavalry", "naval":
			return family == scope or (scope == "naval" and family in ["river", "water", "coastal"])
		"family_artillery":
			return family == "artillery"
		"family_cavalry":
			return family == "cavalry"
		"family_naval":
			return family in ["river", "water", "coastal"]
		"machine_gun":
			return unit.def_id == "machine_gun"
		"motor_or_rail":
			return definition.movement_profile in ["motor", "rail"]
		"artillery_or_naval":
			return family in ["artillery", "river", "water", "coastal"]
	return scope.begins_with("all_friendly")

static func technology(state: Dictionary, owner: String, effect: String, unit: Dictionary, content: ContentRegistry) -> int:
	var f = StateAccess.faction(state, owner)
	var amount: int = 0
	for id in f.profile_snapshot.tech_ranks:
		var definition = content.definition("technologies", id)
		var rank = int(f.profile_snapshot.tech_ranks[id])
		if definition.is_empty() or rank <= 0 or definition.effect != effect:
			continue
		var scope = definition.effect_scope
		if scope == "friendly_whitelisted_airfield" or scope == "faction" or scope.begins_with("all_friendly") or (not unit.is_empty() and scope_matches(scope, unit, content)):
			amount += int(definition.effect_by_rank[rank-1])
	return amount

static func general_bonus(state: Dictionary, unit: Dictionary, effect: String, content: ContentRegistry) -> int:
	if unit.get("general_id") == null:
		return 0
	var general = StateAccess.find(state, "generals", unit.general_id)
	var definition = content.definition("generals", unit.general_id)
	if general.is_empty() or definition.is_empty():
		return 0
	var result: int = 0
	var passive = content.definition("skills", definition.passive_skill)
	if passive.effect == effect and scope_matches(passive.scope, unit, content):
		var rank = int(general.skill_ranks.get(passive.id, 1))
		result += int(round(float(passive.value) * int(passive.rank_scale_permille[rank-1]) / 1000.0))
	if effect == "attack_bonus":
		var family = content.definition("units", unit.def_id).family
		var specialty = "navy" if family in ["river","water","coastal"] else ("artillery" if family == "rail" else ("infantry" if family == "motor" else family))
		result += int(definition.stars.get(specialty, 0)) * int(content.rules.progression.general_star_attack_permille)
	var f = StateAccess.faction(state, unit.owner_id)
	for medal in f.profile_snapshot.medals:
		if medal.general_id != unit.general_id:
			continue
		var m = content.definition("medals", medal.medal_id)
		if m.effect == effect:
			var values = m.get("values_permille", m.get("values", []))
			result += int(values[int(medal.rank)-1])
	if effect == "defense_flat":
		return mini(result, int(content.rules.progression.general_defense_bonus_cap))
	return result

static func status_bonus(state: Dictionary, unit: Dictionary, effect: String) -> int:
	var result: int = 0
	for status in state.statuses:
		if status.target_id != unit.id:
			continue
		if effect == "defense_flat" and status.def_id in ["entrenched", "fortified_order"]:
			result = maxi(result, int(status.value))
		elif effect == "transport_cost_reduction" and status.def_id == "rail_priority_order":
			result = maxi(result, int(status.value))
	return result

static func reduced_cost(base: Dictionary, reduction: int) -> Dictionary:
	var result: Dictionary = {}
	reduction = clampi(reduction, 0, 300)
	for resource in base:
		var value = int(base[resource])
		result[resource] = maxi(1, int(ceil(float(value) * (1000-reduction)/1000.0))) if value > 0 else 0
	return result

static func scaled_definition(unit: Dictionary, content: ContentRegistry) -> Dictionary:
	var base = content.definition("units", unit.def_id).duplicate(true)
	if unit.get("elite_id") != null:
		var elite = content.definition("elite_variants", unit.elite_id)
		if not elite.is_empty():
			base.hp += int(elite.hp_bonus)
			base.attack += int(elite.attack_bonus)
			base.defense += int(elite.defense_bonus)
			base.max_stack = int(elite.max_stack)
			base.per_faction_cap = int(elite.per_faction_cap)
			for resource in base.cost:
				base.cost[resource] = int(ceil(base.cost[resource] * elite.cost_multiplier_permille / 1000.0))
			for resource in base.upkeep:
				base.upkeep[resource] = int(ceil(base.upkeep[resource] * elite.upkeep_multiplier_permille / 1000.0))
	return base
