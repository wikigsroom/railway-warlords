class_name GeneralPortraitQA
extends RefCounted

# Native UI traversal only. Published deployments and rules are never patched.
var app
var folder=""
var checks: Array=[]
var captures: Array=[]

static func run(application) -> void:
	var qa=GeneralPortraitQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:push_error("PORTRAIT_QA: "+name)

func settle() -> void:
	for i in range(5):await app.get_tree().process_frame

func portraits(parent: Node) -> Array:
	return app.ui_nodes(parent).filter(func(node):return node is GeneralPortraitView)

func reveal(view: Control) -> void:
	var ancestor=view.get_parent()
	var card: Control=view
	while is_instance_valid(ancestor):
		if ancestor is PanelContainer:card=ancestor
		if ancestor is ScrollContainer:
			ancestor.ensure_control_visible(card if card.size.y<ancestor.size.y else view);await settle()
			check(ancestor.get_global_rect().grow(2).encloses(view.get_global_rect()),"scroll_reveals_"+view.name)
			return
		ancestor=ancestor.get_parent()

func capture(surface: String) -> void:
	await settle()
	var path=folder+"/"+surface+".png"
	check(await app.capture_ui(path,surface),"capture_"+surface)
	var root=app.overlay if is_instance_valid(app.overlay) else app.screen
	var visible=[]
	for view in portraits(root):
		if app.get_viewport_rect().encloses(view.get_global_rect()):visible.append(view.record)
	var overflow=false
	for node in app.ui_nodes(root):
		if node is ScrollContainer:
			for child in node.get_children():
				if child is Container and child.size.x>node.size.x+2:overflow=true
	check(not overflow,"content_fits_width_"+surface)
	captures.append({"surface":surface,"path":path,"visible_portraits":visible})

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--general-portrait-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/general_portraits_native"
	var profile_before=ContentRegistry.fingerprint(app.profiles.profile)
	app.war_room.show_headquarters("generals");await settle()
	var stages=["young","prime","middle","late"]
	for stage_index in range(stages.size()):
		var selector=app.screen.find_child("HeadquartersAgeStage",true,false)
		check(selector is OptionButton,"headquarters_has_age_selector")
		selector.select(stage_index);selector.item_selected.emit(stage_index);await settle()
		var seen={};var pages=int(ceil(app.content.tables.generals.size()/float(CommanderRoster.PAGE_SIZE)))
		for page in range(pages):
			if page>0:
				var next=app.screen.find_child("RosterNext",true,false)
				check(next is Button and not next.disabled,"next_roster_page_available_%s_%d"%[stages[stage_index],page])
				next.pressed.emit();await settle()
			var views=portraits(app.screen)
			check(views.size()==mini(CommanderRoster.PAGE_SIZE,app.content.tables.generals.size()-page*CommanderRoster.PAGE_SIZE),"bounded_roster_page_%s_%d"%[stages[stage_index],page])
			for i in range(views.size()):
				var view=views[i];await reveal(view)
				check(view.record.kind=="portrait" and view.portrait!=null and view.record.age_stage==stages[stage_index],"whole_age_portrait_"+str(view.record.general_id)+"_"+stages[stage_index])
				check(not seen.has(str(view.record.general_id)),"no_duplicate_roster_person_%s_%s"%[stages[stage_index],str(view.record.general_id)]);seen[str(view.record.general_id)]=true
				if page in [0,int(pages/2),pages-1] and i==0:await capture("roster_%s_page_%02d"%[stages[stage_index],page])
		check(seen.size()==app.content.tables.generals.size(),"every_registered_general_traversed_"+stages[stage_index])
		check(app.assets.portrait_texture_order.size()<=AssetLibrary.PORTRAIT_TEXTURE_CACHE_LIMIT,"portrait_cache_bounded_"+stages[stage_index])
		app.war_room.hq_page=0
	for id in ["li_hongzhang","hong_xiuquan","mao_zedong"]:
		app.show_general_growth(id);await settle()
		for stage_index in range(stages.size()):
			var selector=app.overlay.find_child("GeneralAgeStage",true,false)
			check(selector is OptionButton,"growth_has_age_selector_"+id)
			selector.select(stage_index);selector.item_selected.emit(stage_index);await settle()
			var growth=portraits(app.overlay)
			check(growth.size()==1 and growth[0].record.general_id==id and growth[0].record.age_stage==stages[stage_index],"growth_age_identity_"+id+"_"+stages[stage_index])
			await capture("growth_"+id+"_"+stages[stage_index])
		app.close_overlay()
	app.war_room.show_headquarters("political");await settle()
	for stage_index in range(stages.size()):
		var selector=app.screen.find_child("PoliticalPortraitAgeStage",true,false)
		check(selector is OptionButton,"political_archive_has_age_selector")
		selector.select(stage_index+1);selector.item_selected.emit(stage_index+1);await settle()
		var views=portraits(app.screen)
		check(views.size()==17,"political_archive_covers_all_registered_figures_"+stages[stage_index])
		for view in views:
			await reveal(view)
			check(view.record.kind=="portrait" and view.portrait!=null and view.record.age_stage==stages[stage_index],"political_age_portrait_"+str(view.record.general_id)+"_"+stages[stage_index])
			if view.record.general_id in ["daoguang","xianfeng","ito_hirobumi","nicholas_ii"]:await capture("political_"+str(view.record.general_id)+"_"+stages[stage_index])
	check(ContentRegistry.fingerprint(app.profiles.profile)==profile_before,"portrait_browsing_does_not_change_profile")
	for id in ["campaign_1840_01","campaign_1860_01","campaign_1890_01","campaign_1900_01","campaign_1917_01","campaign_1927_01","campaign_1940_01","asia_1917","asia_1940"]:
		app.start_game(id,app.content.scenarios[id].player_default);app.close_overlay();await settle()
		var state=app.match_controller.state;var frozen=ContentRegistry.fingerprint(state)
		var units=state.units.filter(func(u):return u.owner_id==state.player_faction_id and u.position!=null)
		check(not units.is_empty(),"actual_player_unit_"+id)
		if units.is_empty():continue
		app.show_generals(units[0].id);await settle()
		var dated=portraits(app.overlay);var valid=true
		for view in dated:
			valid=valid and (view.record.kind=="identity" or view.record.reference_year<=int(str(state.date).left(4)) or view.record.age_stage=="young")
		var available=state.generals.filter(func(g):return g.owner_id==state.player_faction_id and not g.get("injured_this_match",false) and not g.get("withdrawn_this_match",false) and g.assigned_unit_id==null)
		check(dated.size()==available.size() and valid,"assignment_uses_own_available_reserves_and_scenario_date_"+id)
		if dated.is_empty():check(is_instance_valid(app.overlay.find_child("NoScenarioGenerals",true,false)),"empty_roster_explained_"+id)
		await capture("assignment_"+id);app.close_overlay()
		var assigned=units.filter(func(u):return u.general_id!=null)
		if not assigned.is_empty():
			var unit=assigned[0];app.on_hex_selected(HexGrid.coordinate(unit.position));await settle()
			var inspector=portraits(app.inspector)
			check(inspector.size()==1 and inspector[0].record.general_id==unit.general_id,"unit_inspector_matches_assigned_general_"+id)
			await capture("inspector_"+id)
		check(ContentRegistry.fingerprint(state)==frozen,"presentation_keeps_actual_state_"+id)
	app.war_room.political_portrait_stage=""
	app.war_room.show_headquarters("political");await settle()
	var dated_figures=portraits(app.screen);var current_date=str(app.match_controller.state.date)
	for view in dated_figures:
		var expected=app.assets.general_portraits.resolve(str(view.record.general_id),current_date)
		check(view.record==expected,"political_archive_uses_current_match_date_"+str(view.record.general_id))
	await capture("political_current_match_date")
	var report={"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"passed":checks.all(func(c):return c.passed),"checks":checks,"captures":captures,"viewport":app.get_viewport_rect().size,"ui_scale":app.settings.ui_scale,"qa_save_isolated":not app.qa_save_path.is_empty(),"physical_android_device_tested":OS.has_feature("android"),"raw_godot_captures":true,"formal_art_approval":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GENERAL_PORTRAIT_QA ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"captures":captures.size()}));app.get_tree().quit(0 if report.passed else 1)
