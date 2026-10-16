extends SceneTree

var content=ContentRegistry.new()
var kernel: CommandKernel
var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)
func command(s: Dictionary, kind: String, args: Dictionary={}) -> Dictionary:
	var c=args.duplicate(true);c.type=kind;c.actor_id=s.turn_order[s.phase_index];c.expected_version=s.state_version;return c

# Deliberately synthetic QA arena, never included in the published scenario list.
# Small fixed positions isolate counterfire, kill, fog and persisted RNG behavior.
func fixture() -> Dictionary:
	var s=StateBuilder.create(content,"campaign_1920_01","zhili",{})
	s.units=[];s.cities=[];s.generals=[];s.visibility=[];s.statuses=[];s.engineer_jobs=[];s.authored_events=[];s.protected_commander_id=null;s.protected_general_id=null
	s.objectives=[{"id":"qa","type":"capture","target_ids":["never"],"required":1,"progress":0,"protected":false}]
	s.map.cells=[];s.map.rail_edges=[];s.map.rail_nodes=[];s.map.crossings=[]
	for q in range(-4,6):
		for r in range(-4,6):s.map.cells.append({"id":"qa_%d_%d"%[q,r],"position":{"q":q,"r":r},"terrain_id":"plain","region_id":"theater"})
	for entry in [["a","rifle","zhili",Vector2i(0,0)],["b","rifle","anhui",Vector2i(1,0)],["c","rifle","zhili",Vector2i(0,1)],["d","machine_gun","anhui",Vector2i(1,1)]]:
		s.units.append(StateBuilder.unit(entry[0],entry[1],entry[2],HexGrid.position(entry[3]),content))
	StateAccess.invalidate_occupancy();VisibilityRules.refresh(s,content)
	return s

func run() -> void:
	verify(content.load_all(),"published_content_loads");kernel=CommandKernel.new(content)
	var s=fixture();s.combat_random.state=12345
	var c=command(s,"Attack",{"unit_id":"a","target_hex":{"q":1,"r":0}})
	var fingerprint=ContentRegistry.fingerprint(s);var preview=kernel.preview(s,c)
	for i in range(30):kernel.preview(s,c)
	verify(preview.valid and ContentRegistry.fingerprint(s)==fingerprint and s.combat_random.draws==0,"repeated_previews_preserve_entire_state_and_random_stream")
	var result=kernel.resolve(s,c)
	verify(result.valid and ContentRegistry.fingerprint(s)==fingerprint,"attack_transaction_preserves_input_snapshot")
	var rolls=result.events.filter(func(e):return e.type=="CombatDiceRolled")
	verify(rolls.size()==2 and result.state.combat_random.draws==4,"primary_and_counter_use_separate_pairs_of_persisted_dice")
	verify(rolls.all(func(e):return e.attack_die>=1 and e.attack_die<=6 and e.defense_die>=1 and e.defense_die<=6 and e.modifier_permille>=825 and e.modifier_permille<=1175),"recorded_faces_and_modifiers_within_advertised_bounds")
	var damages: Dictionary={};var all_in_range=true
	for seed_value in range(1,19):
		var trial=StateAccess.clone_transaction(s);trial.combat_random.state=seed_value
		var outcome=kernel.resolve(trial,c)
		var hits=outcome.events.filter(func(e):return e.type=="DamageApplied" and not e.counter)
		var counters=outcome.events.filter(func(e):return e.type=="DamageApplied" and e.counter)
		if hits.is_empty():all_in_range=false;continue
		damages[hits[0].amount]=true
		all_in_range=all_in_range and hits[0].amount>=preview.damage_min and hits[0].amount<=preview.damage_max
		if not counters.is_empty():all_in_range=all_in_range and counters[0].amount>=preview.counter_min and counters[0].amount<=preview.counter_max
	verify(all_in_range and damages.size()>1,"different_rolls_change_real_damage_inside_preview_ranges")
	var stale=c.duplicate(true);stale.expected_version=-1
	var friendly=c.duplicate(true);friendly.target_hex={"q":0,"r":1}
	verify(not kernel.resolve(s,stale).valid and not kernel.resolve(s,friendly).valid and ContentRegistry.fingerprint(s)==fingerprint,"stale_and_friendly_fire_commands_do_not_draw_random_numbers")
	var saves=SaveService.new("user://qa/combat_presentation_%d"%Time.get_ticks_usec())
	verify(saves.write("test",result.state,content.content_hash),"committed_dice_state_saves_with_checksum")
	var loaded=saves.load_slot("test",content.content_hash)
	var next_command=command(result.state,"Attack",{"unit_id":"c","target_hex":{"q":1,"r":1}})
	var replay=kernel.resolve(loaded,next_command);var uninterrupted=kernel.resolve(result.state,next_command)
	verify(replay.valid and uninterrupted.valid and ContentRegistry.fingerprint(replay.state)==ContentRegistry.fingerprint(uninterrupted.state),"save_load_replays_next_battle_to_identical_complete_state")
	var corrupt=StateAccess.clone_transaction(result.state);corrupt.combat_random.state=0;saves.write("test",corrupt,content.content_hash)
	verify(saves.load_slot("test",content.content_hash).is_empty(),"checksummed_but_invalid_random_stream_is_rejected")
	var dead=StateAccess.clone_transaction(s);StateAccess.find(dead,"units","b").hp=1
	var death=kernel.resolve(dead,c)
	verify(death.valid and death.events.filter(func(e):return e.type=="CombatDiceRolled").size()==1 and death.state.combat_random.draws==2,"destroyed_defender_never_counterfires_or_draws_counter_dice")
	verify(death.events.any(func(e):return e.type=="UnitDefeated" and e.unit_id=="b" and e.position=={"q":1,"r":0}),"fatal_hits_keep_position_for_visible_destruction")
	var veteran=StateAccess.clone_transaction(dead);StateAccess.find(veteran,"units","a").experience=18
	var promotion=kernel.resolve(veteran,c)
	verify(promotion.valid and StateAccess.find(promotion.state,"units","a").experience==24 and promotion.events.any(func(e):return e.type=="UnitPromoted" and e.rank==1),"surviving_formation_earns_attack_and_kill_experience_and_promotes")
	verify(VeterancyRules.bonus(StateAccess.find(promotion.state,"units","a"))==30 and StateAccess.find(veteran,"units","a").experience==18,"veterancy_bonus_applies_only_to_committed_surviving_formation")
	var playback=BattlePlayback.new();var sounds: Array=[];playback.cue.connect(func(id):sounds.append(id))
	playback.begin(s,result.state,result.events,content)
	verify(playback.active and StateAccess.find({"units":playback.units},"units","b").hp==StateAccess.find(s,"units","b").hp,"animation_starts_with_pre_hit_visual_health")
	playback.tick(.5)
	verify(not playback.cue_flags.has("hit") and StateAccess.find({"units":playback.units},"units","b").hp==StateAccess.find(s,"units","b").hp,"health_does_not_change_while_dice_are_rolling")
	playback.tick(.55)
	verify(playback.cue_flags.has("hit") and StateAccess.find({"units":playback.units},"units","b").hp==StateAccess.find(result.state,"units","b").hp,"visual_health_changes_at_projectile_impact")
	var committed=ContentRegistry.fingerprint(result.state);playback.skip()
	verify(not playback.active and ContentRegistry.fingerprint(result.state)==committed and playback.units==result.state.units,"skipping_animation_keeps_committed_damage_and_random_state")
	playback.begin(dead,death.state,death.events,content);playback.tick(1.15)
	verify(playback.opacity_of(StateAccess.find({"units":playback.units},"units","b"))<1.0,"destroyed_unit_fades_after_actual_hit")
	var marcher=StateAccess.clone_transaction(s);marcher.units=marcher.units.filter(func(u):return u.id in ["a","d"]);StateAccess.invalidate_occupancy();VisibilityRules.refresh(marcher,content)
	var move=kernel.resolve(marcher,command(marcher,"Move",{"unit_id":"a","target_hex":{"q":-2,"r":0}}))
	var moved_events=move.events.filter(func(e):return e.type=="UnitMoved")
	verify(move.valid and moved_events.size()==1 and moved_events[0].path[0]=={"q":0,"r":0} and moved_events[0].path[-1]=={"q":-2,"r":0},"movement_events_contain_actual_traversed_path")
	var orientation_view=MapView.new();orientation_view.update_unit_headings(move.state,moved_events)
	var west_heading: Vector2=orientation_view.unit_headings.get("a",Vector2.ZERO)
	var north_orientation=orientation_view.unit_orientation(Vector2(0,-1),"se")
	var east_orientation=orientation_view.unit_orientation(Vector2(1,0),"se")
	verify(west_heading.x<-.8 and west_heading.y<-.2,"completed_move_persists_world_facing_for_idle_unit")
	verify(north_orientation.asset=="se" and east_orientation.asset=="se" and absf(north_orientation.angle-east_orientation.angle)>.9,"cardinal_heading_rotates_immutable_sub2_source_view")
	orientation_view.assets=AssetLibrary.new()
	var directional_unit=StateAccess.find(move.state,"units","a")
	for sample in [[Vector2.UP,"n"],[Vector2.RIGHT,"e"],[Vector2.DOWN,"s"],[Vector2.LEFT,"w"]]:
		var actual=orientation_view.unit_orientation(sample[0],"se",directional_unit)
		verify(actual.asset==sample[1] and actual.angle==0.0,"authored_cardinal_source_remains_upright_"+sample[1])
	var saved_view=MapView.new();saved_view.update_unit_headings(move.state,[])
	verify(saved_view.unit_headings.get("a",Vector2.ZERO).distance_to(west_heading)<.001,"saved_committed_move_log_restores_last_world_heading")
	saved_view.free()
	var untouched=ContentRegistry.fingerprint(result.state)
	orientation_view.update_unit_headings(result.state,result.events)
	verify(orientation_view.unit_headings.get("a",Vector2.ZERO).dot(-orientation_view.unit_headings.get("b",Vector2.ZERO))>.99,"attacker_and_hit_target_face_each_other")
	verify(ContentRegistry.fingerprint(result.state)==untouched,"heading_updates_preserve_rules_and_random_state")
	orientation_view.free()
	playback.begin(marcher,move.state,move.events,content);playback.tick(.16)
	var visual=playback.position_of(StateAccess.find({"units":playback.units},"units","a"))
	verify(visual!=Vector2.ZERO and visual!=HexGrid.to_world(Vector2i(-2,0)),"marching_interpolates_between_hexes_instead_of_teleporting")
	playback.skip();var fast=BattlePlayback.new();fast.speed=2;fast.reduced_motion=true;fast.begin(s,result.state,result.events,content);fast.tick(.55)
	verify(fast.cue_flags.has("hit") and fast.position_of(StateAccess.find({"units":fast.units},"units","a"))==Vector2.ZERO,"double_speed_and_reduced_motion_preserve_hit_timing_without_camera_or_unit_shake")
	var aircraft=StateAccess.clone_transaction(s);var aviation_events: Array=[]
	var airfield={"id":"qa_airfield","owner_id":"zhili","position":{"q":-2,"r":0},"air_sorties_left":3}
	GeneralRules.air(aircraft,airfield,{"q":1,"r":0},true,content,aviation_events)
	playback.begin(s,aircraft,aviation_events,content)
	verify(playback.steps.size()==1 and playback.current.kind=="air" and playback.current.impacts.size()==1,"air_bomb_has_one_flight_and_correlated_impact_without_duplicate_explosions")
	playback.tick(.74)
	verify(StateAccess.find({"units":playback.units},"units","b").hp==StateAccess.find(aircraft,"units","b").hp,"air_damage_is_applied_visually_at_impact")
	var action_assets=AssetLibrary.new();var rifle=StateAccess.find(s,"units","a").duplicate(true);rifle.def_id="rifle";rifle.elite_id=null
	for direction in ["n","e","s","w"]:
		var previous: Texture2D=null
		for pose in ["idle","march_a","march_b","fire","hit"]:
			var texture=action_assets.unit_action_texture(rifle,direction,pose)
			var rect=action_assets.unit_action_rect(rifle,direction,pose,Vector2(88,80))
			verify(texture!=null and rect.has_area() and texture!=previous,"independent_whole_"+direction+"_"+pose+"_source_is_loaded")
			previous=texture
	var vessel=rifle.duplicate(true);vessel.def_id="river_gunboat"
	var sailing=BattlePlayback.new();sailing.active=true;sailing.current={"kind":"move","unit_id":vessel.id,"path":[{"q":0,"r":0},{"q":0,"r":-1}],"duration":.5};sailing.elapsed=.21
	verify(absf(sailing.motion_visual(vessel,content).rotation)<.02,"northbound_ship_source_is_not_rotated_again_by_heading")
	var pose_attack=BattlePlayback.new();pose_attack.begin(s,result.state,result.events,content);pose_attack.elapsed=pose_attack.current.duration*.4
	verify(pose_attack.pose_of(StateAccess.find(s,"units","a"))=="fire","attack_uses_authored_shooting_pose_during_projectile_phase")
	pose_attack.elapsed=pose_attack.current.duration*.74
	verify(pose_attack.pose_of(StateAccess.find(s,"units","b"))=="hit","defender_uses_authored_hit_pose_after_impact")
	var report={"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"checks":checks,"failures":failures,"passed":checks.size()-failures.size(),"failed":failures.size(),"scope":"Synthetic QA arena; actual published scenario replay is separately verified by VisualPlaytest."}
	var file=FileAccess.open("res://reports/combat_presentation_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("COMBAT_PRESENTATION_TESTS ",checks.size()-failures.size()," passed / ",failures.size()," failed");quit(0 if failures.is_empty() else 1)
