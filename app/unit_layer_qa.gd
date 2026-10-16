class_name UnitLayerQA
extends RefCounted

static func original_order(source: Array) -> Array:
	var ordered=source.duplicate()
	ordered.sort_custom(func(a,b):return (HexGrid.to_world(HexGrid.coordinate(a.position)).y if a.position!=null else -9999)<(HexGrid.to_world(HexGrid.coordinate(b.position)).y if b.position!=null else -9999))
	return ordered.map(func(u):return u.id)

static func capture_pair(app: Control, name: String, rows: Array) -> void:
	var view:MapView=app.map_view;app.get_tree().paused=true
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	view.unit_cache_enabled=true;view.unit_signature="";view.queue_redraw()
	for i in range(3):await RenderingServer.frame_post_draw
	var source=view.playback.units if view.playback.active else view.state.units
	var order=[];var path="cached_segments" if view.uses_unit_cache() else "direct_atlas_or_many_actors"
	if view.uses_unit_cache():
		for i in range(view.unit_segments.size()):
			order.append_array(view.unit_segments[i].map(func(u):return u.id))
			if i<view.unit_actors.size():order.append(view.unit_actors[i].id)
	else:order=view.ordered_units(source).map(func(u):return u.id)
	var directory="res://reports/screenshots/unit_layers/";DirAccess.make_dir_recursive_absolute(directory)
	var cached=directory+name+"_cached.png";var direct=directory+name+"_direct.png"
	app.get_viewport().get_texture().get_image().save_png(cached)
	view.unit_cache_enabled=false;view.queue_redraw()
	for i in range(3):await RenderingServer.frame_post_draw
	app.get_viewport().get_texture().get_image().save_png(direct)
	rows.append({"name":name,"cached":cached,"direct":direct,
		"runtime_render_path":path,"drawable_units":view.unit_layer_draw_count(),
		"unit_order_preserved":order==original_order(source),
		"unit_count":source.size(),"animated_units":view.playback.animated_unit_ids.keys() if view.playback.active else [],
		"state_and_rng_unchanged":before==ContentRegistry.fingerprint(app.match_controller.state),
		"map_screen_rect":[view.global_position.x,view.global_position.y,view.size.x,view.size.y],
		"raw_native_viewport":true,"manual_compositing":false})
	view.unit_cache_enabled=true;view.unit_signature="";app.get_tree().paused=false

static func run(app: Control) -> void:
	if app.qa_save_path.is_empty():push_error("Native layer comparisons require --qa-session");app.get_tree().quit(1);return
	var rows=[]
	app.start_game("campaign_1924_03","zhili");app.close_overlay()
	for i in range(5):await app.get_tree().process_frame
	await capture_pair(app,"campaign_static",rows)
	var map=ContentRegistry.integerize(app.content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	var initial=CapacityFixture.create(app.content,map)
	app.start_game("qa_capacity",initial.player_faction_id);app.close_overlay();app.match_controller.load_state(initial)
	for i in range(5):await app.get_tree().process_frame
	var view:MapView=app.map_view
	view.fit_map()
	await capture_pair(app,"capacity_static",rows)
	var command=AIPlanner.new(app.content,app.match_controller.kernel).choose(app.match_controller.state)
	if command.type!="Attack" or not app.match_controller.dispatch(command,true):push_error("Native comparison requires a legal attack");app.get_tree().quit(1);return
	view.playback_paused=true
	await capture_pair(app,"capacity_attack_start",rows)
	view.playback_paused=false
	while view.playback.active and not view.playback.cue_flags.has("hit"):await app.get_tree().process_frame
	view.playback_paused=true
	await capture_pair(app,"capacity_attack_hit",rows)
	var report={"passed":rows.all(func(row):return row.unit_order_preserved and row.state_and_rng_unchanged),
		"version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"qa_save_isolated":true,
		"physical_android_device_tested":false,"cases":rows,"native_command":command,
		"scope":"Raw whole-viewport captures of identical paused native scenes; cached and direct rendering; same unit order, state and RNG."}
	var file=FileAccess.open("res://reports/unit_layer_native.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("UNIT_LAYER_NATIVE ",report.passed," ",rows.size()," pairs");app.get_tree().quit(0 if report.passed else 1)
