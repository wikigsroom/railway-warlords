extends SceneTree

var app: Control
var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func rifle_attack(state: Dictionary) -> Dictionary:
	for unit in state.units:
		if unit.owner_id!=state.player_faction_id or unit.def_id!="rifle" or unit.position==null:continue
		for target in state.units:
			if target.position==null or target.def_id!="rifle" or not StateAccess.hostile(state,unit.owner_id,target.owner_id):continue
			var c=VisualPlaytest.command(state,"Attack",{"unit_id":unit.id,"target_hex":target.position})
			if app.match_controller.kernel.preview(state,c).valid:return c
	return {}

func advance(state: Dictionary) -> Dictionary:
	var best={};var distance=999999
	for unit in state.units:
		if unit.owner_id!=state.player_faction_id or unit.def_id!="rifle" or unit.position==null or unit.ap_left<=0:continue
		var graph=MovementRules.reachable(state,unit,app.content)
		for key in graph.costs:
			var hex=HexGrid.from_key(key)
			if not StateAccess.at(state,"units",hex).is_empty():continue
			for target in state.units:
				if target.position==null or target.def_id!="rifle" or not StateAccess.hostile(state,unit.owner_id,target.owner_id):continue
				var d=HexGrid.distance(hex,HexGrid.coordinate(target.position))
				if d>=distance:continue
				var c=VisualPlaytest.command(state,"Move",{"unit_id":unit.id,"target_hex":HexGrid.position(hex)})
				if app.match_controller.kernel.preview(state,c).valid:distance=d;best=c
	return best

func run() -> void:
	app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/actions_%d"%Time.get_ticks_usec();root.add_child(app);await process_frame
	app.settings.tutorial=false;app.settings.music=false;app.settings.sound=false;app.apply_audio_settings()
	app.start_game("campaign_1924_03","zhili");app.close_overlay()
	var original=app.match_controller.state;var commands=[];var attack={}
	var recorder=func(c):commands.append(c.duplicate(true))
	app.match_controller.command_committed.connect(recorder)
	var ended=0
	for attempt in range(48):
		var state=app.match_controller.state;attack=rifle_attack(state)
		if not attack.is_empty():break
		var move=advance(state)
		if move.is_empty():
			if ended>=3:break
			ended+=1;app.match_controller.dispatch(VisualPlaytest.command(state,"EndPhase",{}))
			var deadline=Time.get_ticks_msec()+120000
			while app.match_controller.ai_running or app.match_controller.state.turn_order[app.match_controller.state.phase_index]!=app.match_controller.state.player_faction_id or app.match_controller.presentation_busy:
				if Time.get_ticks_msec()>deadline:failures.append("ai_contact_deadline");break
				app.map_view.playback.skip();await process_frame
			if not failures.is_empty():break
			continue
		if not app.match_controller.dispatch(move):break
		app.map_view.playback.skip()
		while app.match_controller.presentation_busy:await process_frame
	verify(not attack.is_empty(),"legal_rifle_against_rifle_contact_in_unmodified_published_campaign")
	if attack.is_empty():quit(1);return
	var before=app.match_controller.state;var attacker=StateAccess.find(before,"units",attack.unit_id);var defender=StateAccess.at(before,"units",HexGrid.coordinate(attack.target_hex))
	app.selected_unit_id=attacker.id;app.selected_city_id="";app.refresh_battle()
	var origin=HexGrid.to_world(HexGrid.coordinate(attacker.position));var target=HexGrid.to_world(HexGrid.coordinate(defender.position))
	app.map_view.zoom=1.65;app.map_view.camera=(origin+target)*.5;app.map_view.queue_redraw()
	verify(app.match_controller.dispatch(attack),"native_player_attack_committed")
	var playback=app.map_view.playback;playback.speed=0
	var sources=[];var directory="res://reports/screenshots/actions";DirAccess.make_dir_recursive_absolute(directory)
	for sample in [[.12,"ready"],[.42,"fire"],[.74,"hit"]]:
		playback.elapsed=playback.current.duration*sample[0]
		for frame in range(4):await process_frame
		app.map_view.queue_redraw()
		var apose=playback.pose_of(attacker);var dpose=playback.pose_of(defender)
		var adir=app.map_view.unit_orientation((target-origin).normalized(),"se",attacker).asset
		var ddir=app.map_view.unit_orientation((origin-target).normalized(),"se",defender).asset
		var aids=[app.assets.unit_action_id(attacker,adir,apose),app.assets.unit_action_id(defender,ddir,dpose)]
		verify(not aids[0].is_empty() and not aids[1].is_empty(),sample[1]+"_uses_real_directional_source_ids")
		if sample[1]=="fire":verify(apose=="fire" and dpose=="idle","attacker_changes_pose_before_impact")
		if sample[1]=="hit":verify(apose=="idle" and dpose=="hit","defender_changes_pose_at_impact")
		await VisualPlaytest.capture(app,directory+"/"+sample[1]+".png")
		sources.append({"stage":sample[1],"attacker_asset":aids[0],"defender_asset":aids[1],"attacker_pose":apose,"defender_pose":dpose})
	playback.skip()
	while app.match_controller.presentation_busy:await process_frame
	var replay=original
	for c in commands:
		var result=app.match_controller.kernel.resolve(replay,c)
		if not result.valid:failures.append("replay_rejected");break
		replay=result.state
	verify(ContentRegistry.fingerprint(replay)==ContentRegistry.fingerprint(app.match_controller.state),"native_pose_changes_preserve_complete_command_replay_and_rng")
	var report={"passed":failures.is_empty(),"failures":failures,"checks":checks,"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"commands":commands,"sources":sources,"published_deployment_unchanged":true,"raw_godot_capture":true,"manual_compositing":false,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/unit_action_native_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("UNIT_ACTION_NATIVE_TEST ",checks.size()," checks / ",failures.size()," failures")
	app.audio.stop_all();await create_timer(.1).timeout;quit(0 if failures.is_empty() else 1)
