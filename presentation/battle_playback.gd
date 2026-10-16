class_name BattlePlayback
extends RefCounted

signal cue(sound_id: String)
var active=false
var steps: Array=[]
var index=0
var elapsed=0.0
var units: Array=[]
var cities: Array=[]
var after_units: Array=[]
var current: Dictionary={}
var speed=1.0
var cinematics=true
var reduced_motion=false
var skipped=false
var cue_flags: Dictionary={}
var completed_actions=0
var animated_unit_ids: Dictionary={}

func begin(before: Dictionary, after: Dictionary, events: Array, content: ContentRegistry) -> void:
	prepare(before,after,events,content);activate_prepared()

# Pure event-to-presentation data preparation. A worker can build it without
# accessing scenes or emitting audio cues; activation happens on the main thread.
func prepare(before: Dictionary, after: Dictionary, events: Array, content: ContentRegistry) -> void:
	steps.clear();index=0;elapsed=0;current={};cue_flags.clear();skipped=false
	units=before.get("units",[]).duplicate(true);cities=before.get("cities",[]).duplicate(true);after_units=after.units
	animated_unit_ids.clear();var known_units={}
	for unit in units+after_units:known_units[unit.id]=true
	for event in events:
		for key in ["unit_id","attacker_id","target_id","ship_id"]:
			var id=event.get(key)
			if id!=null and known_units.has(str(id)):animated_unit_ids[str(id)]=true
	for event in events:
		var kind=event.type
		if kind in ["UnitMoved","RailTransported","MoveUndone","Disembarked","EmergencyDisembark"]:
			var unit=StateAccess.find(before,"units",str(event.unit_id))
			if unit.is_empty():unit=StateAccess.find(after,"units",str(event.unit_id))
			if unit.is_empty() or not observable(before,after,event):continue
			var path: Array=event.get("path",[]).duplicate()
			if kind=="RailTransported":path=rail_path(before,event)
			if path.size()<2:
				var origin=event.get("from",unit.position)
				var end=event.get("position",StateAccess.find(after,"units",unit.id).get("position",unit.position))
				if origin!=null and end!=null:path=[origin,end]
			if path.size()<2:continue
			steps.append({"kind":"rail" if kind=="RailTransported" else "move","unit_id":unit.id,"path":path,"duration":clampf(.22+path.size()*.065,.28,.64),"event":event})
		elif kind=="CombatDiceRolled":
			if not observable(before,after,event):continue
			var attacker=StateAccess.find(before,"units",str(event.attacker_id));var target=StateAccess.find(before,"units",str(event.target_id));var city=StateAccess.find(before,"cities",str(event.get("city_id",event.target_id)))
			if attacker.is_empty():continue
			var impacts=events.filter(func(e):return e.type in ["DamageApplied","FortDamaged"] and e.get("attacker_id")==event.attacker_id and e.get("counter",false)==event.counter)
			var title="反击" if event.counter else ("炮击" if content.definition("units",attacker.def_id).family=="artillery" else "交战")
			steps.append({"kind":"attack","attacker":attacker.duplicate(true),"target":target.duplicate(true),"city":city.duplicate(true),"from":event.from,"position":event.position,"roll":event,"impacts":impacts,"duration":1.55 if cinematics and not event.counter else .78,"cinematic":cinematics and not event.counter,"title":title,"family":content.definition("units",attacker.def_id).family,"counter":event.counter})
		elif kind in ["DamageApplied","FortDamaged"] and not event.has("source_city_id") and not events.any(func(e):return e.type=="CombatDiceRolled" and e.attacker_id==event.get("attacker_id")):
			if observable(before,after,event):steps.append({"kind":"impact","position":event.get("position",unit_position(before,str(event.get("unit_id","")))),"impacts":[event],"duration":.42})
		elif kind in ["AirBombed","AirRecon"]:
			if not observable(before,after,event) and event.owner_id!=after.player_faction_id:continue
			var impacts=events.filter(func(e):return e.type in ["DamageApplied","FortDamaged"] and e.get("source_city_id")==event.city_id)
			steps.append({"kind":"air","position":event.position,"from":event.from,"impacts":impacts,"bomb":kind=="AirBombed","duration":1.1})
		elif kind=="CityCaptured":
			var city=StateAccess.find(after,"cities",str(event.city_id))
			if not city.is_empty() and (city.owner_id==after.player_faction_id or VisibilityRules.hex_visible(after,after.player_faction_id,HexGrid.coordinate(city.position))):steps.append({"kind":"capture","position":city.position,"name":city.name,"duration":.45,"event":event})
		elif kind in ["UnitDeployed","UnitReinforced","RailRepaired","FortRepaired","BuildingCompleted","SkillActivated","UnitPromoted"]:
			var object=StateAccess.find(after,"units",str(event.get("target_id",event.get("unit_id",""))))
			if object.is_empty():object=StateAccess.find(after,"cities",str(event.get("city_id","")))
			var position=event.get("position",object.get("position"))
			if position==null or not VisibilityRules.hex_visible(after,after.player_faction_id,HexGrid.coordinate(position)):continue
			var effect="fx_supply_crate" if kind=="UnitReinforced" else ("fx_rail_repair" if kind in ["RailRepaired","BuildingCompleted","FortRepaired"] else ("fx_spark" if kind=="UnitPromoted" else "fx_capture"))
			steps.append({"kind":"support","position":position,"unit_id":object.get("id",""),"effect":effect,"event":event,"duration":.45})

func adopt(prepared: BattlePlayback) -> void:
	steps=prepared.steps;units=prepared.units;cities=prepared.cities;after_units=prepared.after_units;animated_unit_ids=prepared.animated_unit_ids
	index=0;elapsed=0;current={};cue_flags.clear();skipped=false
	activate_prepared()

func activate_prepared() -> void:
	active=not steps.is_empty()
	if active:start_step()
	else:units=after_units

static func unit_position(state: Dictionary, id: String) -> Variant:
	return StateAccess.find(state,"units",id).get("position")

static func observable(before: Dictionary, after: Dictionary, event: Dictionary) -> bool:
	var id=str(event.get("unit_id",event.get("attacker_id","")))
	var u=StateAccess.find(before,"units",id)
	if u.is_empty():u=StateAccess.find(after,"units",id)
	if u.get("owner_id")==after.player_faction_id:return true
	for position in [event.get("position"),event.get("from"),u.get("position")]:
		if position!=null and (VisibilityRules.hex_visible(before,after.player_faction_id,HexGrid.coordinate(position)) or VisibilityRules.hex_visible(after,after.player_faction_id,HexGrid.coordinate(position))):return true
	return false

static func rail_path(state: Dictionary, event: Dictionary) -> Array:
	var path: Array=[];var cursor=HexGrid.coordinate(event.from)
	for id in event.route:
		var edges=state.map.rail_edges.filter(func(e):return e.id==id)
		if edges.is_empty():continue
		var points=edges[0].path_hexes.duplicate()
		if HexGrid.distance(cursor,HexGrid.coordinate(points[-1]))<HexGrid.distance(cursor,HexGrid.coordinate(points[0])):points.reverse()
		for position in points:
			if path.is_empty() or HexGrid.coordinate(path[-1])!=HexGrid.coordinate(position):path.append(position)
		cursor=HexGrid.coordinate(points[-1])
	return path

func start_step() -> void:
	current=steps[index];elapsed=0;cue_flags.clear()
	if current.kind in ["move","rail"]:cue.emit("rail" if current.kind=="rail" else "order_move")
	elif current.kind=="capture":cue.emit("capture")
	elif current.kind=="attack":
		for group in ["attacker","target"]:
			var staged=StateAccess.find({"units":units},"units",str(current[group].get("id","")))
			if not staged.is_empty():current[group]=staged.duplicate(true)
		cue.emit("dice")
	elif current.kind=="air":cue.emit("air")
	elif current.kind=="support":cue.emit("skill" if current.event.type=="SkillActivated" else "repair")

func tick(delta: float) -> void:
	if not active:return
	elapsed+=delta*speed
	var p=progress()
	if current.kind=="attack":
		if p>=.35 and not cue_flags.has("fire"):
			cue_flags.fire=true;cue.emit("artillery" if current.family=="artillery" else ("machine_gun" if current.attacker.def_id=="machine_gun" else "rifle"))
		if p>=.65 and not cue_flags.has("hit"):
			cue_flags.hit=true;cue.emit("explosion" if current.family in ["artillery","naval"] else "rifle");apply_impacts(current.impacts)
	elif current.kind=="impact" and p>=.35 and not cue_flags.has("hit"):
		cue_flags.hit=true;cue.emit("explosion");apply_impacts(current.impacts)
	elif current.kind=="air" and p>=.65 and not cue_flags.has("hit"):
		cue_flags.hit=true
		if current.bomb:cue.emit("explosion");apply_impacts(current.impacts)
	elif current.kind=="support" and p>=.5 and not cue_flags.has("hit"):
		cue_flags.hit=true
		for u in units:
			if u.id==current.unit_id:
				var final=StateAccess.find({"units":after_units},"units",u.id)
				if not final.is_empty():u.hp=final.hp
		if current.event.type=="UnitDeployed":
			var spawned=StateAccess.find({"units":after_units},"units",current.unit_id)
			if not spawned.is_empty():units.append(spawned.duplicate(true))
	if p>=1:
		if current.kind in ["move","rail"]:
			for u in units:
				if u.id==current.unit_id:u.position=current.path[-1].duplicate()
		elif current.kind=="capture":
			for city in cities:
				if city.id==current.event.city_id:city.owner_id=current.event.owner_id
		completed_actions+=1;index+=1
		if index>=steps.size():active=false;units=after_units;current={}
		else:start_step()

func apply_impacts(events: Array) -> void:
	for event in events:
		if event.type=="FortDamaged":
			for city in cities:
				if city.id==event.city_id:city.fort_hp=maxi(0,city.fort_hp-int(event.amount))
		if event.type!="DamageApplied":continue
		for u in units:
			if u.id==event.unit_id:u.hp=maxi(0,u.hp-int(event.amount));u.suppression=mini(100,u.suppression+int(event.get("suppression",0)))

func progress() -> float:return clampf(elapsed/float(current.get("duration",1.0)),0,1)

func skip() -> void:
	skipped=true;completed_actions+=steps.size()-index;active=false;units=after_units;current={}

func position_of(unit: Dictionary) -> Vector2:
	var position=HexGrid.to_world(HexGrid.coordinate(unit.position))
	if not active:return position
	var p=progress()
	if current.kind in ["move","rail"] and current.unit_id==unit.id:
		# Ease departure and arrival without changing the authored route or AP cost.
		var travel=p if reduced_motion else p*p*(3-2*p)
		var route=current.path;var length=(route.size()-1)*travel;var segment=mini(route.size()-2,int(length));var fraction=length-segment
		position=HexGrid.to_world(HexGrid.coordinate(route[segment])).lerp(HexGrid.to_world(HexGrid.coordinate(route[segment+1])),fraction)
	elif current.kind=="attack" and not reduced_motion:
		var direction=(HexGrid.to_world(HexGrid.coordinate(current.position))-HexGrid.to_world(HexGrid.coordinate(current.from))).normalized()
		if unit.id==current.attacker.id and p>.20 and p<.35:position-=direction*sin((p-.20)/.15*PI)*2
		if unit.id==current.attacker.id and p>.35 and p<.57:position-=direction*sin((p-.35)/.22*PI)*5
		if unit.id==current.target.get("id","") and p>.65 and p<.87:position+=direction*sin((p-.65)/.22*PI)*4
	return position

func pose_of(unit: Dictionary) -> String:
	if not active:return "idle"
	if current.kind in ["move","rail"] and current.unit_id==unit.id:
		return "march_a" if int(progress()*maxi(2,current.path.size()-1)*2)%2==0 else "march_b"
	if current.kind=="attack":
		var p=progress()
		if unit.id==current.attacker.id and p>=.18 and p<.65:return "fire"
		if unit.id==current.target.get("id","") and p>=.65 and p<.90:return "hit"
	return "idle"

func motion_visual(unit: Dictionary, content: ContentRegistry) -> Dictionary:
	# Presentation-only motion profile. The authored path and the legal movement
	# cost remain in the simulation; this gives each period unit family a readable
	# cadence and silhouette while it traverses that path.
	var result={"offset":Vector2.ZERO,"rotation":0.0,"scale":1.0,"profile":"idle","phase":0.0}
	if not active or current.kind not in ["move","rail"] or current.unit_id!=unit.id or reduced_motion:return result
	var definition=content.definition("units",unit.def_id)
	var profile=str(definition.get("movement_profile","foot"));var p=progress();var path=current.path
	var travel=p*p*(3-2*p);var segment=mini(path.size()-2,int((path.size()-1)*travel))
	var from=HexGrid.to_world(HexGrid.coordinate(path[segment]));var to=HexGrid.to_world(HexGrid.coordinate(path[segment+1]));var direction=(to-from).normalized()
	var phase=p*TAU*maxi(1,path.size()-1);var normal=direction.orthogonal()
	result.profile=profile;result.phase=phase
	match profile:
		"cavalry":
			result.offset=normal*sin(phase)*2.6+Vector2(0,-absf(sin(phase))*5.0)
			result.rotation=sin(phase)*.045;result.scale=1.0+sin(phase*2.0)*.035
		"motor":
			result.offset=normal*sin(phase)*1.4+Vector2(0,-absf(sin(phase))*2.0)
			result.rotation=sin(phase)*.018;result.scale=1.0+sin(phase*2.0)*.018
		"rail":
			result.offset=Vector2(0,-absf(sin(phase))*1.2);result.rotation=0.0;result.scale=1.0+sin(phase*2.0)*.012
		"river","water","sea":
			# AssetLibrary now selects a genuine cardinal ship view. Applying the
			# heading again here turned north-facing boats sideways while sailing.
			result.offset=normal*sin(phase)*1.8+Vector2(0,-absf(sin(phase))*1.0);result.rotation=sin(phase)*.012;result.scale=1.0+sin(phase*2.0)*.018
		_:
			result.offset=normal*sin(phase)*1.1+Vector2(0,-absf(sin(phase))*2.8)
			result.rotation=sin(phase)*.028;result.scale=1.0+sin(phase*2.0)*.022
	return result

func opacity_of(unit: Dictionary) -> float:
	if unit.hp>0:return 1.0
	return clampf(1.0-(progress()-.65)/.35,0,1) if active and current.kind in ["attack","impact"] else 0.0
