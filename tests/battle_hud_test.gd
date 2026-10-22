extends SceneTree

# Uses viewport input dispatch through the real Godot GUI. No pressed signal
# is emitted by the test and no rule map, unit position or random state is set.
var app
var checks: Array=[]
var failures: Array=[]
var captures: Array=[]
var input_events=0
var touch=false
var directory=""

func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)
func array_rect(rect: Rect2) -> Array:return [rect.position.x,rect.position.y,rect.size.x,rect.size.y]
func contained(rect: Rect2) -> bool:return app.get_viewport_rect().grow(.5).encloses(rect)
func settle(count: int=8) -> void:
	for i in range(count):await process_frame
	app.layout_battle_hud()
	for i in range(3):await process_frame
func click_at(at: Vector2) -> void:
	if touch:
		for down in [true,false]:
			var event=InputEventScreenTouch.new();event.index=0;event.position=at;event.pressed=down
			root.push_input(event,true);input_events+=1;await process_frame
	else:
		var motion=InputEventMouseMotion.new();motion.position=at;motion.global_position=at;root.push_input(motion,true)
		for down in [true,false]:
			var event=InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT;event.position=at;event.global_position=at;event.pressed=down
			root.push_input(event,true);input_events+=1;await process_frame
	await settle()
func click(control: Control) -> void:
	var parent=control.get_parent()
	while parent!=null:
		if parent is ScrollContainer:parent.ensure_control_visible(control);await settle()
		parent=parent.get_parent()
	await click_at(control.get_global_rect().get_center())
func find_button(node: Node, caption: String) -> Button:
	if node is Button and (node.text==caption or node.get_meta("hud_caption","")==caption):return node
	for child in node.get_children():
		var found=find_button(child,caption)
		if found!=null:return found
	return null
func capture(name: String) -> void:
	var path=directory+"/"+name+".png";await VisualPlaytest.capture(app,path)
	captures.append({"name":name,"path":path,"sha256":FileAccess.get_sha256(path),"raw_native_viewport":true})
func verify_controls(node: Node, context: String) -> void:
	if node is Button and node.is_visible_in_tree():
		var clipped=node.get_global_rect();var parent=node.get_parent()
		while parent!=null:
			if parent is Control and parent.clip_contents:clipped=clipped.intersection(parent.get_global_rect())
			parent=parent.get_parent()
		if not clipped.has_area():return
		verify(contained(clipped),context+":visible_button_in_view:"+node.text)
		verify(node.size.x>=44 and node.size.y>=44,context+":minimum_44px_target:"+node.text)
	for child in node.get_children():verify_controls(child,context)

func scroll_details() -> void:
	var scroll=app.inspector.get_parent();var start=scroll.get_global_rect().get_center()
	if touch:
		for swipe in range(4):
			var press=InputEventScreenTouch.new();press.index=0;press.position=start+Vector2(0,90);press.pressed=true;root.push_input(press,true);input_events+=1
			for step in range(1,7):
				var drag=InputEventScreenDrag.new();drag.index=0;drag.position=press.position+Vector2(0,-step*30);drag.relative=Vector2(0,-30);root.push_input(drag,true);input_events+=1;await process_frame
			var release=InputEventScreenTouch.new();release.index=0;release.position=press.position+Vector2(0,-180);release.pressed=false;root.push_input(release,true);input_events+=1
			await settle()
	else:
		for step in range(30):
			for down in [true,false]:
				var wheel=InputEventMouseButton.new();wheel.button_index=MOUSE_BUTTON_WHEEL_DOWN;wheel.position=start;wheel.global_position=start;wheel.pressed=down;root.push_input(wheel,true);input_events+=1
			await process_frame
	await settle()
	var last=find_button(app.inspector,"更多部队命令")
	verify(scroll.get_global_rect().grow(1).encloses(last.get_global_rect()),"actual_scroll_gesture_reaches_last_unit_order")
	verify(not is_instance_valid(app.overlay) and app.order_mode.is_empty(),"scroll_gesture_does_not_activate_an_underlying_order")
	await capture("details_scrolled")

func run() -> void:
	root.content_scale_size=Vector2i.ZERO
	app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/battle_hud_%d"%Time.get_ticks_usec();root.add_child(app)
	await process_frame
	app.settings.tutorial=false;app.settings.music=false;app.settings.sound=false;app.apply_audio_settings()
	touch=app.mobile_layout();var viewport=app.get_viewport_rect();var tag="%dx%d_%03d%s"%[int(viewport.size.x),int(viewport.size.y),roundi(app.settings.ui_scale*100),"_touch" if touch else "_mouse"]
	directory="res://reports/screenshots/battle_hud_v0230/"+tag
	var args=OS.get_cmdline_user_args()
	if "--evidence-root" in args:directory=str(args[args.find("--evidence-root")+1])+"/"+tag
	app.start_game("legion_07","zhili");app.close_overlay();await settle(16)
	var hud=app.battle_hud;var initial=ContentRegistry.fingerprint(app.match_controller.state)
	var mission_text=""
	for child in app.mission_card.get_children():
		if child is Label:mission_text+=child.text
	verify(mission_text.contains("汉阳江岸") and mission_text.contains("一格内"),"escort_objective_names_actual_bank_destination_and_rule_radius")
	verify(not app.inspector_shell.visible and not app.mission_shell.visible and not app.layer_shell.visible,"default_drawers_are_collapsed")
	verify(not app.map_view.minimap.visible and not app.map_view.show_legends,"no_permanent_minimap_or_legend_plates")
	var map_fraction=app.map_view.map_hud_area().get_area()/viewport.get_area()
	var minimum=.60 if app.settings.ui_scale>1.25 else .70
	verify(map_fraction>=minimum,"camera_and_label_area_meets_viewport_and_text_size_target")
	verify_controls(app.screen,"default")
	await capture("battlefield")
	await click(hud.selection);verify(hud.details_open and app.inspector_shell.visible,"selection_pointer_opens_real_inspector")
	verify_controls(app.screen,"details")
	await capture("details")
	await scroll_details()
	await click(find_button(app.inspector_shell,"关闭"));verify(not hud.details_open,"close_pointer_dismisses_inspector")
	await click(hud.objective_button);verify(hud.objectives_open and app.mission_shell.visible,"objective_pointer_opens_live_objectives")
	verify_controls(app.screen,"objectives");await capture("objectives")
	await click(find_button(hud.rail,"图层"));verify(hud.layers_open and not hud.objectives_open,"layers_pointer_switches_exclusive_drawer")
	for item in [["势力覆盖","show_control"],["自然地形","show_terrain"],["地方地名","show_places"],["铁路线","show_rail"],["补给线","show_supply"],["操作蜂窝","show_grid"]]:
		var before=app.map_view.get(item[1]);var button=find_button(app.layer_shell,item[0])
		await click(button);verify(app.map_view.get(item[1])!=before,"layer_pointer_changes:"+item[1])
		await click(button);verify(app.map_view.get(item[1])==before,"layer_pointer_restores:"+item[1])
	verify_controls(app.screen,"layers");await capture("layers")
	await click(find_button(hud.rail,"军令"));verify(hud.extras_open and not hud.layers_open,"additional_orders_pointer_opens_menu")
	verify(find_button(hud.extras,"自动作战")!=null and find_button(hud.extras,"撤销移动")!=null,"automatic_and_undo_commands_remain_available")
	verify_controls(app.screen,"additional_orders");await capture("additional_orders")
	await click(find_button(hud.rail,"军令"))
	var own_city=StateAccess.find(app.match_controller.state,"cities","hankou")
	app.selected_unit_id="";app.selected_city_id=own_city.id;app.refresh_battle();await settle()
	verify(find_button(app.orders,"征募部队")!=null and find_button(app.orders,"城市建设")!=null,"owned_city_exposes_contextual_recruitment_and_construction")
	await click(find_button(app.orders,"征募部队"));verify(is_instance_valid(app.overlay),"city_recruitment_pointer_opens_actual_dialog")
	app.close_overlay();await settle()
	verify(ContentRegistry.fingerprint(app.match_controller.state)==initial,"all_drawers_and_layers_preserve_state_and_random_stream")
	# The independently reviewed 250 m Wuhan board has 8,007 safe fine-material
	# anchors. Keep the whole-footprint land restriction after the refinement.
	var outside=[]
	for key in app.map_view.map_details.surfaces:
		if app.map_view.map_details.surface_families.get(key,"")=="sea_water":continue
		if not app.map_view.relief.dry_point(HexGrid.to_world(HexGrid.from_key(key))):outside.append(key)
	verify(outside.is_empty(),"no_land_material_assigned_outside_source_land")
	verify(app.map_view.map_details.surfaces.size()==8007,"refined_wuhan_8007_safe_material_assignments_retained")
	# Exercise a legal movement by selecting the unit/target on the actual map,
	# then clicking the native confirmation control. State is independently replayed.
	var state=app.match_controller.state;var original=state.duplicate(true)
	var move=VisualPlaytest.advance_to_contact(state,app.content,app.match_controller.kernel)
	verify(not move.is_empty(),"published_wuhan_deployment_has_legal_move")
	var committed: Array=[]
	app.match_controller.command_committed.connect(func(command):committed.append(command.duplicate(true)))
	if not move.is_empty():
		var unit=StateAccess.find(state,"units",move.unit_id)
		app.selected_unit_id="";app.selected_city_id="";app.pending={};app.refresh_battle();await settle()
		app.map_view.zoom=1.1;app.map_view.focus_world(HexGrid.to_world(HexGrid.coordinate(unit.position)));await settle()
		await click_at(app.map_view.world_to_screen(HexGrid.to_world(HexGrid.coordinate(unit.position))))
		verify(app.selected_unit_id==unit.id,"map_pointer_selects_unit")
		await click(find_button(app.orders,"移动"));verify(app.order_mode=="move","move_pointer_sets_order_mode")
		app.map_view.focus_world(HexGrid.to_world(HexGrid.coordinate(move.target_hex)));await settle()
		await click_at(app.map_view.world_to_screen(HexGrid.to_world(HexGrid.coordinate(move.target_hex))))
		await settle(20)
		verify(app.pending.get("type","")=="Move","map_pointer_creates_movement_preview")
		var confirm=find_button(app.orders,"确认移动")
		verify(confirm!=null and not confirm.disabled,"legal_move_confirmation_enabled")
		if confirm!=null and not confirm.disabled:
			await capture("move_confirmation");await click(confirm)
			for i in range(180):
				if not committed.is_empty() and not app.match_controller.command_busy:break
				await process_frame
			verify(committed.size()==1,"confirmation_pointer_commits_exactly_one_command")
			if not committed.is_empty():
				var replay=app.match_controller.kernel.resolve(original,committed[0])
				verify(replay.get("valid",false) and ContentRegistry.fingerprint(replay.state)==ContentRegistry.fingerprint(app.match_controller.state),"pointer_command_replays_to_identical_state_and_rng")
			app.map_view.playback.skip();await settle(12)
			verify_controls(app.screen,"after_move");await capture("after_move")
	# A separate dock must select its owning inland city through real pointer
	# dispatch, while naming the bank correctly in the actual mission drawer.
	app.start_game("legion_08","zhili");app.close_overlay();await settle(16)
	var ningpu_hud=app.battle_hud;var ningpu_initial=ContentRegistry.fingerprint(app.match_controller.state)
	var landing_text=""
	for child in app.mission_card.get_children():
		if child is Label:landing_text+=child.text
	verify(landing_text.contains("南京江岸") and not landing_text.contains("目标格"),"landing_objective_uses_source_city_bank_name")
	await click(ningpu_hud.objective_button);verify_controls(app.screen,"landing_objective")
	await capture("ningpu_objective");await click(ningpu_hud.objective_button)
	var nanjing=StateAccess.find(app.match_controller.state,"cities","nanjing")
	app.selected_unit_id="";app.selected_city_id="";app.order_mode="";app.pending={};app.refresh_battle();await settle()
	app.map_view.zoom=1.05;app.map_view.focus_world(HexGrid.to_world(HarborRules.land_hex(nanjing)));await settle(16)
	await click_at(app.map_view.world_to_screen(HexGrid.to_world(HarborRules.land_hex(nanjing))))
	verify(app.selected_city_id=="nanjing","bank_marker_pointer_selects_its_inland_city")
	var recruit=find_button(app.orders,"征募部队")
	verify(recruit!=null,"selected_bank_exposes_owning_city_orders")
	await capture("ningpu_bank_selection")
	if recruit!=null:
		await click(recruit);verify(is_instance_valid(app.overlay),"bank_city_recruitment_pointer_opens_actual_dialog")
		app.close_overlay();await settle()
	verify(ContentRegistry.fingerprint(app.match_controller.state)==ningpu_initial,"bank_selection_and_dialog_preserve_state_and_random_stream")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"tag":tag,"viewport":[viewport.size.x,viewport.size.y],"ui_scale":app.settings.ui_scale,"input_kind":"viewport_screen_touch" if touch else "viewport_mouse_button","input_events":input_events,"command_signal_emission_used":false,"camera_label_area_fraction":map_fraction,"area_is_not_visible_map_pixel_measurement":true,"header":array_rect(app.header_shell.get_global_rect()),"footer":array_rect(app.footer_shell.get_global_rect()),"captures":captures,"committed_commands":committed,"outside_source_land_materials":outside,"development_engine":true,"physical_android_device_tested":false,"formal_art_approval":false,"ew6_parity_claimed":false,"source_pngs_modified":false}
	var file=FileAccess.open(directory+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("BATTLE_HUD_NATIVE ",tag," ",checks.size()," checks / ",failures.size()," failures")
	app.audio.stop_all();quit(0 if failures.is_empty() else 1)
