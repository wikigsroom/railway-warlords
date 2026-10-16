class_name FacingMemory
extends RefCounted

# Presentation-only state, serialized beside the rules payload. The integer
# screen-space vectors keep checksums stable across JSON float conversion.
# This ledger is bounded by living formations, independently of battle-log age.
var match_id=""
var headings: Dictionary={}
var undo: Dictionary={}

func reset(state: Dictionary, saved: Dictionary = {}) -> void:
	match_id=str(state.get("match_id",state.get("scenario_id","")));headings={};undo={}
	if saved.get("format",0)==1 and saved.get("match_id","")==match_id:
		for id in saved.get("headings",{}):
			var vector=saved.headings[id]
			if vector is Array and vector.size()==2 and vector[0] is int and vector[1] is int and absi(vector[0])<=1000 and absi(vector[1])<=1000 and absi(vector[0])+absi(vector[1])>0:headings[id]=vector.duplicate()
		undo=saved.get("undo",{}).duplicate(true)
		commit(state,[]);return
	commit(state,state.get("event_log",[]))

func remember(id: String, from: Variant, to: Variant) -> void:
	if id.is_empty() or not from is Dictionary or not to is Dictionary:return
	var direction=HexGrid.to_world(HexGrid.coordinate(to))-HexGrid.to_world(HexGrid.coordinate(from))
	if direction.length_squared()<.01:return
	direction=direction.normalized();headings[id]=[roundi(direction.x*1000),roundi(direction.y*1000)]

func commit(state: Dictionary, events: Array, before: Dictionary = {}) -> void:
	var previous=headings.duplicate(true)
	var undone=events.any(func(event):return event.get("type")=="MoveUndone")
	var moved=events.filter(func(event):return event.get("type")=="UnitMoved")
	if not events.is_empty() and not undone:
		undo={}
		if moved.size()==1:
			var id=str(moved[0].unit_id)
			undo={"unit_id":id,"heading":previous.get(id)}
	for event in events:
		var type=str(event.get("type",""))
		if type in ["UnitMoved","RailTransported","Disembarked","EmergencyDisembark"]:
			var path: Array=event.get("path",[])
			var from=event.get("from")
			if from==null and not before.is_empty():
				var old=StateAccess.find(before,"units",str(event.get("unit_id","")))
				from=old.get("position")
				if from==null and old.get("cargo_parent_id")!=null:from=StateAccess.find(before,"units",str(old.cargo_parent_id)).get("position")
			remember(str(event.get("unit_id","")),path[-2] if path.size()>=2 else from,path[-1] if path.size()>=2 else event.get("position"))
		elif type in ["CombatDiceRolled","DamageApplied"]:
			var target_id=str(event.get("target_id",event.get("unit_id","")))
			remember(str(event.get("attacker_id","")),event.get("from"),event.get("position"))
			remember(target_id,event.get("position"),event.get("from"))
		elif type=="MoveUndone" and undo.get("unit_id")==str(event.get("unit_id","")):
			if undo.get("heading") is Array:headings[undo.unit_id]=undo.heading.duplicate()
			else:headings.erase(undo.unit_id)
			undo={}
	var living={}
	for unit in state.get("units",[]):living[str(unit.id)]=true
	for id in headings.keys():
		if not living.has(id):headings.erase(id)

func snapshot() -> Dictionary:
	return {"format":1,"match_id":match_id,"headings":headings.duplicate(true),"undo":undo.duplicate(true)}

func vectors() -> Dictionary:
	var result={}
	for id in headings:result[id]=Vector2(headings[id][0],headings[id][1]).normalized()
	return result
