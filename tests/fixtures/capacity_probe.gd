extends RefCounted
const Movement=preload("res://tests/fixtures/capacity_probe_movement.gd")
static var times={}
static var counts={}

static func add(name: String, start: int) -> void:
	times[name]=int(times.get(name,0))+Time.get_ticks_usec()-start
	counts[name]=int(counts.get(name,0))+1

static func reachable(s: Dictionary, u: Dictionary, c: ContentRegistry, budget: int=-1) -> Dictionary:
	var start=Time.get_ticks_usec();var graph=Movement.reachable(s,u,c,budget)
	add("reachable",start);return graph

static func clone_transaction(s: Dictionary) -> Dictionary:
	var start=Time.get_ticks_usec();var result=StateAccess.clone_transaction(s)
	add("snapshot",start);return result

static func resolve_move(s: Dictionary, u: Dictionary, path: Array, c: ContentRegistry, events: Array) -> void:
	var start=Time.get_ticks_usec();MovementRules.resolve_move(s,u,path,c,events);add("resolve_move",start)

static func refresh(s: Dictionary, c: ContentRegistry) -> void:
	var start=Time.get_ticks_usec();VisibilityRules.refresh(s,c);add("visibility",start)

static func victory_check(s: Dictionary, c: ContentRegistry, events: Array) -> void:
	var start=Time.get_ticks_usec();VictoryRules.check(s,c,events);add("victory",start)

static func end_phase(s: Dictionary, c: ContentRegistry, events: Array) -> void:
	var start=Time.get_ticks_usec();TurnRules.end_phase(s,c,events);add("end_phase",start)
