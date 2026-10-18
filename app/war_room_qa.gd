class_name WarRoomQA
extends RefCounted

# Native Windows UI evidence. Uses an isolated save profile and actual controls;
# no scenario state or image is synthesized for the screenshots.
var checks: Array=[]
var captures: Array=[]
var app
var folder=""

static func run(application) -> void:
	var qa=WarRoomQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String, detail: Variant=null) -> void:
	checks.append({"name":name,"passed":value,"detail":detail})
	if not value:push_error("WAR_ROOM_QA: "+name)

func settle() -> void:
	for i in range(5):await app.get_tree().process_frame

func capture(name: String) -> void:
	await settle()
	var path=folder+"/"+name+".png"
	check(await app.capture_ui(path,name),"native_capture_"+name)
	var row={"surface":name,"path":path}
	if is_instance_valid(app.war_room.atlas) and app.screen.find_child("WarRoomAtlas",true,false)!=null:
		row["atlas_preview"]=app.war_room.atlas.capture_facts()
	captures.append(row)
	layout_checks(name)

func find_button(parent: Node, prefix: String) -> Button:
	for node in app.ui_nodes(parent):
		if node is Button and node.text.begins_with(prefix):return node
	return null

func layout_checks(surface: String) -> void:
	var root=app.overlay if is_instance_valid(app.overlay) else app.screen
	var viewport=app.get_viewport_rect();var horizontal_overflow: Array=[]
	for node in app.ui_nodes(root):
		if node is ScrollContainer and node.is_visible_in_tree():
			for child in node.get_children():
				if child is Container and child.size.x>node.size.x+2:horizontal_overflow.append({"width":child.size.x,"available":node.size.x})
	check(horizontal_overflow.is_empty(),surface+"_scroll_content_fits_width",horizontal_overflow)
	for name in ["LaunchScenario","EraSelector","DifficultySelector","FactionSelector","AtlasZoomIn","AtlasZoomOut","AtlasFit"]:
		var control=root.find_child(name,true,false)
		if not is_instance_valid(control):continue
		check(viewport.encloses(control.get_global_rect()),surface+"_"+name+"_inside_viewport")
		if app.mobile_layout():check(control.size.y>=95,surface+"_"+name+"_touch_height")
	var date=root.find_child("ScenarioDate",true,false)
	if is_instance_valid(date):
		check(date.size.x>=date.get_minimum_size().x and date.get_line_count()==1,surface+"_date_stays_on_one_line")
		check(app.war_room.atlas.size.y>=app.get_viewport_rect().size.y*.40,surface+"_atlas_retains_useful_height",app.war_room.atlas.size.y)
		var chosen: Button=app.war_room.browser_buttons.get(app.war_room.browser_id)
		var scroll: ScrollContainer=app.war_room.browser_list.get_parent()
		check(is_instance_valid(chosen) and scroll.get_global_rect().grow(2).encloses(chosen.get_global_rect()),surface+"_selected_scenario_card_is_visible")
	if is_instance_valid(app.overlay):
		var close=find_button(root,"关闭")
		check(is_instance_valid(close) and viewport.encloses(close.get_global_rect()),surface+"_close_reachable")
		if app.mobile_layout():check(is_instance_valid(close) and close.size.y>=95,surface+"_close_touch_height")

func wait_previews(parent: Node) -> void:
	for frame in range(900):
		var pending=false
		for node in app.ui_nodes(parent):
			if node is Button and node.tooltip_text=="正在核对命令条件":pending=true;break
		if not pending:return
		await app.get_tree().process_frame
	check(false,"command_preview_completed_before_timeout")

func wait_command() -> void:
	for frame in range(1800):
		if not app.match_controller.command_busy and not app.match_controller.presentation_busy:return
		await app.get_tree().process_frame
	check(false,"command_completed_before_timeout")

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--war-room-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/war_room_native"
	await capture("home")
	var before_profile=ContentRegistry.fingerprint(app.profiles.profile)
	app.show_scenario_browser("campaign");await settle()
	app.war_room.select_recipe("campaign_1920_02");await settle()
	check(app.screen.find_child("LaunchScenario",true,false).disabled,"locked_campaign_cannot_launch")
	app.war_room.select_recipe("campaign_1920_01");await capture("campaign")
	var atlas:WarRoomAtlas=app.war_room.atlas
	check(atlas.landscape.material!=null and atlas.landscape.terrain_surface_variant_draw_count>0,"scenario_preview_renders_shipping_ground_material")
	check(atlas.landscape.relief.mesh!=null,"scenario_preview_renders_source_relief")
	check(atlas.landscape.terrain_scenery_draw_count>0,"scenario_preview_renders_whole_scenery_originals")
	check(atlas.settlement_originals_drawn>0,"scenario_preview_renders_whole_settlement_originals")
	check(atlas.source_map.is_read_only(),"scenario_preview_keeps_source_map_immutable")
	var fit_scale=atlas.scale_factor;var map_revision=atlas.map_revision
	for i in range(4):app.screen.find_child("AtlasZoomIn",true,false).pressed.emit()
	await settle();check(atlas.scale_factor>fit_scale*2 and atlas.map_revision==map_revision,"atlas_zoom_changes_camera_without_rebuilding_source_map")
	var before_pan=atlas.view_center
	var press=InputEventMouseButton.new();press.button_index=MOUSE_BUTTON_LEFT;press.pressed=true;press.position=atlas.size*.5;atlas._gui_input(press)
	var motion=InputEventMouseMotion.new();motion.position=press.position+Vector2(80,35);motion.relative=Vector2(80,35);atlas._gui_input(motion)
	press.pressed=false;press.position=motion.position;atlas._gui_input(press)
	check(atlas.view_center.distance_to(before_pan)>1 and app.war_room.browser_id=="campaign_1920_01","atlas_drag_pans_without_selecting_another_scenario")
	await capture("campaign_detail")
	app.screen.find_child("AtlasFit",true,false).pressed.emit();await settle()
	check(is_equal_approx(atlas.view_multiplier,1.0) and atlas.view_center.is_equal_approx(atlas.framing_bounds().get_center()),"atlas_fit_restores_geographic_framing")
	app.show_scenario_browser("conquest");app.war_room.select_recipe("asia_1927");await settle()
	var era:OptionButton=app.screen.find_child("EraSelector",true,false)
	for i in range(era.item_count):
		if era.get_item_text(i)=="1927 年":era.select(i);era.item_selected.emit(i);break
	check(app.war_room.browser_buttons.keys()==["asia_1927"],"era_filter_selects_actual_1927_scenario")
	check(app.war_room.atlas.source_map.id=="asia_strategic","conquest_preview_uses_real_asia_map")
	var old_owner=app.war_room.browser_owner;var clicked=""
	for pin in app.war_room.atlas.pin_rects:
		if pin.owner!=old_owner:
			clicked=pin.owner;var touch=InputEventScreenTouch.new();touch.pressed=true;touch.position=pin.rect.get_center();app.war_room.atlas._gui_input(touch);touch.pressed=false;app.war_room.atlas._gui_input(touch);break
	await settle();check(not clicked.is_empty() and app.war_room.browser_owner==clicked,"map_city_touch_changes_playable_faction")
	await capture("conquest")
	app.show_scenario_browser("legion");await capture("legion")
	check(app.match_controller.state.is_empty() and ContentRegistry.fingerprint(app.profiles.profile)==before_profile,"preview_navigation_does_not_create_match_or_mutate_profile")
	app.show_scenario_browser("campaign");app.war_room.select_recipe("campaign_1920_01");await settle()
	var launch:Button=app.screen.find_child("LaunchScenario",true,false)
	check(not launch.disabled,"unlocked_campaign_can_launch");launch.pressed.emit();app.close_overlay();await settle()
	check(app.match_controller.state.scenario_id=="campaign_1920_01","launch_button_starts_selected_scenario")
	var state=app.match_controller.state;var owner=state.player_faction_id;var city=state.cities.filter(func(c):return c.owner_id==owner and EconomyRules.building_level(c,"barracks")>0)[0]
	var own=state.units.filter(func(u):return u.owner_id==owner and u.position!=null)
	var visible=0
	for unit in own:
		if app.map_view.map_hud_area().grow(-20).has_point(app.map_view.world_to_screen(HexGrid.to_world(HexGrid.coordinate(unit.position)))):visible+=1
	check(visible>=ceili(own.size()*.7),"opening_army_visible_between_hud_panels",{"visible":visible,"own_units":own.size(),"playfield":app.map_view.map_hud_area()})
	await capture("opening_army")
	app.show_recruit(city.id);await wait_previews(app.overlay)
	var rifle_card:Node
	for node in app.ui_nodes(app.overlay):
		if node.get_meta("recruit_unit","")=="rifle":rifle_card=node;break
	check(is_instance_valid(rifle_card),"rifle_card_present")
	if is_instance_valid(rifle_card):
		var selector:OptionButton=rifle_card.find_child("RecruitStack",true,false)
		selector.select(1);selector.item_selected.emit(1);selector.select(2);selector.item_selected.emit(2);await wait_previews(rifle_card)
		var recruit=find_button(rifle_card,"征募 · 3 层")
		check(is_instance_valid(recruit) and not recruit.disabled,"rapid_stack_change_validates_latest_three_layer_offer")
		var cash_before=StateAccess.faction(app.match_controller.state,owner).resources.cash
		var expected_cost=EconomyRules.recruit_cost(app.match_controller.state,owner,"rifle",3,null,app.content)
		if is_instance_valid(recruit) and not recruit.disabled:
			recruit.pressed.emit();await wait_command();await settle()
			var updated=StateAccess.find(app.match_controller.state,"cities",city.id)
			check(updated.recruit_queue.any(func(q):return q.target_def_id=="rifle" and q.stack==3),"three_layer_offer_submits_actual_recruit_command")
			check(StateAccess.faction(app.match_controller.state,owner).resources.cash==cash_before-expected_cost.cash,"displayed_recruit_cost_matches_actual_resource_payment")
	app.show_recruit(city.id);await wait_previews(app.overlay);await capture("recruit")
	app.show_buildings(city.id);await wait_previews(app.overlay);await capture("buildings")
	app.show_diplomacy();await wait_previews(app.overlay);await capture("diplomacy")
	var explanations=app.ui_nodes(app.overlay).filter(func(n):return n is Button and n.disabled and n.has_meta("validation_label") and is_instance_valid(n.get_meta("validation_label")) and not n.get_meta("validation_label").text.is_empty())
	check(not explanations.is_empty(),"unavailable_diplomatic_actions_have_visible_reasons")
	diplomacy_checks("single_counterparty")
	app.show_generals(own[0].id);await wait_previews(app.overlay);await capture("assign_general");app.close_overlay()
	var frozen=ContentRegistry.fingerprint(StateAccess.faction(app.match_controller.state,owner).profile_snapshot)
	app.show_headquarters();await capture("headquarters")
	app.war_room.show_headquarters("technology","infantry");await capture("technology")
	var research_before=app.profiles.profile.research;var research=find_button(app.screen,"研究 · 30 研究点")
	check(is_instance_valid(research) and not research.disabled,"first_technology_has_actionable_research_button")
	if is_instance_valid(research) and not research.disabled:
		research.pressed.emit();await settle()
		check(app.profiles.profile.research==research_before-30 and int(app.profiles.profile.tech_ranks.get("rifle_drill",0))==1,"research_button_pays_and_persists_real_rank")
		check(ContentRegistry.fingerprint(StateAccess.faction(app.match_controller.state,owner).profile_snapshot)==frozen,"headquarters_research_does_not_change_live_match_snapshot")
	app.war_room.show_headquarters("technology","staff");await capture("staff_research")
	check(app.ui_nodes(app.screen).any(func(n):return n is Label and n.text=="电报协同"),"seventh_staff_research_branch_accessible")
	app.show_legion_deployment("legion_12");await capture("legion_deployment");app.close_overlay()
	app.start_game("conq_1924","zhili");app.close_overlay();await settle()
	app.show_diplomacy();await wait_previews(app.overlay);await settle()
	var targets=app.ui_nodes(app.overlay).filter(func(n):return n is Button and n.has_meta("target_faction_id"))
	check(targets.size()>1,"multi_faction_office_has_real_counterparty_roster")
	var stable_targets=targets.filter(func(n):return str(n.get_meta("target_faction_id"))!=app.war_room.diplomacy_target and app.match_controller.state.cities.any(func(c):return c.owner_id==str(n.get_meta("target_faction_id")) and (c.level>=2 or c.get("command_center",false))))
	check(not stable_targets.is_empty(),"multi_faction_aid_fixture_has_another_strategic_base")
	if not stable_targets.is_empty():
		var selected_id=str(stable_targets[stable_targets.size()-1].get_meta("target_faction_id"))
		stable_targets[stable_targets.size()-1].pressed.emit();await wait_previews(app.overlay);await settle()
		check(app.war_room.diplomacy_target==selected_id,"roster_button_selects_its_named_counterparty")
	diplomacy_checks("multiple_counterparties");await capture("multi_diplomacy")
	var target=app.war_room.diplomacy_target
	var aid:Button=app.overlay.find_child("DiplomacyAction_aid",true,false)
	check(is_instance_valid(aid) and not aid.disabled,"selected_counterparty_aid_offer_is_actionable")
	var cash_before_aid=int(StateAccess.faction(app.match_controller.state,"zhili").resources.cash)
	if is_instance_valid(aid) and not aid.disabled:
		aid.pressed.emit();await wait_command();await settle()
		var after_aid=app.match_controller.state
		check(int(StateAccess.faction(after_aid,"zhili").resources.cash)==cash_before_aid-50,"office_aid_button_pays_exactly_fifty_once",{"before":cash_before_aid,"after":StateAccess.faction(after_aid,"zhili").resources.cash,"target":target,"events":after_aid.event_log.slice(maxi(0,after_aid.event_log.size()-6))})
		check(after_aid.pending_aid.any(func(a):return a.sender_id=="zhili" and a.receiver_id==target and int(a.resources.get("cash",0))==50),"office_aid_uses_selected_real_counterparty",{"target":target,"pending":after_aid.pending_aid})
		app.war_room.show_diplomacy(target);await wait_previews(app.overlay);await settle()
		check(app.overlay.find_child("DiplomacyAction_aid",true,false).disabled,"aid_cooldown_disables_repeat_offer")
		check(app.overlay.find_child("DiplomacyAidTransit",true,false)!=null,"pending_aid_is_visible_in_selected_office")
		await capture("aid_pending")
	var report={"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"passed":checks.all(func(c):return c.passed),"checks":checks,"captures":captures,"viewport":app.get_viewport_rect().size,"ui_scale":app.settings.ui_scale,"qa_save_isolated":not app.qa_save_path.is_empty(),"physical_android_device_tested":OS.has_feature("android"),"raw_godot_captures":true}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("WAR_ROOM_QA ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"captures":captures.size()}))
	app.get_tree().quit(0 if report.passed else 1)

func diplomacy_checks(prefix: String) -> void:
	var roster=app.overlay.find_child("DiplomacyRoster",true,false)
	var detail=app.overlay.find_child("DiplomacyDetails",true,false)
	check(is_instance_valid(roster) and is_instance_valid(detail) and detail.size.x>roster.size.x*1.5,prefix+"_selected_office_uses_available_width")
	var state=app.match_controller.state;var target=app.war_room.diplomacy_target
	var expected=state.units.filter(func(u):return u.owner_id==target and VisibilityRules.unit_visible(state,state.player_faction_id,u)).size()
	var known=app.overlay.find_child("DiplomacyKnownUnits",true,false)
	check(is_instance_valid(known) and known.text=="已侦知编队 %d"%expected,prefix+"_army_display_respects_current_intelligence")
	var identity=app.overlay.find_child("DiplomacySelectedName",true,false)
	check(is_instance_valid(identity) and identity.text==StateAccess.faction_name(state,target,app.content),prefix+"_details_follow_selected_faction")
