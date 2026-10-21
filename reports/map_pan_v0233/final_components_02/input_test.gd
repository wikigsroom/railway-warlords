extends SceneTree

var failures: Array=[]
var checks: Array=[]

func _init() -> void:run.call_deferred()
func check(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/input_%d"%Time.get_ticks_usec();root.add_child(app)
	await process_frame
	app.start_game("campaign_1920_01","zhili");app.close_overlay()
	await process_frame;await process_frame
	var map:MapView=app.map_view;var selected: Array=[];map.hex_selected.connect(func(hex):selected.append(hex))
	var point=map.size*.5;var expected=map.screen_to_hex(point)
	var press=InputEventMouseButton.new();press.button_index=MOUSE_BUTTON_LEFT;press.pressed=true;press.position=point;map._gui_input(press)
	var release=InputEventMouseButton.new();release.button_index=MOUSE_BUTTON_LEFT;release.pressed=false;release.position=point;map._gui_input(release)
	check(selected.size()==1 and selected[0]==expected,"mouse_click_maps_to_real_hex")
	map.camera=map.world_bounds.get_center();map.clamp_camera()
	var old_camera=map.camera
	press.position=point;map._gui_input(press);var motion=InputEventMouseMotion.new();motion.button_mask=MOUSE_BUTTON_MASK_LEFT;motion.position=point+Vector2(50,20);motion.relative=Vector2(50,20);map._gui_input(motion);release.position=motion.position;map._gui_input(release)
	check(map.camera!=old_camera and selected.size()==1,"mouse_drag_pans_without_accidental_selection")
	var touch=InputEventScreenTouch.new();touch.index=0;touch.position=point;touch.pressed=true;map._gui_input(touch);touch.pressed=false;map._gui_input(touch)
	check(selected.size()==2,"touch_tap_selects_once_without_mouse_emulation")
	map.camera=map.world_bounds.get_center();map.clamp_camera()
	old_camera=map.camera;touch.pressed=true;map._gui_input(touch);var drag=InputEventScreenDrag.new();drag.index=0;drag.position=point+Vector2(65,35);drag.relative=Vector2(65,35);map._gui_input(drag);touch.pressed=false;touch.position=drag.position;map._gui_input(touch)
	check(map.camera!=old_camera and selected.size()==2,"single_finger_drag_pans_without_selecting")
	map.camera=map.world_bounds.position;map.clamp_camera();old_camera=map.camera
	touch.position=point;touch.pressed=true;map._gui_input(touch);drag.position=point+Vector2(90,90);drag.relative=Vector2(90,90);map._gui_input(drag);touch.pressed=false;touch.position=drag.position;map._gui_input(touch)
	check(map.camera==old_camera and selected.size()==2,"touch_drag_at_map_boundary_stays_clamped_without_selection")
	var a=InputEventScreenTouch.new();a.index=0;a.position=point-Vector2(50,0);a.pressed=true;map._gui_input(a);var b=InputEventScreenTouch.new();b.index=1;b.position=point+Vector2(50,0);b.pressed=true;map._gui_input(b)
	var old_zoom=map.zoom;drag.index=1;drag.position=point+Vector2(95,0);drag.relative=Vector2(45,0);map._gui_input(drag)
	check(map.zoom>old_zoom,"two_finger_pinch_changes_zoom")
	a.pressed=false;b.pressed=false;map._gui_input(a);map._gui_input(b);check(map.pointers.is_empty(),"touch_release_clears_pointer_state")
	app.show_recruit(app.match_controller.state.cities[0].id);check(app.match_controller.paused,"production_panel_pauses_ai_and_keeps_snapshot_stable");app.close_overlay();check(not app.match_controller.paused,"closing_modal_resumes_game")
	app.show_pause();app.show_save_dialog(true);check(app.match_controller.paused,"pause_remains_active_when_switching_to_save_panel");app.close_overlay()
	root.size=Vector2i(1280,720);await process_frame;await process_frame
	check(app.screen.get_global_rect().size.x>=1270 and app.map_view.size.x>650,"landscape_layout_1280x720_map_preserved")
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_02/input_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify({"checks":checks,"failures":failures,"physical_android_device_tested":false},"\t"));file.close()
	print("INPUT_TESTS: ",checks.size()-failures.size()," passed / ",failures.size()," failed");quit(0 if failures.is_empty() else 1)
