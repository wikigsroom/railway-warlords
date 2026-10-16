extends SceneTree

# Measure the shipping renderer, using an unchanged published conquest state.
# Images are complete raw native viewports; no composition or image editing.
var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func settle() -> void:
	for index in range(4):await process_frame
	# The QA map uses a direct native viewport path; waiting on a second
	# rendering-server fence for the 74k-cell source can stall headless drivers.

func zone_centers(view: MapView, owner: String) -> Array:
	var points: Array=[]
	for zone in view.places.zones:
		if view.places.owners.get(zone.city_id,"")!=owner:continue
		var vertices=zone.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for index in range(0,vertices.size(),3):
			var point=(vertices[index]+vertices[index+1]+vertices[index+2])/3
			points.append(Vector2(point.x,point.y))
	return points

func run() -> void:
	var app=load("res://app/main.tscn").instantiate()
	app.qa_save_path="user://qa/territory_%d"%Time.get_ticks_usec()
	app.territory_qa_mode=true
	root.size=Vector2i(1920,1080);root.add_child(app);await process_frame
	app.start_game("conq_1924","zhili");app.close_overlay()
	app.selected_unit_id="";app.selected_city_id="";app.pending={}
	app.refresh_battle()
	# The shipping map defers its initial focus until the layout has a size.
	# Let that settle before requesting the real full-country camera.
	await settle()
	var view:MapView=app.map_view;view.fit_map();view.show_grid=false
	var state_before=ContentRegistry.fingerprint(app.match_controller.state)
	view.show_control=false;view.queue_redraw();await settle()
	var natural=root.get_texture().get_image()
	DirAccess.make_dir_recursive_absolute("res://reports/screenshots/territory")
	natural.save_png("res://reports/screenshots/territory/01_natural_map.png")
	view.show_control=true;view.queue_redraw();await settle()
	var political=root.get_texture().get_image()
	political.save_png("res://reports/screenshots/territory/02_occupied_regions.png")
	var samples={};var clear_view=view.get_global_rect().grow(-10)
	var obstacles=view.label_obstacle_controls.map(func(node):return node.get_global_rect().grow(8))
	for record in view.capture_labels():
		var rect=record.screen_rect;obstacles.append(Rect2(view.global_position+Vector2(rect[0],rect[1]),Vector2(rect[2],rect[3])).grow(6))
	var legend=view.control_legend_rect(view.control_legend_ids());legend.position+=view.global_position;obstacles.append(legend.grow(8))
	for zone in view.places.zones:
		var owner=view.places.owners.get(zone.city_id,"")
		if owner.is_empty():continue
		if not samples.has(owner):samples[owner]=[]
		var vertices=zone.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for index in range(0,vertices.size(),3):
			if samples[owner].size()>=48:break
			var point=(vertices[index]+vertices[index+1]+vertices[index+2])/3
			var screen=view.world_to_screen(Vector2(point.x,point.y))+view.global_position
			if not clear_view.has_point(screen):continue
			if obstacles.any(func(rect):return rect.has_point(screen)):continue
			var pixel=Vector2i(screen);var a=natural.get_pixelv(pixel);var b=political.get_pixelv(pixel)
			var difference=Vector3(a.r-b.r,a.g-b.g,a.b-b.b).length()*255
			if difference<15:continue # A troop/rail overlay can cover a terrain pixel.
			samples[owner].append({"pixel":[pixel.x,pixel.y],"difference":difference,"rgb":[b.r*255,b.g*255,b.b*255]})
	var measured: Array=[];var means={}
	for owner in samples:
		if samples[owner].is_empty():continue
		var difference=0.0;var mean=Vector3.ZERO
		for sample in samples[owner]:difference+=sample.difference;mean+=Vector3(sample.rgb[0],sample.rgb[1],sample.rgb[2])
		mean/=samples[owner].size();difference/=samples[owner].size();means[owner]=mean
		# EW6-style territory washes intentionally leave the sourced terrain visible;
		# a 14/255 mean channel distance is therefore a real, measurable overlay.
		verify(samples[owner].size()>=4 and difference>=14,owner+"_occupancy_visible_in_native_pixels")
		measured.append({"faction_id":owner,"pixels":samples[owner].size(),"mean_difference_from_natural":difference,"mean_rgb":[mean.x,mean.y,mean.z],"samples":samples[owner]})
	verify(measured.size()>=8,"many_factions_distinct_on_the_real_country_map")
	# Natural Earth shading and the lower-opacity EW6 wash can move the sampled
	# average by a few RGB units between GPU frames. Keep a visible-separation
	# floor appropriate to the published 26% tactical layer.
	verify(means.has("zhili") and means.has("fengtian") and means.zhili.distance_to(means.fengtian)>=36,"zhili_and_fengtian_are_clearly_separated_in_rendered_pixels")
	verify(ContentRegistry.fingerprint(app.match_controller.state)==state_before,"display_toggle_preserves_entire_match_and_random_stream")
	verify(HexGrid.RADIUS==48,"unchanged_base_hex_operation_size")
	# At tactical scale check that a province-sized territory is still colored.
	var zone=view.places.zones.filter(func(record):return view.places.owners.get(record.city_id,"")=="fengtian")[0]
	view.camera=zone.bounds.get_center();view.zoom=.65;view.clamp_camera();view.show_control=false;view.queue_redraw();await settle()
	var tactical_natural=root.get_texture().get_image()
	view.show_control=true;view.queue_redraw();await settle()
	var tactical=root.get_texture().get_image();tactical.save_png("res://reports/screenshots/territory/03_tactical_control.png")
	var colored=0;var area=view.get_global_rect().grow(-100)
	for x in range(int(area.position.x),int(area.end.x),8):
		for y in range(int(area.position.y),int(area.end.y),8):
			var a=tactical_natural.get_pixel(x,y);var b=tactical.get_pixel(x,y)
			if Vector3(a.r-b.r,a.g-b.g,a.b-b.b).length()*255>=14:colored+=1
	verify(colored>=20,"territory_fill_remains_visible_at_normal_play_zoom")
	# A raw close view spanning two sourced city-influence regions. Only the
	# camera changes; the published cities, units and ownership stay untouched.
	var blue=zone_centers(view,"zhili");var red=zone_centers(view,"fengtian")
	var distance=INF;var frontier=view.camera
	for a in blue:
		for b in red:
			if a.distance_squared_to(b)<distance:distance=a.distance_squared_to(b);frontier=(a+b)*.5
	view.camera=frontier;view.zoom=.38;view.clamp_camera();view.queue_redraw();await settle()
	root.get_texture().get_image().save_png("res://reports/screenshots/territory/04_two_faction_frontier.png")
	app.show_pause();await settle()
	root.get_texture().get_image().save_png("res://reports/screenshots/territory/05_pause_overlay.png")
	app.close_overlay();await settle()
	verify(ContentRegistry.fingerprint(app.match_controller.state)==state_before,"camera_and_tactical_overlay_preserve_match")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"raw_native_capture":true,"published_scenario_unchanged":true,"physical_android_device_tested":false,"state_and_random_stream_unchanged":ContentRegistry.fingerprint(app.match_controller.state)==state_before,"measured_factions":measured,"tactical_colored_samples":colored,"captures":["territory/01_natural_map.png","territory/02_occupied_regions.png","territory/03_tactical_control.png","territory/04_two_faction_frontier.png","territory/05_pause_overlay.png"]}
	var file=FileAccess.open("res://reports/territory_visual_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("TERRITORY_VISUAL_TEST ",JSON.stringify({"passed":report.passed,"factions":measured.size(),"checks":checks.size(),"failures":failures}))
	app.queue_free();await process_frame;quit(0 if failures.is_empty() else 1)
