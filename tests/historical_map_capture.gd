extends SceneTree

func _init() -> void:run.call_deferred()

func run() -> void:
	var app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/calendar_%d"%Time.get_ticks_usec();root.add_child(app)
	await process_frame
	if app.content.errors.size()>0:push_error("Calendar capture content load failed");quit(1);return
	# Isolate QA saves and mark the state as debug. This exercises the actual
	# game scene with a calendar fixture, not a played campaign or physical phone.
	app.settings.tutorial=false
	app.start_game("conq_1924","zhili")
	var state=app.match_controller.state;state.date="1925-02-09";state.round=24;state.debug_match=true
	var events: Array=[];TurnRules.round_start(state,app.content,events)
	app.match_controller.paused=true;app.map_view.set_state(state,events);app.refresh_battle()
	await process_frame;await process_frame
	app.close_overlay();await process_frame;app.match_controller.paused=true
	app.map_view.camera=app.map_view.world_bounds.get_center();app.map_view.zoom=.28;app.map_view.clamp_camera();app.map_view.queue_redraw()
	await RenderingServer.frame_post_draw
	var path="res://reports/screenshots/map_1925_calendar_fixture.png"
	var labels=state.map.admin_layers[ContentRegistry.administration_year(state.date)].map(func(r):return ContentRegistry.administration_label(r.name,state.date))
	var saved=root.get_viewport().get_texture().get_image().save_png(path)
	var passed=saved==OK and not is_instance_valid(app.overlay) and labels.has("西康特别区") and not labels.has("川边特别区")
	var metadata={"passed":passed,"viewport":root.get_viewport().get_visible_rect().size,"window":DisplayServer.window_get_size(),"content_hash":app.content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"raw_godot_capture":true,"calendar_fixture_only":true,"gameplay_completed_to_this_date":false,"date":state.date,"round":state.round,"region_labels":labels,"physical_android_device_tested":false,"mobile_layout_profile":false,"ui_scale":app.settings.ui_scale,"scope":"Native source game scene with isolated QA saves; checks calendar labels, not exported-executable playthrough or historical military control."}
	var file=FileAccess.open(path.get_basename()+".json",FileAccess.WRITE);file.store_string(JSON.stringify(metadata,"\t"));file.close()
	print("HISTORICAL_CALENDAR_CAPTURE ",JSON.stringify(metadata));quit(0 if passed else 1)
