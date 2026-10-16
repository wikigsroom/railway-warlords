class_name RulesJob
extends RefCounted

var kind: String
var base: Dictionary
var arguments: Dictionary
var content: ContentRegistry
var planner: AIPlanner
var presentation_options: Dictionary
var command: Dictionary={}
var result: Dictionary={}
var worker_usec=0
var worker_thread_id=0
var _mutex=Mutex.new()
var _completed=false
var _cancelled=false

func _init(job_kind: String, snapshot: Dictionary, data: Dictionary, registry: ContentRegistry, ai: AIPlanner = null, presentation: Dictionary = {}) -> void:
	kind=job_kind;base=snapshot;arguments=data.duplicate(true);content=registry;planner=ai;presentation_options=presentation.duplicate()

func cancel() -> void:
	_mutex.lock();_cancelled=true;_mutex.unlock()

func is_completed() -> bool:
	_mutex.lock();var ready=_completed;_mutex.unlock();return ready

func execute() -> void:
	_mutex.lock();var cancelled=_cancelled;_mutex.unlock()
	var started=Time.get_ticks_usec();var value: Dictionary={};var issued: Dictionary={}
	if not cancelled:
		var kernel=CommandKernel.new(content)
		match kind:
			"plan":
				issued=planner.choose(base);value=kernel.resolve(base,issued)
			"resolve":
				issued=arguments;value=kernel.resolve(base,issued)
			"preview":value=kernel.preview(base,arguments)
			"selection":value=selection_query(kernel)
			"save":
				var service=SaveService.new(arguments.path,content)
				value={"valid":service.write(arguments.slot,base,content.content_hash,arguments.get("presentation",{})),"reason":service.error}
			"slots":
				var service=SaveService.new(arguments.path,content);value={"valid":true,"slots":service.list_slots()}
			"load":
				var service=SaveService.new(arguments.path,content);var loaded=service.load_slot(arguments.slot,content.content_hash)
				if not loaded.is_empty():VisibilityRules.refresh(loaded,content)
				value={"valid":not loaded.is_empty(),"state":loaded,"presentation":service.last_presentation,"reason":service.error}
		if kind in ["plan","resolve"] and value.get("valid",false):value.presentation=prepare_presentation(value.state,value.events)
	_mutex.lock()
	command=issued;result=value if not _cancelled else {}
	worker_usec=Time.get_ticks_usec()-started;worker_thread_id=OS.get_thread_caller_id();_completed=true
	_mutex.unlock()

func prepare_presentation(after: Dictionary, events: Array) -> Dictionary:
	var staged=BattlePlayback.new();staged.cinematics=presentation_options.get("cinematics",true);staged.reduced_motion=presentation_options.get("reduced_motion",false)
	staged.prepare(base,after,events,content)
	var visible={};var explored={};var known: Array=[]
	var sights=after.visibility.filter(func(sight):return sight.faction_id==after.player_faction_id)
	if sights.size()==1:
		var cache=PreparedSightCache.current()
		var visible_index=cache.build(sights[0].visible_cell_ids,"visible")
		var explored_index=visible_index if is_same(sights[0].visible_cell_ids,sights[0].explored_cell_ids) else cache.build(sights[0].explored_cell_ids,"explored")
		visible=visible_index.ids;explored=explored_index.ids;known=visible_index.known
	else:
		for sight in sights:
			for id in sight.visible_cell_ids:visible[id]=true
			for id in sight.explored_cell_ids:explored[id]=true
		known=visible.keys();visible.make_read_only();explored.make_read_only();known.make_read_only()
	var tracks=[]
	for edge in after.map.rail_edges:tracks.append([edge.id,edge.damage,after.date>=edge.active_from,MovementRules.rail_available(after,edge),edge.path_hexes])
	return {"playback":staged,"visible_ids":visible,"explored_ids":explored,"known":known,"tracks":tracks}

func selection_query(kernel: CommandKernel) -> Dictionary:
	var value={"reachable":{},"attack_targets":{},"preview":{},"reinforce":{},"undo":{}}
	var unit=StateAccess.find(base,"units",arguments.get("unit_id",""))
	var owner=base.turn_order[base.phase_index]
	var prefix={"actor_id":owner,"expected_version":base.state_version}
	if not unit.is_empty() and unit.position!=null and unit.owner_id==base.player_faction_id and owner==base.player_faction_id:
		value.reachable=MovementRules.reachable(base,unit,content).costs
		for target in base.units+base.cities:
			if target.position==null or not StateAccess.hostile(base,unit.owner_id,target.owner_id):continue
			var c=prefix.duplicate();c.type="Attack";c.unit_id=unit.id;c.target_hex=target.position
			if kernel.preview(base,c).valid:value.attack_targets[HexGrid.key(HexGrid.coordinate(target.position))]=true
		var c=prefix.duplicate();c.type="Reinforce";c.unit_id=unit.id
		value.reinforce=kernel.preview(base,c)
	var undo=prefix.duplicate();undo.type="UndoMove";value.undo=kernel.preview(base,undo)
	if not arguments.get("pending",{}).is_empty():value.preview=kernel.preview(base,arguments.pending)
	return value
