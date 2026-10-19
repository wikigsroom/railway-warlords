extends SceneTree

class TimedRelief:
	extends AtlasRelief
	var point_calls=0
	var point_usec=0
	func dry_point(point: Vector2) -> bool:
		var before=Time.get_ticks_usec()
		var result=super.dry_point(point)
		point_usec+=Time.get_ticks_usec()-before;point_calls+=1
		return result
	func build(map: Dictionary, shapes: Array, lines: Array, minor: Array=[]) -> void:
		var started=Time.get_ticks_usec();print("COAST_PROFILE_BEGIN relief")
		super.build(map,shapes,lines,minor)
		print("COAST_PROFILE_RELIEF ",JSON.stringify({"ms":(Time.get_ticks_usec()-started)/1000.0,"point_calls":point_calls,"point_ms":point_usec/1000.0,"details":diagnostics}))

class TimedDetails:
	extends MapDetails
	func build(map: Dictionary, cells: Dictionary, relief: AtlasRelief, coast: Array, rivers: Array) -> void:
		var started=Time.get_ticks_usec();print("COAST_PROFILE_BEGIN details")
		super.build(map,cells,relief,coast,rivers)
		print("COAST_PROFILE_DETAILS ",JSON.stringify({"ms":(Time.get_ticks_usec()-started)/1000.0,"details":diagnostics}))

func _init() -> void:run.call_deferred()

func run() -> void:
	var started=Time.get_ticks_usec();var registry=ContentRegistry.new();registry.load_all()
	print("COAST_PROFILE_CONTENT_MS ",(Time.get_ticks_usec()-started)/1000.0)
	started=Time.get_ticks_usec();var state=StateBuilder.create(registry,"conq_1922",registry.scenarios.conq_1922.player_default,{})
	print("COAST_PROFILE_STATE_MS ",(Time.get_ticks_usec()-started)/1000.0)
	var library=AssetLibrary.new();var view=MapView.new();view.relief=TimedRelief.new();view.map_details=TimedDetails.new()
	view.size=Vector2(1200,760);view.setup(registry,library)
	started=Time.get_ticks_usec();view.set_state(state)
	print("COAST_PROFILE_VIEW_MS ",(Time.get_ticks_usec()-started)/1000.0)
	print("COAST_PROFILE_FINAL_RELIEF ",JSON.stringify({"point_calls":view.relief.point_calls,"point_ms":view.relief.point_usec/1000.0}))
	view.free();quit()
