extends RefCounted

static func supply_reach(state: Dictionary, owner: String, content: ContentRegistry) -> Dictionary:
	var distance: Dictionary={};var open: Array=[]
	var probe={"owner_id":owner,"def_id":"rifle","elite_id":null}
	for c in state.cities:
		var usable=c.owner_id==owner or (StateAccess.relation(state,owner,c.owner_id).get("supply",false) and StateAccess.allied(state,owner,c.owner_id))
		if usable and not c.blockaded:
			var h=HexGrid.coordinate(c.position);distance[HexGrid.key(h)]=0;open.append({"hex":h,"cost":0})
	while not open.is_empty():
		open.sort_custom(func(a,b):return a.cost<b.cost)
		var now=open.pop_front()
		if now.cost!=distance[HexGrid.key(now.hex)]:continue
		for next in MovementRules.neighbors(state,now.hex):
			var c=StateAccess.cell(state,next)
			if c.is_empty() or c.region_id=="restricted":continue
			var city=StateAccess.at(state,"cities",next)
			if not city.is_empty() and city.owner_id!=owner and not (StateAccess.allied(state,owner,city.owner_id) and StateAccess.relation(state,owner,city.owner_id).get("supply",false)):continue
			var enemy=StateAccess.at(state,"units",next)
			if (not enemy.is_empty() and StateAccess.hostile(state,owner,enemy.owner_id)) or MovementRules.adjacent_hostile(state,probe,next,content,false):continue
			var step=int(content.definition("terrains",c.terrain_id).get("cost_foot",0))
			var crossing=MovementRules.crossing_cost(state,now.hex,next)
			if crossing>0:step=crossing
			if step<=0:continue
			# Intact controlled track extends distribution, while off-track reach remains six cost.
			if MovementRules.rail_neighbor(state,now.hex,next):step=0
			var total=int(now.cost)+step;var key=HexGrid.key(next)
			if total<=6 and total<int(distance.get(key,100000)):
				distance[key]=total;open.append({"hex":next,"cost":total})
	return distance

static func naval_supply_reach(state: Dictionary, owner: String, content: ContentRegistry) -> Dictionary:
	var ports=state.cities.filter(func(c):return c.port and not c.blockaded and EconomyRules.building_level(c,"port")>0 and (c.owner_id==owner or (StateAccess.allied(state,owner,c.owner_id) and StateAccess.relation(state,owner,c.owner_id).get("supply",false))))
	var seeds={};var coverage={}
	for city in ports:
		for dir in HexGrid.DIRECTIONS:
			var h=HexGrid.coordinate(city.get("harbor_position",city.position))+dir;var cell=StateAccess.cell(state,h)
			if not cell.is_empty() and (content.definition("terrains",cell.terrain_id).water or cell.get("water_under_bridge",false)):
				var key=HexGrid.key(h);seeds[key]=city.id;coverage[key]=true
	var visited={};var probe={"owner_id":owner,"def_id":"river_gunboat"}
	for seed in seeds:
		if visited.has(seed):continue
		var component=[];var connected_ports={};var open: Array=[HexGrid.from_key(seed)];visited[seed]=true
		while not open.is_empty():
			var current=open.pop_front();var key=HexGrid.key(current);component.append(key)
			if seeds.has(key):connected_ports[seeds[key]]=true
			for dir in HexGrid.DIRECTIONS:
				var next=current+dir;var nk=HexGrid.key(next);var cell=StateAccess.cell(state,next)
				if visited.has(nk) or cell.is_empty() or cell.region_id=="restricted":continue
				if not (content.definition("terrains",cell.terrain_id).water or cell.get("water_under_bridge",false)):continue
				var enemy=StateAccess.at(state,"units",next)
				if not enemy.is_empty() and not StateAccess.allied(state,owner,enemy.owner_id):continue
				if MovementRules.adjacent_hostile(state,probe,next,content,false):continue
				visited[nk]=true;open.append(next)
		if connected_ports.size()>=2:
			for key in component:coverage[key]=true
	return coverage

static func distribute(state: Dictionary, owner: String, content: ContentRegistry, events: Array) -> void:
	var coverage=supply_reach(state,owner,content)
	var naval_coverage=naval_supply_reach(state,owner,content)
	var troops=state.units.filter(func(u):return u.owner_id==owner)
	troops.sort_custom(func(a,b):
		if a.supply_priority!=b.supply_priority:return a.supply_priority>b.supply_priority
		var da=int(coverage.get(HexGrid.key(HexGrid.coordinate(a.position)),100000)) if a.position!=null else 100000
		var db=int(coverage.get(HexGrid.key(HexGrid.coordinate(b.position)),100000)) if b.position!=null else 100000
		return da<db if da!=db else str(a.id)<str(b.id))
	for u in troops:
		var prior_supply=u.supply_state
		var pos=u.position
		if u.cargo_parent_id!=null:
			var ship=StateAccess.find(state,"units",u.cargo_parent_id);pos=ship.get("position")
		var connected=pos!=null and coverage.has(HexGrid.key(HexGrid.coordinate(pos)))
		if pos!=null and (MovementRules.domain_of(u,content)!="land" or u.cargo_parent_id!=null):
			connected=naval_coverage.has(HexGrid.key(HexGrid.coordinate(pos)))
			for city in state.cities:
				if city.owner_id==owner and city.port and not city.blockaded and EconomyRules.building_level(city,"port")>0 and HexGrid.distance(HexGrid.coordinate(city.get("harbor_position",city.position)),HexGrid.coordinate(pos))<=2:connected=true
		var d=EffectRules.scaled_definition(u,content)
		var reduction=EffectRules.technology(state,owner,"food_upkeep_reduction",u,content)+EffectRules.general_bonus(state,u,"food_upkeep_reduction",content)
		var food=int(EffectRules.reduced_cost({"food":int(d.upkeep.food)*u.stack},reduction).food)
		if state.weather.current=="snow":food+=u.stack
		var fed=connected and StateAccess.pay(state,owner,{"food":food},events,"粮食补给")
		if fed:
			u.supply_state="FULL";u.food_reserve=3+EffectRules.technology(state,owner,"reserve_cap_flat",u,content);u.unsupplied_own_phases=0
			if prior_supply=="NONE" and owner==state.player_faction_id:state.metrics.formations_restored_from_none=int(state.metrics.get("formations_restored_from_none",0))+1
		else:
			u.supply_state="FULL" if u.food_reserve>=2 else ("LOW" if u.food_reserve==1 else "NONE")
			u.food_reserve=maxi(0,u.food_reserve-1)
			u.unsupplied_own_phases=u.unsupplied_own_phases+1 if u.supply_state=="NONE" else 0
			if u.supply_state=="NONE":u.morale=maxi(0,u.morale-8)
		var cut=u.get("rail_supply_cut",{})
		if not cut.is_empty():
			if connected or not StateAccess.hostile(state,cut.cut_by,owner):u.erase("rail_supply_cut")
			elif ["NONE","LOW","FULL"].find(u.supply_state)<["NONE","LOW","FULL"].find(cut.prior_supply):
				if cut.cut_by==state.player_faction_id:state.metrics.rail_cut_changed_enemy_supply=int(state.metrics.get("rail_cut_changed_enemy_supply",0))+1
				events.append({"type":"EnemySupplyCut","owner_id":cut.cut_by,"unit_id":u.id,"prior_supply":cut.prior_supply,"supply_state":u.supply_state});u.erase("rail_supply_cut")
		if connected:
			var price=EffectRules.reduced_cost({"arms":int(d.ammo_refill_arms)},EffectRules.technology(state,owner,"ammo_refill_reduction",u,content)).arms
			price*=u.stack
			while u.ammo<int(d.ammo_capacity) and price>0 and StateAccess.pay(state,owner,{"arms":price},events,"弹药补充"):u.ammo+=1
		if u.unsupplied_own_phases>=2:
			var loss=maxi(1,int(u.max_hp*80/1000));u.hp-=loss
			events.append({"type":"Attrition","unit_id":u.id,"amount":loss})
			if u.hp<=0:CombatRules.defeat(state,u,events,content);continue
		if fed and u.position!=null:
			var healing=0
			for c in state.cities:
				if c.owner_id==owner and HexGrid.distance(HexGrid.coordinate(c.position),HexGrid.coordinate(u.position))<=1:healing=maxi(healing,5*EconomyRules.building_level(c,"hospital"))
			healing=mini(healing,int(u.max_hp*.1));u.hp=mini(u.max_hp,u.hp+healing)
			u.morale=mini(50,u.morale+5+EffectRules.general_bonus(state,u,"morale_recovery_flat",content)) if u.morale<50 and not MovementRules.adjacent_hostile(state,u,HexGrid.coordinate(u.position),content,false) else u.morale
		u.supply_connected=connected
		if u.position!=null:
			var nearest=StateAccess.nearest_city(state,HexGrid.coordinate(u.position),owner)
			u.supply_city_id=nearest.get("id",null) if connected else null
		else:u.supply_city_id=null

