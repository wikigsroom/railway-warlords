class_name LegionRules
extends RefCounted

# The same draft contract is used by the screen, state builder and tests.
static func entry(content: ContentRegistry, choice_id: String, stack: int = 1) -> Dictionary:
	var elite=content.definition("elite_variants",choice_id)
	var def_id=elite.base_unit if not elite.is_empty() else choice_id
	if content.definition("units",def_id).is_empty():return {}
	return {"def_id":def_id,"elite_id":null if elite.is_empty() else choice_id,"stack":stack}

static func price(content: ContentRegistry, formation: Dictionary) -> int:
	if formation.is_empty():return 0
	return int(EffectRules.scaled_definition(formation,content).cost.cash)*int(formation.stack)

static func choices(content: ContentRegistry, recipe: Dictionary) -> Array:
	var result: Array=[]
	var equipment=["militia","rifle","machine_gun","cavalry","engineer","field_artillery","assault"]
	if recipe.anchor_date>="1922-01-01":equipment.append_array(["heavy_artillery","armored_car","armored_train"])
	if recipe.focus in ["navy","embark"]:equipment.append_array(["river_gunboat","transport_ship","coastal_gunship"])
	for id in equipment:
		if id=="armored_train" and content.maps[recipe.map_id].rail_edges.is_empty():continue
		result.append(id)
	if int(recipe.elite_slots)>0:
		for elite in content.tables.elite_variants:
			if equipment.has(elite.base_unit):result.append(elite.id)
	return result

static func default_army(content: ContentRegistry, recipe: Dictionary) -> Array:
	var candidates=["rifle","machine_gun","field_artillery","engineer","militia"]
	if recipe.focus=="repair_rail":candidates=["engineer","rifle","machine_gun","field_artillery","militia"]
	if recipe.focus in ["navy","embark"]:candidates=["river_gunboat","transport_ship","rifle","river_gunboat"]
	var army: Array=[];var remaining=int(recipe.deployment_cash_budget)
	for id in candidates:
		var formation=entry(content,id);var cost=price(content,formation)
		if cost<=remaining:army.append(formation);remaining-=cost
	return army

static func normalized_snapshot(content: ContentRegistry, recipe: Dictionary) -> Dictionary:
	var snapshot={"tech_ranks":{},"general_ranks":{},"skill_ranks":{},"medals":[],"elite_unlocks":[],"active_skills":{}}
	if int(recipe.elite_slots)>0:
		for elite in content.tables.elite_variants:
			snapshot.elite_unlocks.append(elite.id)
			grant_technology(content,snapshot.tech_ranks,elite.required_tech,int(elite.required_rank))
	return snapshot

static func grant_technology(content: ContentRegistry, ranks: Dictionary, id: String, rank: int) -> void:
	if int(ranks.get(id,0))>=rank:return
	ranks[id]=rank
	for prerequisite in content.definition("technologies",id).prerequisite:
		grant_technology(content,ranks,prerequisite.id,int(prerequisite.rank))

static func validate(content: ContentRegistry, recipe: Dictionary, deployment: Variant, generals: Variant, require_focus: bool = true) -> Dictionary:
	if not deployment is Array or deployment.is_empty():return {"valid":false,"reason":"请至少选择一支部队"}
	if not generals is Array:return {"valid":false,"reason":"将领编组格式无效"}
	if generals.size()>int(recipe.general_slots):return {"valid":false,"reason":"将领数量超过本题名额"}
	var seen_generals={}
	for id in generals:
		if not id is String or content.definition("generals",id).is_empty() or seen_generals.has(id):return {"valid":false,"reason":"将领无效或重复选择"}
		seen_generals[id]=true
	var allowed=choices(content,recipe);var army: Array=[];var spent=0;var elite_count=0;var counts={}
	for raw in deployment:
		var formation=entry(content,raw) if raw is String else (raw.duplicate(true) if raw is Dictionary else {})
		if formation.is_empty() or not formation.get("def_id") is String or not formation.get("stack") is int:return {"valid":false,"reason":"编队格式无效"}
		var d=content.definition("units",formation.def_id);var elite_id=formation.get("elite_id")
		var choice_id=str(elite_id) if elite_id!=null else formation.def_id
		if d.is_empty() or not allowed.has(choice_id):return {"valid":false,"reason":"本题未开放此兵种"}
		var elite=content.definition("elite_variants",choice_id) if elite_id!=null else {}
		if elite_id!=null and (elite.is_empty() or elite.base_unit!=d.id):return {"valid":false,"reason":"精锐必须使用对应基础兵种"}
		var max_stack=int(elite.max_stack) if not elite.is_empty() else int(d.max_stack)
		if formation.stack<1 or formation.stack>max_stack:return {"valid":false,"reason":"编队层数超过兵种上限"}
		counts[choice_id]=int(counts.get(choice_id,0))+1
		var cap=int(elite.per_faction_cap) if not elite.is_empty() else int(d.per_faction_cap)
		if cap>0 and counts[choice_id]>cap:return {"valid":false,"reason":"兵种数量超过上限"}
		if elite_id!=null:elite_count+=1
		if elite_count>int(recipe.elite_slots):return {"valid":false,"reason":"精锐数量超过本题名额"}
		formation={"def_id":d.id,"elite_id":elite_id,"stack":int(formation.stack)}
		spent+=price(content,formation);army.append(formation)
	if spent>int(recipe.deployment_cash_budget):return {"valid":false,"reason":"部署预算不足"}
	if require_focus:
		if recipe.focus=="navy" and not army.any(func(u):return u.def_id=="river_gunboat"):return {"valid":false,"reason":"江防护航需要炮艇"}
		if recipe.focus=="embark" and (not army.any(func(u):return u.def_id=="transport_ship") or not army.any(func(u):return content.definition("units",u.def_id).can_occupy and u.def_id!="armored_train")):return {"valid":false,"reason":"跨江训练需要运输船和可装载部队"}
		if recipe.focus=="repair_rail" and not army.any(func(u):return u.def_id=="engineer"):return {"valid":false,"reason":"修桥训练需要工兵"}
	return {"valid":true,"army":army,"generals":generals.duplicate(),"spent":spent,"elite_count":elite_count}

static func elite_count(state: Dictionary, owner: String) -> int:
	var total=state.units.filter(func(u):return u.owner_id==owner and u.elite_id!=null).size()
	for city in state.cities:
		if city.owner_id==owner:total+=city.recruit_queue.filter(func(q):return q.get("elite_id")!=null).size()
	return total
