extends SceneTree

# Diagnostic ablation of actual native map layers. Only the first capture at
# each camera is the ordinary renderer; all other captures are labelled QA
# alternatives. They are not shipping screenshots or art-acceptance evidence.
var app
var output=""
var captures: Array=[]
var checks: Array=[]
var expected_camera=Vector2.ZERO
var expected_zoom=1.0

func _init() -> void:run.call_deferred()

func settle() -> void:
	app.map_view.backdrop_signature=""
	app.map_view.queue_redraw()
	for index in range(12):await process_frame
	await RenderingServer.frame_post_draw

func capture(name: String, overrides: Array) -> void:
	await settle()
	checks.append({"name":"requested_camera_preserved:"+name,
		"passed":app.map_view.camera.distance_to(expected_camera)<.05 and is_equal_approx(app.map_view.zoom,expected_zoom)})
	var picture=root.get_texture().get_image()
	var path=output.path_join(name+".png")
	if picture.save_png(path)!=OK:push_error("Native layer capture failed");quit(1);return
	captures.append({"file":name+".png","sha256":FileAccess.get_sha256(path),
		"renderer_overrides":overrides,"ordinary_renderer":overrides.is_empty(),
		"raw_godot_capture":true,"camera":[app.map_view.camera.x,app.map_view.camera.y],
		"zoom":app.map_view.zoom,"control_visible":app.map_view.show_control})

func run() -> void:
	var args=OS.get_cmdline_user_args();output=args[args.find("--output")+1]
	app=load("res://app/main.tscn").instantiate()
	app.qa_save_path="user://qa/ground_layers/"+str(Time.get_ticks_usec())
	root.add_child(app)
	app.settings.tutorial=false
	app.start_game("asia_1927",app.content.scenarios.asia_1927.player_default)
	app.close_overlay()
	app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id=""
	app.pending={};app.order_mode="";app.refresh_battle()
	# Drain start_game's deferred focus_player and HUD layout before choosing
	# any diagnosis camera. Its first frame otherwise replaces that camera.
	await settle()
	var view: MapView=app.map_view
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	var surfaces=view.map_details.surfaces
	var buckets=view.terrain_visual_buckets
	for row in [["himalaya",85.5,29.2,.72],["tianjin",117.2,39.1,.66]]:
		view.map_details.surfaces=surfaces;view.terrain_visual_buckets=buckets
		view.map_details.fine_chunk_meshes.clear();view.map_details.fine_chunk_order.clear()
		view.zoom=float(row[3])
		var map: Dictionary=view.state.map
		var x=(float(row[1])-float(map.geographic_bounds[0]))/float(map.longitude_step_deg)*72.0
		var y=(float(map.geographic_bounds[3])-float(row[2]))/float(map.latitude_step_deg)*sqrt(3.0)*48.0
		view.focus_world(Vector2(x,y))
		expected_camera=view.camera;expected_zoom=view.zoom
		view.show_control=true
		await capture(row[0]+"_control",[])
		view.show_control=false
		await capture(row[0]+"_natural",[])
		view.map_details.surfaces={}
		view.map_details.fine_chunk_meshes.clear();view.map_details.fine_chunk_order.clear()
		await capture(row[0]+"_no_cell_details",["fine_surface_assignments_withheld"])
		view.terrain_visual_buckets={}
		await capture(row[0]+"_no_details_or_washes",["fine_surface_assignments_withheld","cell_wash_buckets_withheld"])
	view.map_details.surfaces=surfaces;view.terrain_visual_buckets=buckets
	var unchanged=before==ContentRegistry.fingerprint(app.match_controller.state)
	checks.append({"name":"rules_state_unchanged","passed":unchanged})
	var passed=checks.all(func(row):return row.passed)
	var report={"passed":passed,"checks":checks,"captures":captures,"rules_state_unchanged":unchanged,
		"build_version":ContentRegistry.APP_VERSION,"qa_save_isolated":true,
		"ordinary_renderer_captures":4,"ablation_captures":4,"shipping_exe":false,
		"physical_android_device_tested":false,"formal_art_approval":false}
	var file=FileAccess.open(output.path_join("validation.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_LAYERS_NATIVE ",JSON.stringify({"passed":passed,"captures":captures.size()}))
	quit(0 if passed else 1)
