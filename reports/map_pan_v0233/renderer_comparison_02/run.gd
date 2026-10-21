extends SceneTree
var app
func _init() -> void:execute.call_deferred()
func settle(frames: int) -> void:
	for i in frames:await process_frame
func execute() -> void:
	var source=load("res://reports/map_pan_v0233/renderer_comparison_02/profiled_map_view.gd")
	if source==null or not source.can_instantiate():quit(1);return
	source.legacy=true
	app=load("res://app/main.tscn").instantiate();root.add_child(app);await settle(20)
	app.settings.tutorial=false
	var facts: Array=[]
	for entry in [{"name":"mountains","scenario":"campaign_1924_03","camera":Vector2(16848,7000),"zoom":1.05},{"name":"wuhan","scenario":"legion_07","camera":Vector2(1800,1500),"zoom":1.05},{"name":"beijing","scenario":"campaign_1924_01","camera":Vector2(14950,7300),"zoom":.62}]:
		source.legacy=true
		app.start_game(entry.scenario,app.content.scenarios[entry.scenario].player_default);app.close_overlay();await settle(20)
		var view=app.map_view;view.camera=entry.camera;view.zoom=entry.zoom
		if entry.name=="wuhan":view.focus_world(HexGrid.to_world(HexGrid.coordinate(StateAccess.find(app.match_controller.state,"cities","hankou").position)))
		await settle(30);view.set_process(false)
		var fingerprint=ContentRegistry.fingerprint(app.match_controller.state)
		for legacy in [true,false]:
			source.legacy=legacy;view.backdrop_signature="";view.sync_backdrop();view.queue_redraw();await settle(4)
			await RenderingServer.frame_post_draw
			var path="res://reports/map_pan_v0233/renderer_comparison_02/"+entry.name+("_baseline" if legacy else "_optimized")+".png"
			root.get_texture().get_image().save_png(path)
			facts.append({"name":entry.name,"baseline":legacy,"image":path,"camera":view.camera,"zoom":view.zoom,"state_unchanged":fingerprint==ContentRegistry.fingerprint(app.match_controller.state),"raw_native_viewport":true})
		print("PIXEL_PAIR_CAPTURED ",entry.name)
		view.set_process(true)
	var output=FileAccess.open("res://reports/map_pan_v0233/renderer_comparison_02/captures.json",FileAccess.WRITE);output.store_string(JSON.stringify(facts,"\t"));output.close()
	print("PIXEL_COMPARISON_CAPTURE_COMPLETE");quit(0)
