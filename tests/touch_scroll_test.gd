extends SceneTree

# Component input regression for direct touch with mouse emulation disabled.
# No generated screenshot or synthetic scene is used as gameplay evidence.
const TouchScroll=preload("res://presentation/touch_scroll.gd")
var checks: Array=[]
var failures: Array=[]
var activated: Array=[]
var scroll
var rows: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)
func settle() -> void:
	for i in range(5):await process_frame
func touch(point: Vector2, pressed: bool) -> void:
	var event=InputEventScreenTouch.new();event.index=0;event.position=point;event.pressed=pressed
	root.push_input(event,true);await process_frame
func swipe(start: Vector2, distance: float) -> void:
	await touch(start,true)
	for step in range(1,7):
		var drag=InputEventScreenDrag.new();drag.index=0;drag.position=start+Vector2(0,-distance*step/6.0);drag.relative=Vector2(0,-distance/6.0)
		root.push_input(drag,true);await process_frame
	await touch(start+Vector2(0,-distance),false);await settle()

func run() -> void:
	root.content_scale_size=Vector2i.ZERO;root.size=Vector2i(800,600)
	var screen=Control.new();screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(screen)
	scroll=TouchScroll.new();scroll.position=Vector2(20,20);scroll.size=Vector2(320,220)
	scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;screen.add_child(scroll)
	var body=VBoxContainer.new();body.size_flags_horizontal=Control.SIZE_EXPAND_FILL;scroll.add_child(body)
	for index in range(12):
		var button=Button.new();button.text="Command %d"%index;button.custom_minimum_size=Vector2(280,60)
		button.pressed.connect(func():activated.append(index));body.add_child(button);rows.append(button)
	var outside=Button.new();outside.text="Outside";outside.position=Vector2(450,100);outside.size=Vector2(180,60);outside.pressed.connect(func():activated.append("outside"));screen.add_child(outside)
	await settle()
	verify(not ProjectSettings.get_setting("input_devices/pointing/emulate_mouse_from_touch",true),"test_uses_production_mouse_emulation_disabled")
	var source=rows[2].get_global_rect().get_center()
	await swipe(source,100)
	verify(scroll.scroll_vertical>=90,"drag_starting_on_a_button_scrolls_content")
	verify(activated.is_empty(),"scroll_begin_cancels_child_button_press")
	for index in range(5):await swipe(scroll.get_global_rect().get_center()+Vector2(0,60),150)
	verify(scroll.get_global_rect().grow(1).encloses(rows[-1].get_global_rect()),"repeated_direct_swipes_reach_last_command")
	verify(activated.is_empty(),"swipes_over_different_buttons_never_activate_commands")
	await touch(rows[-1].get_global_rect().get_center(),true);await touch(rows[-1].get_global_rect().get_center(),false)
	verify(activated==[11],"ordinary_touch_tap_activates_exactly_once_after_scroll")
	await touch(outside.get_global_rect().get_center(),true);await touch(outside.get_global_rect().get_center(),false)
	verify(activated==[11,"outside"],"scroll_does_not_capture_an_unrelated_control")
	var at=scroll.get_global_rect().get_center();await touch(at,true);scroll.hide();await settle()
	verify(scroll.touch_index==-1,"hiding_panel_clears_active_touch")
	await touch(at,false);scroll.show();await settle()
	var before=scroll.scroll_vertical
	for down in [true,false]:
		var wheel=InputEventMouseButton.new();wheel.button_index=MOUSE_BUTTON_WHEEL_UP;wheel.position=at;wheel.global_position=at;wheel.pressed=down;root.push_input(wheel,true)
	await settle()
	verify(scroll.scroll_vertical<before,"native_mouse_wheel_still_scrolls")
	var result={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"touch_component_sha256":FileAccess.get_sha256("res://presentation/touch_scroll.gd"),"mouse_emulation":false,"headless_component_test":true,"physical_android_device_tested":false,"synthetic_gameplay_evidence":false}
	var output=FileAccess.open("res://reports/touch_scroll_tests.json",FileAccess.WRITE);output.store_string(JSON.stringify(result,"\t"));output.close()
	print("TOUCH_SCROLL_TEST ",checks.size()," checks / ",failures.size()," failures")
	quit(0 if failures.is_empty() else 1)
