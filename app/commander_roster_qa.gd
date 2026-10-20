class_name CommanderRosterQA
extends RefCounted

# Exercises the actual catalogue controls without rewriting scenario state.
# A successful layout run does not certify unfinished portrait production.
var app
var folder=""
var checks: Array=[]
var captures: Array=[]

static func run(application) -> void:
	var qa=CommanderRosterQA.new();qa.app=application;await qa.execute()

func check(value: bool, description: String) -> void:
	checks.append({"name":description,"passed":value})
	if not value:push_error("COMMANDER_ROSTER_QA: "+description)

func settle() -> void:
	for frame in range(6):await app.get_tree().process_frame

func node(id: String) -> Node:
	return app.screen.find_child(id,true,false)

func cards() -> Array:
	return app.war_room.hq_grid.get_children().filter(func(n):return n.has_meta("roster_id"))

func select(id: String, index: int) -> void:
	var control=node(id)
	check(control is OptionButton,"selector_"+id)
	if control is OptionButton:control.select(index);control.item_selected.emit(index);await settle()

func query(text: String) -> void:
	var input=node("HeadquartersSearch")
	check(input is LineEdit,"search_exists_"+text)
	if not input is LineEdit:return
	input.grab_focus();input.text=text;input.text_changed.emit(text);await settle()
	check(is_instance_valid(input) and input==node("HeadquartersSearch") and input.has_focus(),"typing_retains_focus_"+text)

func reset() -> void:
	app.war_room.hq_query="";app.war_room.hq_country="all";app.war_room.hq_level="all";app.war_room.hq_era=0;app.war_room.hq_page=0
	app.war_room.show_headquarters("generals");await settle()

func capture(surface: String) -> void:
	await settle()
	var root=app.overlay if is_instance_valid(app.overlay) else app.screen
	for control in app.ui_nodes(root):
		if control is ScrollContainer:
			for child in control.get_children():
				if child is Container:check(child.size.x<=control.size.x+2,"content_fits_"+surface+"_"+str(control.name))
	var path=folder+"/"+surface+".png"
	check(await app.capture_ui(path,surface),"raw_capture_"+surface)
	captures.append({"surface":surface,"path":path})

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--commander-roster-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/commander_roster_native"
	check(not app.qa_save_path.is_empty(),"isolated_profile")
	if app.qa_save_path.is_empty():app.get_tree().quit(1);return
	var before=ContentRegistry.fingerprint(app.profiles.profile)
	await reset()
	check(app.content.tables.generals.size()>=300,"at_least_300_military_commanders")
	check(cards().size()==CommanderRoster.PAGE_SIZE,"first_page_is_bounded")
	check(node("RosterPrevious").disabled and not node("RosterNext").disabled,"first_page_navigation")
	await capture("commander_catalogue")
	var seen={};var pages=int(ceil(app.content.tables.generals.size()/float(CommanderRoster.PAGE_SIZE)))
	for page in range(pages):
		if page>0:node("RosterNext").pressed.emit();await settle()
		check(cards().size()<=CommanderRoster.PAGE_SIZE,"bounded_page_%d"%page)
		var scroller=app.war_room.hq_grid.get_parent().get_parent()
		check(scroller is ScrollContainer and scroller.scroll_vertical==0,"new_page_starts_at_top_%d"%page)
		for card in cards():
			var id=str(card.get_meta("roster_id"));check(not seen.has(id),"unique_paged_person_"+id);seen[id]=true
			for view in app.ui_nodes(card):
				if view is GeneralPortraitView and view.record.kind=="portrait":check(view.portrait!=null,"registered_portrait_actually_loads_"+id)
	check(seen.size()==app.content.tables.generals.size(),"every_commander_is_browsable")
	check(node("RosterNext").disabled and not node("RosterPrevious").disabled,"last_page_navigation")
	await capture("commander_last_page")
	await reset()
	await select("HeadquartersCountry",2)
	for card in cards():check(CommanderRoster.service(app.content,str(card.get_meta("roster_id"))).country=="Japan","country_filter_"+str(card.get_meta("roster_id")))
	await select("HeadquartersCommandLevel",2)
	await select("HeadquartersLivingYear",7)
	for card in cards():
		var record=CommanderRoster.service(app.content,str(card.get_meta("roster_id")))
		check(CommanderRoster.matches(record,"","Japan","division",1940),"combined_filters_"+str(record.id))
	var count=CommanderRoster.filtered(app.content,"","Japan","division",1940).size()
	check(cards().size()==mini(count,CommanderRoster.PAGE_SIZE),"combined_filter_count")
	await capture("japanese_division_commanders")
	await reset()
	for text in ["洪","洪秀","洪秀全"]:await query(text)
	check(cards().size()==1 and cards()[0].get_meta("roster_id")=="hong_xiuquan","search_preserves_historical_identity")
	await capture("live_name_search")
	await query("不存在的将领查询")
	check(cards().is_empty() and node("RosterPrevious").disabled and node("RosterNext").disabled,"empty_search_navigation")
	await query("")
	check(cards().size()==CommanderRoster.PAGE_SIZE and app.war_room.hq_page==0,"clear_search_returns_first_page")
	check(app.assets.portrait_texture_order.size()<=AssetLibrary.PORTRAIT_TEXTURE_CACHE_LIMIT,"bounded_portrait_texture_memory")
	check(ContentRegistry.fingerprint(app.profiles.profile)==before,"archive_browsing_keeps_profile_unchanged")
	app.start_game("campaign_1924_01","zhili");app.close_overlay();await settle()
	var state=app.match_controller.state
	check(state.generals.filter(func(g):return g.owner_id=="fengtian").size()>int(app.content.scenarios.campaign_1924_01.general_slots),"campaign_roster_is_not_truncated_to_training_budget")
	var unassigned=state.units.filter(func(u):return u.owner_id=="zhili" and u.position!=null and u.general_id==null)
	check(not unassigned.is_empty(),"actual_unassigned_formation_available")
	var unit=unassigned[0] if not unassigned.is_empty() else state.units[0]
	app.show_generals(unit.id);await settle()
	var available=state.generals.filter(func(g):return g.owner_id=="zhili" and g.assigned_unit_id==null and not g.get("injured_this_match",false) and not g.get("withdrawn_this_match",false))
	var views=app.ui_nodes(app.overlay).filter(func(n):return n is GeneralPortraitView)
	check(views.size()==available.size(),"appointment_shows_only_own_unassigned_reserves")
	for view in views:check(available.any(func(g):return g.id==view.record.general_id),"appointment_identity_"+str(view.record.general_id))
	await capture("scenario_reserve_appointment")
	var buttons=app.ui_nodes(app.overlay).filter(func(n):return n is Button and n.has_meta("commander_id") and not n.disabled)
	check(not buttons.is_empty(),"reserve_has_enabled_appointment_control")
	if not buttons.is_empty():
		var selected=str(buttons[0].get_meta("commander_id"));var before_version=int(state.state_version)
		buttons[0].pressed.emit()
		var started=Time.get_ticks_msec()
		while Time.get_ticks_msec()-started<30000 and (app.match_controller.command_busy or int(app.match_controller.state.state_version)==before_version):await app.get_tree().process_frame
		var after=app.match_controller.state;var updated=StateAccess.find(after,"units",str(unit.id));var officer=StateAccess.find(after,"generals",selected)
		check(updated.get("general_id")==selected and officer.get("assigned_unit_id")==unit.id,"actual_reserve_appointment_updates_both_records")
		check(updated.get("general_assignment_lock",false) and not updated.get("attack_ready",true),"actual_appointment_consumes_attack_opportunity")
		await capture("reserve_appointed")
	app.close_overlay()
	var installed=0
	for id in app.assets.general_portraits.records:
		var person=app.assets.general_portraits.records[id]
		var available_stages={}
		for variant in person.get("variants",[]):
			if not str(variant.get("asset_id","")).is_empty():available_stages[str(variant.age_stage)]=true
		if ["young","prime","middle","late"].all(func(stage):return available_stages.has(stage)):installed+=1
	var report={"version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"passed":checks.all(func(c):return c.passed),"checks":checks,"captures":captures,"military_commanders":app.content.tables.generals.size(),"people_with_four_registered_portraits":installed,"all_portraits_complete":installed>=app.content.tables.generals.size()+4,"formal_art_approval":false,"qa_save_isolated":true,"physical_android_device_tested":OS.has_feature("android"),"raw_godot_captures":true,"viewport":app.get_viewport_rect().size,"ui_scale":app.settings.ui_scale}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("COMMANDER_ROSTER_QA ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"captures":captures.size(),"all_portraits_complete":report.all_portraits_complete}));app.get_tree().quit(0 if report.passed else 1)
