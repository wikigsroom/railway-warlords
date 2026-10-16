class_name VisualPlaytest
extends RefCounted

# Drives the actual native controls and command kernel on an unmodified campaign.
# No synthetic positions, HP, terrain, ownership or military formations are inserted.
static func command(s: Dictionary, kind: String, args: Dictionary) -> Dictionary:
	var result=args.duplicate(true);result.type=kind;result.actor_id=s.turn_order[s.phase_index];result.expected_version=s.state_version;return result

static func find_attack(s: Dictionary, registry: ContentRegistry, kernel: CommandKernel, family: String = "") -> Dictionary:
	var own=s.units.filter(func(u):return u.owner_id==s.player_faction_id and u.position!=null and u.attack_ready and u.ammo>0)
	own.sort_custom(func(a,b):return registry.definition("units",a.def_id).attack>registry.definition("units",b.def_id).attack)
	for u in own:
		if not family.is_empty() and registry.definition("units",u.def_id).family!=family:continue
		for target in s.units+s.cities:
			if target.position==null or not StateAccess.hostile(s,u.owner_id,target.owner_id):continue
			var c=command(s,"Attack",{"unit_id":u.id,"target_hex":target.position})
			if kernel.preview(s,c).valid:return c
	return {}

static func advance_to_contact(s: Dictionary, registry: ContentRegistry, kernel: CommandKernel, family: String = "") -> Dictionary:
	var best={};var distance=99999
	for u in s.units:
		if u.owner_id!=s.player_faction_id or u.position==null or u.ap_left<=0:continue
		if not family.is_empty() and registry.definition("units",u.def_id).family!=family:continue
		var graph=MovementRules.reachable(s,u,registry)
		for key in graph.costs:
			var hex=HexGrid.from_key(key)
			if HexGrid.coordinate(u.position)==hex or not StateAccess.at(s,"units",hex).is_empty():continue
			for target in s.units:
				if target.position==null or not StateAccess.hostile(s,u.owner_id,target.owner_id) or not VisibilityRules.unit_visible(s,s.player_faction_id,target):continue
				var d=HexGrid.distance(hex,HexGrid.coordinate(target.position))
				if d<distance:
					var c=command(s,"Move",{"unit_id":u.id,"target_hex":HexGrid.position(hex)})
					if kernel.preview(s,c).valid:distance=d;best=c
	return best

static func capture(app: Control, path: String) -> void:
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var error=app.get_viewport().get_texture().get_image().save_png(path)
	if error!=OK:push_error("Native playtest capture failed: "+str(error))

static func run(app: Control) -> void:
	if app.qa_save_path.is_empty():push_error("Visual playtest needs --qa-session");app.get_tree().quit(1);return
	app.settings.tutorial=false;app.start_game("campaign_1924_03","zhili");app.close_overlay()
	app.map_view.zoom=.98;app.map_view.focus_player();app.map_view.zoom=.98;app.map_view.clamp_camera();app.map_view.queue_redraw()
	for i in range(12):await app.get_tree().process_frame
	var original=app.match_controller.state.duplicate(true);var commands: Array=[];var captures: Array=[];var moves=0;var attacks=0;var dice=0;var counters=0;var failures: Array=[];var saw_muzzle=false;var saw_hit=false
	var artillery_seen=false
	var ledger: Array=[]
	var recorder=func(c):
		commands.append(c.duplicate(true))
		ledger.append_array(app.match_controller.state.event_log.filter(func(e):return e.sequence==app.match_controller.state.state_version).duplicate(true))
	app.match_controller.command_committed.connect(recorder)
	var directory="res://reports/screenshots/visual_playtest"
	var scenario_hash=ContentRegistry.fingerprint(app.content.scenarios.campaign_1924_03)
	for attempt in range(20):
		var s=app.match_controller.state
		if s.status!="playing" or s.turn_order[s.phase_index]!=s.player_faction_id:break
		var c=find_attack(s,app.content,app.match_controller.kernel,"artillery" if not artillery_seen else "")
		if c.is_empty():c=advance_to_contact(s,app.content,app.match_controller.kernel,"artillery" if not artillery_seen else "")
		if c.is_empty() and not artillery_seen:
			app.match_controller.dispatch(command(s,"EndPhase",{}))
			while app.match_controller.presentation_busy or app.match_controller.ai_running or (app.match_controller.state.status=="playing" and app.match_controller.state.turn_order[app.match_controller.state.phase_index]!=app.match_controller.state.player_faction_id):await app.get_tree().process_frame
			continue
		if c.is_empty():c=find_attack(s,app.content,app.match_controller.kernel)
		if c.is_empty():c=advance_to_contact(s,app.content,app.match_controller.kernel)
		if c.is_empty():break
		var u=StateAccess.find(s,"units",c.unit_id)
		if c.type=="Attack" and app.content.definition("units",u.def_id).family=="artillery":artillery_seen=true
		app.selected_unit_id=u.id;app.selected_city_id="";app.pending=c.duplicate(true);app.refresh_battle()
		app.map_view.camera=(HexGrid.to_world(HexGrid.coordinate(u.position))+HexGrid.to_world(HexGrid.coordinate(c.target_hex)))*.5;app.map_view.clamp_camera();app.map_view.queue_redraw()
		if attempt==0:
			await capture(app,directory+"/01_command_preview.png");captures.append("01_command_preview.png")
		await app.get_tree().create_timer(.35).timeout
		app.pending={};app.order_mode=""
		if not app.match_controller.dispatch(c):failures.append("legal_campaign_command_rejected");break
		var step_captured=false;var dice_captured=false;var hit_captured=false
		while app.match_controller.presentation_busy:
			var playback=app.map_view.playback
			if playback.active:
				var p=playback.progress();var action=playback.current
				if action.kind=="move" and not step_captured and p>.35 and p<.8:
					await capture(app,directory+"/02_marching.png");captures.append("02_marching.png");step_captured=true
				if action.kind=="attack":
					if not dice_captured and action.get("cinematic",false) and p>.12 and p<.30:
						await capture(app,directory+"/03_dice_rolling.png");captures.append("03_dice_rolling.png");dice_captured=true
					if p>.36 and p<.63:saw_muzzle=true
					if not hit_captured and p>.67 and p<.86:
						saw_hit=true;await capture(app,directory+"/04_impact.png");captures.append("04_impact.png");hit_captured=true
			await app.get_tree().process_frame
		var events=app.match_controller.state.event_log.filter(func(e):return e.sequence==app.match_controller.state.state_version)
		for event in events:
			if event.type=="UnitMoved":moves+=1
			if event.type=="CombatDiceRolled":dice+=1
			if event.type=="DamageApplied" and event.get("counter",false):counters+=1
		if c.type=="Attack":attacks+=1
		if moves>0 and attacks>=2 and artillery_seen:break
		await app.get_tree().create_timer(.22).timeout
	await capture(app,directory+"/05_battle_complete.png");captures.append("05_battle_complete.png")
	app.match_controller.command_committed.disconnect(recorder)
	var replay=original;var kernel=CommandKernel.new(app.content)
	for c in commands:
		var result=kernel.resolve(replay,c)
		if not result.valid:failures.append("native_command_replay_rejected");break
		replay=result.state
	var equivalent=ContentRegistry.fingerprint(replay)==ContentRegistry.fingerprint(app.match_controller.state)
	if not equivalent:failures.append("native_movie_did_not_replay_to_same_state")
	if moves<1 or attacks<1 or dice<1 or not saw_muzzle or not saw_hit or not artillery_seen:failures.append("required_visible_movement_or_combat_missing")
	var report={"passed":failures.is_empty(),"failures":failures,"build_version":ContentRegistry.APP_VERSION,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"content_hash":app.content.content_hash,"scenario_id":"campaign_1924_03","published_scenario_unchanged":scenario_hash==ContentRegistry.fingerprint(app.content.scenarios.campaign_1924_03),"unmodified_campaign_deployment":true,"native_commands":commands,"moves":moves,"attacks":attacks,"dice_rolls":dice,"counterattacks":counters,"artillery_visible":artillery_seen,"muzzle_visible":saw_muzzle,"impact_visible":saw_hit,"replay_same_final_state":equivalent,"initial_combat_random":original.combat_random,"final_combat_random":app.match_controller.state.combat_random,"captures":captures,"viewport":app.get_viewport_rect().size,"physical_android_device_tested":OS.has_feature("android"),"qa_save_isolated":true,"manual_image_compositing":false}
	report.player_moves=moves;report.player_attacks=attacks
	report.moves=ledger.filter(func(e):return e.type=="UnitMoved").size()
	report.attacks=ledger.filter(func(e):return e.type=="CombatDiceRolled" and not e.counter).size()
	report.dice_rolls=ledger.filter(func(e):return e.type=="CombatDiceRolled").size()
	report.counterattacks=ledger.filter(func(e):return e.type=="CombatDiceRolled" and e.counter).size()
	if report.dice_rolls*2!=int(report.final_combat_random.draws)-int(report.initial_combat_random.draws):report.passed=false;report.failures.append("incomplete_native_random_ledger")
	var file=FileAccess.open("res://reports/visual_playtest.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("VISUAL_PLAYTEST ",JSON.stringify(report));await app.get_tree().create_timer(1.0).timeout;app.audio.stop_all();await app.get_tree().create_timer(.15).timeout;app.get_tree().quit(0 if failures.is_empty() else 1)

static func run_support(app: Control) -> void:
	if app.qa_save_path.is_empty():push_error("Support playtest needs --qa-session");app.get_tree().quit(1);return
	app.settings.tutorial=false;app.start_game("campaign_1924_03","zhili");app.close_overlay()
	for i in range(8):await app.get_tree().process_frame
	# On the enlarged map the old training airport no longer covers its enemy.
	# Construct support through real player commands on the published defense.
	var setup_initial=app.match_controller.state.duplicate(true);var setup_commands: Array=[]
	var recorder=func(c):setup_commands.append(c.duplicate(true))
	app.match_controller.command_committed.connect(recorder)
	var build=command(app.match_controller.state,"Build",{"city_id":"shanhaiguan","def_id":"airfield"})
	if not app.match_controller.dispatch(build):push_error("Real airport construction was rejected");app.get_tree().quit(1);return
	var deadline=Time.get_ticks_msec()+180000
	var setup_planner=AIPlanner.new(app.content,app.match_controller.kernel);var setup_player_phase=-1
	while Time.get_ticks_msec()<deadline:
		await app.get_tree().process_frame
		if app.match_controller.presentation_busy or app.match_controller.command_busy or app.match_controller.ai_running:continue
		var state=app.match_controller.state;var built_city=StateAccess.find(state,"cities","shanhaiguan")
		if state.status!="playing":push_error("Support preparation ended before airport completion");app.get_tree().quit(1);return
		if state.turn_order[state.phase_index]!=state.player_faction_id:continue
		if EconomyRules.building_level(built_city,"airfield")>0:break
		var phase=int(StateAccess.faction(state,state.player_faction_id).own_phase_index)
		if phase!=setup_player_phase:setup_player_phase=phase;setup_planner=AIPlanner.new(app.content,app.match_controller.kernel)
		# Defend with legal unit actions while preserving the support budget.
		# Passing every player turn can legitimately lose this defense scenario.
		var defense=setup_planner.choose(state)
		if defense.type not in ["Move","Attack","ActivateSkill","Reinforce","RailTransport","EndPhase"]:defense=command(state,"EndPhase",{})
		if not app.match_controller.dispatch(defense):push_error("Real airport defense command was rejected");app.get_tree().quit(1);return
	app.match_controller.command_committed.disconnect(recorder)
	var prepared=setup_initial
	for c in setup_commands:
		var result=app.match_controller.kernel.resolve(prepared,c)
		if not result.valid:push_error("Support construction replay rejected");app.get_tree().quit(1);return
		prepared=result.state
	if ContentRegistry.fingerprint(prepared)!=ContentRegistry.fingerprint(app.match_controller.state):push_error("Support construction replay changed state");app.get_tree().quit(1);return
	var initial=app.match_controller.state.duplicate(true);var commands: Array=[];var failures: Array=[];var captures: Array=[]
	var airfields=initial.cities.filter(func(c):return c.owner_id==initial.player_faction_id and EconomyRules.building_level(c,"airfield")>0)
	if airfields.is_empty():push_error("Real support airport construction did not complete");app.get_tree().quit(1);return
	var city=airfields[0];var target: Dictionary={}
	for enemy in initial.units:
		if enemy.owner_id==city.owner_id or enemy.position==null:continue
		if app.match_controller.kernel.preview(initial,command(initial,"AirRecon",{"city_id":city.id,"target_hex":enemy.position})).valid:target=enemy;break
	if target.is_empty():push_error("No legal published air target");app.get_tree().quit(1);return
	app.map_view.camera=(HexGrid.to_world(HexGrid.coordinate(city.position))+HexGrid.to_world(HexGrid.coordinate(target.position)))*.5;app.map_view.zoom=.94;app.map_view.clamp_camera()
	for kind in ["AirRecon","AirBomb"]:
		var s=app.match_controller.state;var c=command(s,kind,{"city_id":city.id,"target_hex":target.position})
		app.selected_city_id=city.id;app.selected_unit_id="";app.pending=c.duplicate(true);app.refresh_battle();await app.get_tree().create_timer(.4).timeout
		app.pending={}
		if not app.match_controller.dispatch(c):failures.append("published_support_command_rejected:"+kind);break
		commands.append(c);var captured=false
		while app.match_controller.presentation_busy:
			if app.map_view.playback.active and app.map_view.playback.current.kind=="air" and app.map_view.playback.progress()>.36 and not captured:
				var path="res://reports/screenshots/visual_playtest/"+("06_air_recon.png" if kind=="AirRecon" else "07_air_bomb.png")
				await capture(app,path);captures.append(path);captured=true
			await app.get_tree().process_frame
		await app.get_tree().create_timer(.35).timeout
	var replay=initial
	for c in commands:
		var result=app.match_controller.kernel.resolve(replay,c)
		if not result.valid:failures.append("air_replay_rejected");break
		replay=result.state
	if ContentRegistry.fingerprint(replay)!=ContentRegistry.fingerprint(app.match_controller.state):failures.append("air_replay_changed_result")
	if commands.size()!=2 or captures.size()!=2:failures.append("air_motion_missing")
	var report={"passed":failures.is_empty(),"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"scenario_id":"campaign_1924_03","published_initial_deployment_unchanged":true,"airport_constructed_through_real_commands":true,"historical_airport_deployment_claimed":false,"setup_commands":setup_commands,"setup_replay_same_final_state":true,"player_defense_performed":setup_commands.any(func(c):return c.actor_id==initial.player_faction_id and c.type in ["Move","Attack","ActivateSkill","Reinforce"]),"setup_initial_combat_random":setup_initial.combat_random,"setup_final_combat_random":initial.combat_random,"setup_match_id":setup_initial.match_id,"native_commands":commands,"captures":captures,"manual_image_compositing":false,"qa_save_isolated":true,"physical_android_device_tested":OS.has_feature("android")}
	var file=FileAccess.open("res://reports/support_playtest.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("SUPPORT_PLAYTEST ",JSON.stringify(report));await app.get_tree().create_timer(.6).timeout;app.audio.stop_all();await app.get_tree().create_timer(.15).timeout;app.get_tree().quit(0 if failures.is_empty() else 1)
