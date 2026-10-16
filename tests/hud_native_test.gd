extends SceneTree

var app: Control
var failures: Array=[]
var checks: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)
func rect_data(rect: Rect2) -> Array:return [rect.position.x,rect.position.y,rect.size.x,rect.size.y]
func contained(outer: Rect2, inner: Rect2) -> bool:return outer.grow(1.1).encloses(inner)
func labels(node: Node) -> Array:
	var result: Array=[]
	if node is Label:result.append(node)
	for child in node.get_children():result.append_array(labels(child))
	return result

func settle() -> void:
	for i in range(8):await process_frame
	app.layout_battle_hud()
	for i in range(4):await process_frame

func run() -> void:
	root.content_scale_size=Vector2i.ZERO
	app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/hud_%d"%Time.get_ticks_usec();root.add_child(app)
	await process_frame
	app.settings.tutorial=false;app.settings.music=false;app.settings.sound=false;app.apply_audio_settings()
	app.start_game("campaign_1924_03","zhili");app.close_overlay();await settle()
	var viewport=app.get_viewport_rect();var header=app.header_shell.get_global_rect();var footer=app.footer_shell.get_global_rect()
	verify(contained(viewport,header) and contained(viewport,footer),"top_and_bottom_rails_inside_viewport")
	verify(not header.intersects(footer),"header_and_orders_do_not_intersect")
	var overflowing=[]
	for line in labels(app.header):
		if not contained(header,line.get_global_rect()):overflowing.append(line.text)
	verify(overflowing.is_empty(),"all_header_labels_fit_actual_panel")
	verify(labels(app.header).all(func(line):return line.autowrap_mode==TextServer.AUTOWRAP_OFF),"header_phase_and_resource_labels_stay_single_line")
	var terrain=app.map_view.terrain_legend_rect();var control=app.map_view.control_legend_rect(app.map_view.control_legend_ids())
	for item in [["terrain",terrain],["control",control]]:
		verify(contained(viewport,item[1]),item[0]+"_legend_inside_viewport")
		for plate in [app.header_shell,app.footer_shell,app.mission_shell,app.inspector_shell,app.layer_shell]:verify(not item[1].intersects(plate.get_global_rect()),item[0]+"_legend_clear_of_"+str(plate.get_instance_id()))
	verify(not terrain.intersects(control),"terrain_and_control_legends_do_not_overlap")
	var original=app.map_view.show_terrain;app.map_view.show_terrain=false;app.map_view.queue_redraw();await settle()
	verify(not app.map_view.foreground_view.show_terrain and not app.map_view.foreground_view.terrain_legend_rect().has_area(),"terrain_toggle_hides_foreground_legend")
	app.map_view.show_terrain=original;app.map_view.queue_redraw();await settle()
	var terrain_cases=[]
	var committed=ContentRegistry.fingerprint(app.match_controller.state)
	for kind in ["plain","hill","mountain","river","sea"]:
		var cells=app.match_controller.state.map.cells.filter(func(cell):return cell.terrain_id==kind and cell.get("region_id","")=="theater" and StateAccess.at(app.match_controller.state,"units",HexGrid.coordinate(cell.position)).is_empty() and StateAccess.at(app.match_controller.state,"cities",HexGrid.coordinate(cell.position)).is_empty())
		if cells.is_empty():continue
		app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode=""
		app.on_hex_selected(HexGrid.coordinate(cells[0].position));await settle()
		var copy=" / ".join(labels(app.inspector).map(func(line):return line.text))
		var definition=app.content.definition("terrains",kind)
		verify(copy.contains(definition.name) and copy.contains("地形掩护") and app.map_view.selected_terrain_hex==HexGrid.coordinate(cells[0].position),"selected_"+kind+"_shows_actual_terrain_and_rules")
		terrain_cases.append(kind)
	verify(ContentRegistry.fingerprint(app.match_controller.state)==committed,"inspecting_terrain_keeps_rules_state_and_random_stream")
	var tag="%dx%d_%03d%s"%[int(viewport.size.x),int(viewport.size.y),roundi(app.settings.ui_scale*100),"_mobile" if app.mobile_layout() else ""]
	var directory="res://reports/screenshots/hud_native";DirAccess.make_dir_recursive_absolute(directory)
	await VisualPlaytest.capture(app,directory+"/"+tag+"_map.png")
	# Real published legal commands establish contact before exercising cinema.
	var attacked=false;var command_count=0
	for step in range(24):
		var state=app.match_controller.state;var c=VisualPlaytest.find_attack(state,app.content,app.match_controller.kernel)
		if c.is_empty():c=VisualPlaytest.advance_to_contact(state,app.content,app.match_controller.kernel)
		if c.is_empty():break
		app.selected_unit_id=c.unit_id;app.selected_city_id="";app.pending={};app.refresh_battle()
		if not app.match_controller.dispatch(c):break
		command_count+=1
		if c.type=="Attack":
			attacked=true;var playback=app.map_view.playback;playback.elapsed=playback.current.duration*.74;playback.speed=0
			await settle();break
		app.map_view.playback.skip()
		while app.match_controller.presentation_busy:await process_frame
	verify(attacked,"published_legal_attack_reaches_cinema")
	var cinema=app.map_view.cinema;var cinema_rect=cinema.get_global_rect()
	verify(cinema.visible and contained(viewport,cinema_rect),"entire_cinema_visible_inside_viewport")
	verify(not cinema_rect.intersects(app.footer_shell.get_global_rect()) and not cinema_rect.intersects(app.header_shell.get_global_rect()),"cinema_results_and_dice_clear_of_both_rails")
	verify(cinema.get_parent()==app.screen and cinema.z_index>app.footer_shell.z_index,"cinema_has_visible_hud_canvas_order")
	await VisualPlaytest.capture(app,directory+"/"+tag+"_impact.png")
	var report={"passed":failures.is_empty(),"failures":failures,"checks":checks,"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"viewport":[viewport.size.x,viewport.size.y],"ui_scale":app.settings.ui_scale,"mobile_layout_test":app.mobile_layout(),"physical_android_device_tested":false,"header":rect_data(app.header_shell.get_global_rect()),"footer":rect_data(app.footer_shell.get_global_rect()),"terrain_legend":rect_data(terrain),"control_legend":rect_data(control),"cinema":rect_data(cinema_rect),"header_overflowing_labels":overflowing,"legal_published_commands":command_count,"terrain_inspected":terrain_cases,"raw_godot_capture":true,"manual_compositing":false}
	var file=FileAccess.open("res://reports/hud_native_"+tag+".json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("HUD_NATIVE_TEST ",tag," ",checks.size()," checks / ",failures.size()," failures")
	app.map_view.playback.skip();app.audio.stop_all();await create_timer(.1).timeout;quit(0 if failures.is_empty() else 1)
