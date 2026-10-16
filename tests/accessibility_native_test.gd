extends SceneTree

const ExactFingerprint = preload("res://tests/immutable_state_fingerprint.gd")

var app
var output_root = ""
var checks: Array = []
var failures: Array = []
var captures: Array = []
var control_geometry: Array = []
var fingerprints = ExactFingerprint.new()
var logical_viewport = false

func _init() -> void:
	run.call_deferred()

func argument(name: String, fallback: String) -> String:
	var args = OS.get_cmdline_user_args()
	var index = args.find(name)
	return args[index + 1] if index >= 0 and index + 1 < args.size() else fallback

func check(value: bool, name: String) -> void:
	checks.append({"name": name, "passed": value})
	if not value:
		failures.append(name)

func settle() -> void:
	for index in range(6):
		await process_frame

func button_named(parent: Node, text: String) -> BaseButton:
	for node in app.ui_nodes(parent):
		if node is BaseButton and node.text == text:
			return node
	return null

func click(point: Vector2) -> void:
	# Deliver mouse events through the real viewport GUI dispatcher. These are
	# window coordinates, including the actual content-scale transform.
	var window_point = root.get_final_transform() * point
	var press = InputEventMouseButton.new()
	press.button_index = MOUSE_BUTTON_LEFT
	press.position = window_point
	press.global_position = window_point
	press.pressed = true
	root.push_input(press)
	var release = press.duplicate()
	release.pressed = false
	root.push_input(release)
	await settle()

func check_button(node: BaseButton, name: String) -> void:
	if node == null:
		check(false, name + ":present")
		return
	var rect = node.get_global_rect()
	var viewport = app.get_viewport_rect()
	var minimum = node.get_combined_minimum_size()
	var fits = node.is_visible_in_tree() and viewport.encloses(rect) and rect.size.x + .1 >= minimum.x and rect.size.y + .1 >= minimum.y
	control_geometry.append({"control": name, "text": node.text, "rectangle": [rect.position.x, rect.position.y, rect.size.x, rect.size.y], "minimum": [minimum.x, minimum.y], "viewport": [viewport.size.x, viewport.size.y], "fully_inside_viewport": viewport.encloses(rect)})
	check(fits, name + ":visible_minimum_and_full_bounds")

func capture(name: String) -> void:
	await settle()
	if not logical_viewport:
		await RenderingServer.frame_post_draw
	if logical_viewport:
		# The dummy headless renderer intentionally has no raster texture.
		# Record the requested logical canvas without fabricating pixels.
		captures.append({"file": name + ".logical.json", "pixels": [root.size.x, root.size.y], "raw_godot_capture": false, "logical_layout_only": true})
		return
	var texture = root.get_texture()
	var image = texture.get_image() if texture != null else null
	var path = output_root.path_join(name + ".png")
	check(image.save_png(path) == OK, name + ":raw_native_capture_saved")
	captures.append({"file": name + ".png", "pixels": [image.get_width(), image.get_height()], "sha256": FileAccess.get_sha256(path), "raw_godot_capture": true})

func run() -> void:
	output_root = argument("--output-root", "res://reports/accessibility/adhoc")
	DirAccess.make_dir_recursive_absolute(output_root)
	logical_viewport = "--logical-viewport" in OS.get_cmdline_user_args()
	print("ACCESS_STAGE init logical=", logical_viewport)
	var expected = argument("--expected-window", "1280x720").split("x")
	var requested = Vector2i(int(expected[0]), int(expected[1]))
	app = load("res://app/main.tscn").instantiate()
	app.qa_save_path = "user://qa/accessibility/" + str(Time.get_ticks_usec())
	root.add_child(app)
	await settle()
	print("ACCESS_STAGE app_ready root=", root.size)
	if logical_viewport:
		# A headless logical canvas lets us exercise the full 4K layout on a
		# lower-resolution host without claiming a physical 4K display result.
		root.size = requested
		await settle()
		print("ACCESS_STAGE logical_size root=", root.size)
	app.settings.tutorial = false
	app.start_game("campaign_1924_02", "zhili")
	app.close_overlay()
	await settle()
	print("ACCESS_STAGE battle_ready viewport=", app.get_viewport_rect().size)
	check(DisplayServer.get_name() != "headless" or logical_viewport, "native_graphical_window_or_explicit_logical_canvas")
	check((root.size == requested) if logical_viewport else DisplayServer.window_get_size() == requested, "actual_requested_window_dimensions")
	check((logical_viewport and is_instance_valid(app.audio)) or (is_instance_valid(app.audio.music) and app.audio.players.size() == 8), "native_audio_players_initialized_or_headless_audio_policy")
	check(is_equal_approx(app.settings.ui_scale, float(argument("--ui-scale", "1.0"))), "requested_ui_font_scale_active")
	var initial_state = fingerprints.state_hash(app.match_controller.state)
	var map_clicks: Array = []
	app.map_view.hex_selected.connect(func(hex): map_clicks.append(hex))
	var screen_rect = app.get_viewport_rect()
	check(screen_rect.encloses(app.map_view.get_global_rect()) and app.map_view.size.x >= 600 and app.map_view.size.y >= 400, "map_and_inspector_layout_preserves_playable_area")
	for name in ["战报", "存档", "设置"]:
		check_button(button_named(app.header, name), "header_" + name)
	for name in ["移动", "攻击", "待命部队", "结束回合  →"]:
		check_button(button_named(app.orders, name), "orders_" + name)
	var resources: Array = []
	for node in app.ui_nodes(app.header):
		if node is Label and node.text in ["军费", "粮秣", "军备"]:
			resources.append(node.text)
			check(screen_rect.encloses(node.get_global_rect()), "resource_label_" + node.text + "_inside_viewport")
	check(resources.size() == 3, "all_three_resource_labels_present")
	await capture("01_battle")
	print("ACCESS_STAGE capture_battle")
	var pause = button_named(app.header, "设置")
	if pause != null:
		await click(pause.get_global_rect().get_center())
	check(is_instance_valid(app.overlay) and app.match_controller.paused, "real_header_click_opens_paused_modal")
	if is_instance_valid(app.overlay):
		for name in ["继续指挥", "保存战局", "读取战局", "设置", "关闭"]:
			check_button(button_named(app.overlay, name), "pause_" + name)
		await capture("02_pause")
		print("ACCESS_STAGE capture_pause")
		await click(app.map_view.get_global_rect().get_center())
		check(map_clicks.is_empty(), "modal_blocks_real_mouse_click_through_to_map")
		var settings = button_named(app.overlay, "设置")
		if settings != null:
			await click(settings.get_global_rect().get_center())
		var music = button_named(app.overlay, "音乐")
		var sound = button_named(app.overlay, "音效")
		check(music != null and sound != null, "real_pause_settings_click_opens_audio_controls")
		if music != null and sound != null:
			check_button(music, "settings_music")
			check_button(sound, "settings_sound")
			await click(music.get_global_rect().get_center())
			await click(sound.get_global_rect().get_center())
			check(not app.settings.music and not app.settings.sound, "real_mouse_controls_disable_music_and_effects")
			check(logical_viewport or not app.audio.music.playing, "muted_music_player_stopped")
			var cursor = app.audio.cursor
			app.audio.play("rifle")
			await settle()
			check(app.audio.cursor == cursor and app.audio.players.all(func(player): return not player.playing), "muted_real_effect_request_starts_no_audio_player")
			var settings_state = app.saves.load_slot("settings")
			check(not settings_state.get("music", true) and not settings_state.get("sound", true), "muted_settings_saved_and_reloaded_in_isolated_slot")
		await capture("03_settings_muted")
		print("ACCESS_STAGE capture_settings")
		var close = button_named(app.overlay, "关闭")
		check_button(close, "settings_close")
		if close != null:
			await click(close.get_global_rect().get_center())
		check(not is_instance_valid(app.overlay) and not app.match_controller.paused, "real_modal_close_returns_to_battle")
	check(fingerprints.state_hash(app.match_controller.state) == initial_state, "ui_modal_and_mute_interaction_preserves_full_match_and_rng")
	check(captures.size() == 3 and captures.all(func(row): return row.pixels == [requested.x, requested.y]) and (logical_viewport or captures.all(func(row): return row.raw_godot_capture)), "three_full_requested_captures_or_logical_layout_records")
	var report = {"passed": failures.is_empty(), "checks": checks, "failures": failures, "game_version": ContentRegistry.APP_VERSION, "content_hash": app.content.content_hash, "requested_window": [requested.x, requested.y], "actual_window": [DisplayServer.window_get_size().x, DisplayServer.window_get_size().y], "logical_viewport": [screen_rect.size.x, screen_rect.size.y], "logical_4k_profile": logical_viewport, "ui_scale": app.settings.ui_scale, "renderer": RenderingServer.get_current_rendering_method(), "gpu": RenderingServer.get_video_adapter_name(), "qa_save_isolated": true, "physical_android_device_tested": false, "captures": captures, "control_geometry": control_geometry, "scope": "Native Windows project runtime, or explicit headless logical canvas when logical_4k_profile is true. Actual viewport mouse dispatch, key-button bounds, resource labels, modal input blocking, persisted mute and audio policy. Entire raw viewport captures; no crop or composite. Logical 4K does not replace a physical 4K display or Android device test."}
	var file = FileAccess.open(output_root.path_join("result.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("ACCESSIBILITY_RESULT ", JSON.stringify({"passed": report.passed, "checks": checks.size(), "failures": failures, "window": report.actual_window}))
	app.audio.stop_all()
	quit(0 if report.passed else 1)
