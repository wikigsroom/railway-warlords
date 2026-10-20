class_name StateBuilder
extends RefCounted

static func unit(id: String, def_id: String, owner: String, position: Variant, content: ContentRegistry, stack: int = 1, elite_id: Variant = null) -> Dictionary:
	var u={"id":id,"def_id":def_id,"owner_id":owner,"position":position,"stack":stack,"elite_id":elite_id,"general_id":null,"cargo_parent_id":null,"hp":0,"max_hp":0,"ap_left":0,"attack_ready":true,"skill_ready":true,"work_ready":true,"counter_left":1,"ammo":4,"food_reserve":3,"supply_state":"FULL","suppression":0,"morale":50,"unsupplied_own_phases":0,"moved_this_phase":false,"attacked_this_phase":false,"transported_this_phase":false,"supply_priority":1,"general_assignment_lock":false}
	var d=EffectRules.scaled_definition(u,content)
	u.max_hp=int(d.hp)*stack
	u.experience=0
	u.hp=u.max_hp
	u.ap_left=int(d.ap)
	u.ammo=int(d.ammo_capacity)
	u.counter_left=2 if def_id=="machine_gun" else 1
	return u

static func historical_equipment_for_year(year: int) -> Array:
	# This is the playable period roster, separate from the generic 1920 rules
	# era_min retained by the original campaign.  The names are game classes;
	# each period gate prevents anachronistic recruitment in the seven Asia starts.
	var result=["militia","rifle","cavalry","engineer","field_artillery","coastal_gunship","transport_ship"]
	if year>=1860:result.append("river_gunboat")
	if year>=1890:result.append("machine_gun")
	if year>=1900:result.append_array(["heavy_artillery","armored_train"])
	if year>=1917:result.append_array(["assault","armored_car"])
	return result

static func create(content: ContentRegistry, scenario_id: String, player_id: String, profile: Dictionary, difficulty: String = "normal") -> Dictionary:
	if not content.scenarios.has(scenario_id):return {}
	var recipe=content.scenarios[scenario_id]
	if not recipe.faction_roster.has(player_id) or (recipe.mode=="conquest" and not content.playable_factions(scenario_id).has(player_id)):return {}
	# A defending and an attacking side can share a dated scenario without
	# inheriting each other's objective. Keep the source recipe immutable.
	var side_objective:Dictionary=recipe.get("objective_by_faction",{}).get(player_id,{})
	if not side_objective.is_empty():
		recipe=recipe.duplicate(false)
		recipe.objective_type=side_objective.type
		recipe.objective_count=int(side_objective.get("count",1))
	var legion_selection={}
	if recipe.mode=="legion":
		difficulty="normal"
		legion_selection=LegionRules.validate(content,recipe,profile.get("_legion_deployment",LegionRules.default_army(content,recipe)),profile.get("_legion_generals",["wu_peifu","feng_yuxiang"].slice(0,int(recipe.general_slots))))
		if not legion_selection.valid:return {}
	var map=content.maps[recipe.map_id].duplicate(false)
	map.rail_edges=map.rail_edges.duplicate(true)
	map.dynamic_cell_offsets={}
	map.reference_pois=[]
	var s={"schema_version":2,"ruleset_version":1,"content_hash":content.content_hash,"match_id":scenario_id+"_"+Crypto.new().generate_random_bytes(16).hex_encode(),"scenario_id":scenario_id,"mode":recipe.mode,"play_mode":recipe.get("play_mode","historical_campaign"),"difficulty":difficulty,"player_faction_id":player_id,"date":recipe.anchor_date,"round":1,"phase_index":0,"state_version":0,"status":"playing","winner_id":null,"turn_order":recipe.faction_roster.duplicate(),"map":map,"cities":[],"units":[],"generals":[],"factions":[],"relations":[],"statuses":[],"visibility":[],"engineer_jobs":[],"pending_aid":[],"authored_events":recipe.events.duplicate(true),"weather":{"current":"clear","forecast":[]},"objectives":[],"metrics":{"kills":0,"losses":0,"captures":0,"rail_trips":0,"rail_repairs":0,"air_recon":0,"air_bombs":0,"skills":0,"reinforcements":0,"buildings":0,"diplomacy":0,"war_exhaustion":0,"legitimacy":0,"colonial_influence":0,"rounds":1},"initial_player_count":0,"sequence":1,"last_move_inverse":null,"event_log":[],"reward_claimed":false}
	s.combat_random=CombatRandom.initialize(s.match_id)
	# The selected player always acts first; no hidden AI opening moves.
	s.turn_order.erase(player_id);s.turn_order.push_front(player_id)
	for owner in s.turn_order:
		var normalized=difficulty=="challenge" or recipe.mode=="legion"
		var snapshot={"tech_ranks":{},"general_ranks":{},"skill_ranks":{},"medals":[],"elite_unlocks":[],"active_skills":{}}
		if recipe.mode=="legion":snapshot=LegionRules.normalized_snapshot(content,recipe)
		if owner==player_id and not normalized:
			for key in snapshot:snapshot[key]=profile.get(key,snapshot[key]).duplicate(true) if profile.get(key) is Array or profile.get(key) is Dictionary else snapshot[key]
		var year=int(recipe.anchor_date.substr(0,4))
		var legacy_equipment=["militia","rifle","machine_gun","cavalry","engineer","field_artillery","assault"]
		if year>=1922:legacy_equipment.append_array(["heavy_artillery","armored_car","armored_train"])
		var equipment=recipe.get("equipment_whitelist",legacy_equipment).duplicate()
		if owner in ["zhili","fengtian","jiangsu","guangdong"]:
			for naval in ["river_gunboat","transport_ship","coastal_gunship"]:
				if year>=int(content.definition("units",naval).get("historical_era_min",0)) and not equipment.has(naval):equipment.append(naval)
		var resources=recipe.starting_resources.duplicate()
		if not resources.has("fuel"):resources.fuel=0
		if not resources.has("silver"):resources.silver=0
		var metrics=recipe.get("faction_metrics",{}).get(owner,{})
		s.factions.append({"id":owner,"resources":resources,"war_exhaustion":int(metrics.get("war_exhaustion",0)),"legitimacy":int(metrics.get("legitimacy",50)),"colonial_influence":int(metrics.get("colonial_influence",0)),"own_phase_index":0,"command_points":3,"transport_pool":0,"air_sorties_left":5,"trade_orders_left":2,"diplomacy_orders_left":1,"war_orders_left":1,"aid_orders_left":1,"income_penalty_permille":1000,"eliminated":false,"profile_snapshot":snapshot,"equipment_whitelist":equipment,"airfield_whitelist":[],"general_whitelist":[],"transport_used_phase":false})
	for i in range(s.turn_order.size()):
		for j in range(i+1,s.turn_order.size()):
			var a=s.turn_order[i];var b=s.turn_order[j]
			var war=recipe.mode!="conquest" or (a=="zhili" and b==("anhui" if recipe.anchor_date.begins_with("1920") else "fengtian")) or (b=="zhili" and a==("anhui" if recipe.anchor_date.begins_with("1920") else "fengtian"))
			for pair in recipe.get("initial_wars",[]):
				if pair is Array and pair.size()>=2 and ((pair[0]==a and pair[1]==b) or (pair[0]==b and pair[1]==a)):war=true
			var relation_state="WAR" if war else "NEUTRAL"
			for relation in recipe.get("initial_relations",[]):
				if relation.get("faction_a","")==a and relation.get("faction_b","")==b or relation.get("faction_a","")==b and relation.get("faction_b","")==a:relation_state=str(relation.get("state",relation_state))
			s.relations.append({"id":"rel_%s_%s"%[a,b],"faction_a":a,"faction_b":b,"state":relation_state,"passage":false,"supply":false,"minimum_until_round":0,"break_at_round":0,"last_aid_round":-10,"betrayal_until_round":0})
	var target={}
	var base_city_id=""
	var enemy_base_id=""
	if recipe.mode!="conquest":
		var goal=map.cities.filter(func(c):return c.id==recipe.target_city_id)[0]
		var candidates=map.cities.filter(func(c):return c.id!=goal.id and c.position.q<goal.position.q)
		candidates.sort_custom(func(a,b):return HexGrid.distance(HexGrid.coordinate(a.position),HexGrid.coordinate(goal.position))<HexGrid.distance(HexGrid.coordinate(b.position),HexGrid.coordinate(goal.position)))
		if not candidates.is_empty():base_city_id=candidates[0].id
		else:
			var fallback=map.cities.filter(func(c):return c.id!=goal.id)
			fallback.sort_custom(func(a,b):return HexGrid.distance(HexGrid.coordinate(a.position),HexGrid.coordinate(goal.position))<HexGrid.distance(HexGrid.coordinate(b.position),HexGrid.coordinate(goal.position)))
			if not fallback.is_empty():base_city_id=fallback[0].id
		if recipe.has("base_city_id") and map.cities.any(func(c):return c.id==recipe.base_city_id):base_city_id=recipe.base_city_id
		var others=map.cities.filter(func(c):return c.id!=goal.id and c.id!=base_city_id)
		others.sort_custom(func(a,b):return HexGrid.distance(HexGrid.coordinate(a.position),HexGrid.coordinate(goal.position))<HexGrid.distance(HexGrid.coordinate(b.position),HexGrid.coordinate(goal.position)))
		if not others.is_empty():enemy_base_id=others[0].id
		if recipe.has("enemy_base_city_id") and map.cities.any(func(c):return c.id==recipe.enemy_base_city_id):enemy_base_id=recipe.enemy_base_city_id
	for city in map.cities:
		if recipe.mode=="conquest" and (ContentRegistry.conquest_reference_only(city,recipe.anchor_date) or not s.turn_order.has(ContentRegistry.conquest_owner(city,recipe.anchor_date,scenario_id))):
			var poi=city.duplicate(true);poi.poi_reason="historical_occupation" if city.has("protected_before") else "unpublished_control"
			map.reference_pois.append(poi)
			if poi.poi_reason=="historical_occupation":
					var cell=StateAccess.mutable_cell(s,HexGrid.coordinate(city.position));cell.region_before_protection=cell.region_id;cell.region_id="restricted"
			continue
		if recipe.mode!="conquest":
			var goal=map.cities.filter(func(c):return c.id==recipe.target_city_id)[0]
			if city.id not in [base_city_id,recipe.target_city_id,enemy_base_id]:continue
		var c=city.duplicate(true)
		c.owner_id=c.reference_owner if s.turn_order.has(c.reference_owner) else player_id
		if recipe.mode=="conquest":
			c.owner_id=ContentRegistry.conquest_owner(c,recipe.anchor_date,scenario_id)
		if recipe.mode!="conquest":
			var goal=map.cities.filter(func(c):return c.id==recipe.target_city_id)[0]
			c.owner_id=player_id if c.id==base_city_id else s.turn_order[1]
			var historical_owner=recipe.get("initial_city_owners",{}).get(c.id,"")
			if s.turn_order.has(historical_owner):c.owner_id=historical_owner
		initialize_city(s,c,content)
		if c.id==recipe.target_city_id:target=c
	if recipe.mode=="conquest":
		for city in s.cities:
			var available=recipe.get("equipment_whitelist",content.tables.units.map(func(d):return d.id))
			var defs=["rifle","field_artillery"] if recipe.has("equipment_whitelist") else ["rifle","machine_gun","field_artillery"]
			if city.level<2:defs=["militia"]
			defs=defs.filter(func(def_id):return available.has(def_id))
			if defs.is_empty():defs=[available[0]]
			for i in range(defs.size()):deploy(s,city.position,city.owner_id,defs[i],content,3)
	else:
		var origin=HexGrid.coordinate(target.position)
		var friend_hex=origin+Vector2i(-5,2)
		var enemy_hex=origin+Vector2i(2,-1)
		if recipe.has("friend_start_offset"):friend_hex=origin+HexGrid.coordinate(recipe.friend_start_offset)
		if recipe.has("enemy_start_offset"):enemy_hex=origin+HexGrid.coordinate(recipe.enemy_start_offset)
		if recipe.objective_type=="escort":friend_hex=origin+Vector2i(-8,4);enemy_hex=origin+Vector2i(-3,1)
		var available=recipe.get("equipment_whitelist",historical_equipment_for_year(int(recipe.anchor_date.substr(0,4))))
		var definitions: Array=[]
		for def_id in ["rifle","rifle","machine_gun","field_artillery","engineer","cavalry","rifle","field_artillery","machine_gun","militia","cavalry","rifle","engineer","rifle"]:
			if available.has(def_id):definitions.append(def_id)
		if definitions.is_empty():definitions=[available[0]]
		var player_deployment: Array=[]
		if recipe.mode=="legion":
			player_deployment=legion_selection.army
		else:
			var player_count=int(recipe.get("starting_formations_by_faction",{}).get(player_id,recipe.player_formations))
			for i in range(player_count):player_deployment.append({"def_id":definitions[i%definitions.size()],"stack":1,"elite_id":null})
		for formation in player_deployment:
			var deployed={}
			if content.definition("units",formation.def_id).movement_profile in ["river","water","sea"]:deployed=deploy_water(s,target.position,player_id,formation.def_id,content,10,int(formation.stack),formation.elite_id)
			else:deployed=deploy(s,HexGrid.position(friend_hex),player_id,formation.def_id,content,4,int(formation.stack),formation.elite_id)
			if recipe.mode=="legion" and deployed.is_empty():return {}
		var other_sides:Array=recipe.get("starting_formations_by_faction",{}).keys() if recipe.has("starting_formations_by_faction") else [s.turn_order[1]]
		other_sides.erase(player_id)
		for side_index in range(other_sides.size()):
			var owner=str(other_sides[side_index])
			if not s.turn_order.has(owner):continue
			var count=int(recipe.get("starting_formations_by_faction",{}).get(owner,recipe.enemy_formations))
			var side_hex=enemy_hex+Vector2i(0,side_index*4)
			for i in range(count):
				var enemy_unit=deploy(s,HexGrid.position(side_hex),owner,definitions[i%definitions.size()],content,4)
				# Stack counts are gameplay parameters; a sourced formation ID
				# remains traceable without asserting literal historical strength.
				if not enemy_unit.is_empty() and recipe.has("destroy_formation_id"):
					enemy_unit.historical_formation_id=str(recipe.destroy_formation_id)
		# Keep the objective city as a fortified garrison, rather than an empty flag.
		var occupying=StateAccess.at(s,"units",origin)
		var garrison_type="machine_gun" if available.has("machine_gun") else "rifle" if available.has("rifle") else str(available[0])
		if occupying.is_empty() and recipe.objective_type not in ["escort","survive"]:s.units.append(unit(next_id(s,"u"),garrison_type,target.owner_id,target.position.duplicate(),content))
		StateAccess.invalidate_occupancy()
		if recipe.objective_type in ["escort","survive"]:
			var escort=s.units.filter(func(u):return u.owner_id==player_id)[0]
			s.objectives.append({"id":"escort","type":recipe.objective_type,"target_ids":[escort.id],"destination":target.position.duplicate(),"required":1,"progress":0,"protected":true})
			target.owner_id=player_id;target.fort_hp=int(target.fort_max_hp)
			clear_hostile_garrison(s,target,enemy_hex,content)
		elif recipe.objective_type=="repair":
			var nearest:Dictionary={};var best=100000
			for edge in map.rail_edges:
				var d=HexGrid.distance(origin,HexGrid.coordinate(edge.path_hexes[int(edge.path_hexes.size()/2)]))
				if d<best:best=d;nearest=edge
			if not nearest.is_empty():
				nearest.damage="broken"
				var repair_at=nearest.path_hexes[int(nearest.path_hexes.size()/2)]
				var engineers=s.units.filter(func(v):return v.owner_id==player_id and v.def_id=="engineer")
				if not engineers.is_empty():
					var engineer=engineers[0];StateAccess.remove_by_id(s,"units",engineer.id)
					var replacement=deploy(s,repair_at,player_id,"engineer",content,1,int(engineer.stack))
					if not replacement.is_empty():
						engineer.position=replacement.position.duplicate();s.units.erase(replacement);s.units.append(engineer);StateAccess.invalidate_occupancy()
					elif recipe.mode=="legion":return {}
					else:s.units.append(engineer);StateAccess.invalidate_occupancy()
				s.objectives.append({"id":"primary","type":"repair","target_ids":[nearest.id],"required":1,"progress":0,"protected":false})
		elif recipe.objective_type=="destroy":
			var destroy_owner=str(recipe.get("destroy_target_owner",s.turn_order[1] if s.turn_order.size()>1 else ""))
			var formation_filter=str(recipe.get("destroy_formation_id",""))
			var destroy_ids:Array=[]
			for enemy_unit in s.units:
				if enemy_unit.owner_id!=destroy_owner:continue
				if formation_filter!="" and str(enemy_unit.get("historical_formation_id",""))!=formation_filter:continue
				destroy_ids.append(enemy_unit.id)
			s.objectives.append({"id":"primary","type":"destroy","target_ids":destroy_ids,"required":1,"progress":0,"protected":false,"formation_id":formation_filter})
		elif recipe.objective_type=="capture_commander":
			var commander_id=str(recipe.get("target_commander_id",""))
			s.objectives.append({"id":"primary","type":"capture_commander","target_ids":[commander_id],"required":1,"progress":0,"protected":false,"optional_if_absent":bool(recipe.get("commander_optional_if_absent",false))})
		else:s.objectives.append({"id":"primary","type":recipe.objective_type,"target_ids":[target.id],"required":recipe.objective_count,"progress":0,"protected":false,"accept_allied_control":bool(side_objective.get("accept_allied_control",false))})
		for condition_index in range(recipe.get("secondary_objectives",[]).size()):
			var condition=recipe.secondary_objectives[condition_index]
			var condition_type=str(condition.get("type",""))
			if condition_type=="capture_commander":
				s.objectives.append({"id":"secondary_%02d"%condition_index,"type":"capture_commander","target_ids":[str(condition.get("commander_id",""))],"required":1,"progress":0,"protected":false,"optional_if_absent":bool(condition.get("optional_if_absent",false))})
			elif condition_type in ["capture","hold"]:
				s.objectives.append({"id":"secondary_%02d"%condition_index,"type":condition_type,"target_ids":[str(condition.get("city_id",recipe.target_city_id))],"required":int(condition.get("required",1)),"progress":0,"protected":false})
		if recipe.mode=="legion":
			var focus=recipe.get("focus","")
			var base_city=StateAccess.find(s,"cities",base_city_id)
			if focus=="recon" and not base_city.is_empty():
				base_city.buildings=base_city.buildings.filter(func(b):return b.def_id!="arsenal")
				base_city.buildings.append({"def_id":"airfield","level":1,"damaged":false})
				StateAccess.faction(s,player_id).airfield_whitelist.append(base_city.id)
				s.objectives.append({"id":"recon","type":"metric","metric":"air_recon","target_ids":[],"required":1,"progress":0,"protected":false})
			if focus=="fortification":
				target.owner_id=player_id;target.buildings.append({"def_id":"fortification","level":1,"damaged":false});target.fort_max_hp+=40;target.fort_hp=target.fort_max_hp
				var garrison=StateAccess.at(s,"units",HexGrid.coordinate(target.position))
				if not garrison.is_empty():garrison.owner_id=player_id
				s.objectives=[{"id":"primary","type":"hold","target_ids":[target.id],"required":3,"progress":0,"protected":false}]
			if focus=="rail_transfer":s.objectives.append({"id":"rail","type":"metric","metric":"rail_trips","target_ids":[],"required":1,"progress":0,"protected":false})
			if focus in ["navy","embark"]:
				if not base_city.is_empty():base_city.owner_id=player_id
				target.owner_id=player_id
				clear_hostile_garrison(s,target,enemy_hex,content)
				# River training uses actual navigable water cells and controlled harbors on the two banks.
				for i in range(2):deploy_water(s,target.position,s.turn_order[1],"river_gunboat",content,8)
				if focus=="navy":
					var boats=s.units.filter(func(v):return v.owner_id==player_id and v.def_id=="river_gunboat")
					if not boats.is_empty():
						var boat=boats[0];StateAccess.remove_by_id(s,"units",boat.id)
						var far=s.map.cells.filter(func(c):return c.terrain_id=="river" and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(target.position))>=6 and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(target.position))<=8 and StateAccess.at(s,"units",HexGrid.coordinate(c.position)).is_empty())
						if not far.is_empty():boat.position=far[0].position.duplicate()
						s.units.append(boat);StateAccess.invalidate_occupancy()
						s.objectives=[{"id":"river_escort","type":"escort","target_ids":[boat.id],"destination":target.position.duplicate(),"required":1,"progress":0,"protected":true}]
				else:
					var transports=s.units.filter(func(v):return v.owner_id==player_id and v.def_id=="transport_ship")
					var infantry=s.units.filter(func(v):return v.owner_id==player_id and content.definition("units",v.def_id).can_occupy)
					if not transports.is_empty() and not infantry.is_empty() and not base_city.is_empty():
						var ship=transports[0];var passenger=infantry[0]
						var waters=s.map.cells.filter(func(c):return c.terrain_id=="river" and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(base_city.position))<=5 and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(target.position))>=4 and StateAccess.at(s,"units",HexGrid.coordinate(c.position)).is_empty())
						waters.sort_custom(func(a,b):return HexGrid.distance(HexGrid.coordinate(a.position),HexGrid.coordinate(base_city.position))<HexGrid.distance(HexGrid.coordinate(b.position),HexGrid.coordinate(base_city.position)))
						if not waters.is_empty():ship.position=waters[0].position.duplicate()
						passenger.cargo_parent_id=ship.id;passenger.position=null;passenger.cargo_actions_ready=true
						s.objectives=[{"id":"river_landing","type":"disembark","target_ids":[passenger.id],"destination":target.position.duplicate(),"required":1,"progress":0,"protected":true}]
				StateAccess.invalidate_occupancy()
	var deployment_recipe=content.scenarios.get(str(recipe.get("scenario_reference","conq_1924")),{}) if recipe.mode=="legion" else recipe
	var commander_index=CommanderRoster.deployment_index(content,deployment_recipe) if not deployment_recipe.is_empty() else {}
	for gd in content.tables.generals:
		var deployment: Dictionary=commander_index.get(str(gd.id),{})
		var owner=str(deployment.get("owner_id",""))
		if recipe.mode=="legion":
			if legion_selection.generals.has(gd.id):
				owner=player_id;deployment={"auto_assign":true,"deployment_role":"training","title_at_start":"军团训练配置"}
			else:
				deployment=commander_index.get(str(gd.id),{})
				owner=str(deployment.get("owner_id",""))
				if owner==player_id:continue
		if not s.turn_order.has(owner):continue
		var f=StateAccess.faction(s,owner)
		# Historical battles use their own dated rosters. Only training exercises
		# have an explicit deployment budget; no shared side quota truncates a battle.
		if recipe.mode=="legion" and f.general_whitelist.size()>=recipe.general_slots:continue
		f.general_whitelist.append(gd.id)
		var rank=int(f.profile_snapshot.general_ranks.get(gd.id,0))
		var skill_id=str(f.profile_snapshot.get("active_skills",{}).get(gd.id,gd.active_skill))
		if skill_id!=gd.active_skill and (skill_id!="cavalry_sweep" or gd.stars.cavalry<3):skill_id=gd.active_skill
		var ranks={gd.passive_skill:1,skill_id:1}
		for key in ranks:ranks[key]=int(f.profile_snapshot.skill_ranks.get(gd.id+":"+key,1))
		var g={"id":gd.id,"owner_id":owner,"rank":rank,"skill_ranks":ranks,"cooldowns":{},"assigned_unit_id":null,"injured_this_match":false,"unassign_cooldown":0,"earned_xp":0}
		s.generals.append(g)
		g.active_skill_id=skill_id
		g.deployment_role=str(deployment.get("deployment_role","field_command"))
		g.historical_title=str(deployment.get("title_at_start",""))
		g.historical_formation=str(deployment.get("formation",""))
		g.roster_source_ids=deployment.get("source_ids",[]).duplicate()
		var active=content.definition("skills",skill_id)
		var eligible=s.units.filter(func(u):return u.owner_id==owner and u.general_id==null and u.cargo_parent_id==null and EffectRules.scope_matches(active.caster_scope,u,content)) if deployment.get("auto_assign",true) else []
		eligible.sort_custom(func(a,b):
			var am=EffectRules.scope_matches(active.caster_scope,a,content);var bm=EffectRules.scope_matches(active.caster_scope,b,content)
			return am and not bm if am!=bm else str(a.id)<str(b.id))
		# Surplus commanders stay in the reserve. Do not create fictional formations
		# merely to place every named officer on the map.
		if not eligible.is_empty():
			var u=eligible[0];u.general_id=g.id;g.assigned_unit_id=u.id
			u.max_hp=CombatRules.rational_round([[u.max_hp,1],[1000+30*rank,1000]]);u.hp=u.max_hp
	s.initial_player_count=s.units.filter(func(u):return u.owner_id==player_id).size()
	s.normalized=difficulty=="challenge" or recipe.mode=="legion"
	s.weak_faction=recipe.get("weak_faction_ids",[]).has(player_id)
	if recipe.mode=="legion":
		s.legion_deployment={"formations":legion_selection.army.duplicate(true),"generals":legion_selection.generals.duplicate(),"spent":legion_selection.spent,"budget":recipe.deployment_cash_budget,"elite_slots":recipe.elite_slots}
	s.protected_commander_id=null;s.protected_general_id=null
	if recipe.mode=="campaign":
		for g in s.generals:
			if g.owner_id==player_id and g.assigned_unit_id!=null:s.protected_general_id=g.id;break
	s.round_limit=recipe.round_limit
	s.ruleset_version=ContentRegistry.RUNTIME_RULESET_VERSION
	s.star_rounds_at_most=recipe.get("stars",{}).get("rounds_at_most",int(ceil(recipe.round_limit*.7)))
	s.star_loss_ratio_permille_at_most=recipe.get("stars",{}).get("loss_ratio_permille_at_most",300)
	TurnRules.round_start(s,content,[])
	TurnRules.own_start(s,player_id,content,[])
	VisibilityRules.refresh(s,content)
	StateAccess.freeze_map(s.map)
	return s

static func next_id(state: Dictionary, prefix: String) -> String:
	var id="%s_%05d"%[prefix,state.sequence];state.sequence+=1;return id

static func initialize_city(state: Dictionary, city: Dictionary, content: ContentRegistry) -> void:
	var base=content.tables.city_levels[int(city.level)-1]
	city.fort_hp=base.fort_hp;city.fort_max_hp=base.fort_hp;city.stability=100;city.recruit_reserve=base.recruit_reserve_cap
	city.buildings=[{"def_id":"barracks","level":2 if city.level>=2 else 1,"damaged":false},{"def_id":"arsenal","level":2 if city.level>=2 else 1,"damaged":false}]
	if state.map.rail_nodes.any(func(n):return n.city_id==city.id):city.buildings.append({"def_id":"station","level":2 if city.level>=2 else 1,"damaged":false})
	else:city.buildings.append({"def_id":"workshop","level":1,"damaged":false})
	if city.port:city.buildings.append({"def_id":"port","level":1,"damaged":false})
	city.recruit_queue=[];city.construction_queue=[];city.construction_action_used=false;city.air_sorties_left=2;city.blockaded=false
	state.cities.append(city)
	var faction=StateAccess.faction(state,city.owner_id)
	if city.level>=2 and not faction.is_empty():faction.airfield_whitelist.append(city.id)

static func deploy(state: Dictionary, center: Dictionary, owner: String, def_id: String, content: ContentRegistry, radius: int = 3, stack: int = 1, elite_id: Variant = null) -> Dictionary:
	var origin=HexGrid.coordinate(center)
	var candidates: Array=[]
	var movement=content.definition("units",def_id).movement_profile
	for q in range(origin.x-radius,origin.x+radius+1):
		for r in range(origin.y-radius,origin.y+radius+1):
			var h=Vector2i(q,r);var cell=StateAccess.cell(state,h)
			if cell.is_empty() or cell.region_id=="restricted" or HexGrid.distance(origin,h)>radius:continue
			var city=StateAccess.at(state,"cities",h)
			if not city.is_empty() and city.owner_id!=owner:continue
			var d=content.definition("terrains",cell.terrain_id)
			var can_stand=d.get("cost_"+movement,0)>0
			if movement=="rail":can_stand=state.map.rail_edges.any(func(edge):return edge.damage=="intact" and MovementRules.rail_available(state,edge) and edge.path_hexes.has(HexGrid.position(h)))
			if can_stand and StateAccess.at(state,"units",h).is_empty():candidates.append(h)
	candidates.sort_custom(func(a,b):
		var da=HexGrid.distance(a,origin);var db=HexGrid.distance(b,origin)
		return da<db if da!=db else (a.x<b.x if a.x!=b.x else a.y<b.y))
	if not candidates.is_empty():
		var deployed=unit(next_id(state,"u"),def_id,owner,HexGrid.position(candidates[0]),content,stack,elite_id)
		state.units.append(deployed);StateAccess.invalidate_occupancy();return deployed
	return {}

static func deploy_water(state: Dictionary, center: Dictionary, owner: String, def_id: String, content: ContentRegistry, radius: int = 6, stack: int = 1, elite_id: Variant = null) -> Dictionary:
	var origin=HexGrid.coordinate(center)
	var terrain_ids=["river"] if content.definition("units",def_id).movement_profile=="river" else ["river","sea"]
	var cells=state.map.cells.filter(func(c):return c.terrain_id in terrain_ids and c.region_id!="restricted" and HexGrid.distance(HexGrid.coordinate(c.position),origin)<=radius and StateAccess.at(state,"units",HexGrid.coordinate(c.position)).is_empty())
	cells.sort_custom(func(a,b):return HexGrid.distance(HexGrid.coordinate(a.position),origin)<HexGrid.distance(HexGrid.coordinate(b.position),origin))
	if not cells.is_empty():
		var deployed=unit(next_id(state,"u"),def_id,owner,cells[0].position.duplicate(),content,stack,elite_id)
		state.units.append(deployed);StateAccess.invalidate_occupancy();return deployed
	return {}

static func clear_hostile_garrison(state: Dictionary, city: Dictionary, fallback: Vector2i, content: ContentRegistry) -> void:
	var garrison=StateAccess.at(state,"units",HexGrid.coordinate(city.position))
	if garrison.is_empty() or garrison.owner_id==city.owner_id:return
	StateAccess.remove_by_id(state,"units",garrison.id)
	deploy(state,HexGrid.position(fallback),garrison.owner_id,garrison.def_id,content,4)
