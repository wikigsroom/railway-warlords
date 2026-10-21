extends SceneTree
var app
func _init() -> void:execute.call_deferred()
func settle(frames: int) -> void:
    for i in frames:await process_frame
func execute() -> void:
    var modes=load("res://reports/map_pan_v0233/perf_final_03_optimized/profiled_map_view.gd");modes.legacy=false
    app=load("res://app/main.tscn").instantiate();root.add_child(app);await settle(20)
    app.settings.tutorial=false;app.start_game("campaign_1924_03",app.content.scenarios.campaign_1924_03.player_default);app.close_overlay();await settle(20)
    if app.map_view==null:quit(1);return
    var view=app.map_view;view.camera=Vector2(16848,7000);view.zoom=1.05
    Engine.max_fps=0;DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED);await settle(90)
    var source=load("res://reports/map_pan_v0233/perf_final_03_optimized/profiled_map_view.gd")
    source.timings.clear();source.recording=true
    var prefetch_before={"requested":app.assets.map_prefetch_requested,"completed":app.assets.map_prefetch_completed,"sync_misses":app.assets.synchronous_map_misses}
    var before=ContentRegistry.fingerprint(app.match_controller.state);var frames: Array=[];var focused=0;var rebuilds=view.backdrop_rebuilds
    for i in 180:
        view.camera=Vector2(16848,7000)+Vector2(sin(float(i)*TAU/180.0)*420.0,cos(float(i)*TAU/180.0)*180.0);view.queue_redraw()
        var began=Time.get_ticks_usec();await process_frame;frames.append((Time.get_ticks_usec()-began)/1000.0)
        if DisplayServer.window_is_focused():focused+=1
    source.recording=false
    var report={"version":ContentRegistry.APP_VERSION,"kind":"native_instrumented_development_cpu_profile","legacy_methods":false,"static_atlas_ms":source.timings,"prefetch_before":prefetch_before,"prefetch_after":{"requested":app.assets.map_prefetch_requested,"completed":app.assets.map_prefetch_completed,"sync_misses":app.assets.synchronous_map_misses},"frame_ms":frames,"state_unchanged":before==ContentRegistry.fingerprint(app.match_controller.state),"focused_frames":focused,"backdrop_rebuilds":view.backdrop_rebuilds-rebuilds,"gpu":RenderingServer.get_video_adapter_name(),"physical_android_device_tested":false,"other_application_gpu_cpu_load_controlled":false}
    var output=FileAccess.open("res://reports/map_pan_v0233/perf_final_03_optimized/profile.json",FileAccess.WRITE);output.store_string(JSON.stringify(report,"\t"));output.close()
    print("PROFILE_COMPLETE state_unchanged=",report.state_unchanged);quit(0 if report.state_unchanged else 1)
