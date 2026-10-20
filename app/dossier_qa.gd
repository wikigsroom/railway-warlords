class_name DossierQA
extends RefCounted

# Real controls against a fresh isolated profile, with no invented match state.
var app
var folder=""
var checks: Array=[]
var captures: Array=[]

static func run(application) -> void:
	var qa=DossierQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:push_error("DOSSIER_QA: "+name)

func settle() -> void:
	for frame in range(6):await app.get_tree().process_frame

func control(name: String) -> Node:
	return (app.overlay if is_instance_valid(app.overlay) else app.screen).find_child(name,true,false)

func reveal(node: Control) -> void:
	if not is_instance_valid(node):return
	var ancestor=node.get_parent()
	while is_instance_valid(ancestor):
		if ancestor is ScrollContainer:
			ancestor.ensure_control_visible(node);await settle()
			check(ancestor.get_global_rect().grow(2).encloses(node.get_global_rect()),"action_revealed_"+node.name)
			return
		ancestor=ancestor.get_parent()

func capture(surface: String) -> void:
	await settle()
	var root=app.overlay if is_instance_valid(app.overlay) else app.screen
	var fits=true
	for node in app.ui_nodes(root):
		if node is ScrollContainer:
			for child in node.get_children():
				if child is Container and child.size.x>node.size.x+2:fits=false
	check(fits,"horizontal_content_fits_"+surface)
	var path=folder+"/"+surface+".png"
	check(await app.capture_ui(path,surface),"raw_native_capture_"+surface)
	captures.append({"surface":surface,"path":path})

func press(name: String) -> void:
	var b=control(name)
	check(b is Button and not b.disabled,"available_real_action_"+name)
	if b is Button and not b.disabled:
		await reveal(b);b.pressed.emit();await settle()

func select(name: String, index: int) -> void:
	var selector=control(name)
	check(selector is OptionButton,"selector_exists_"+name)
	if selector is OptionButton:selector.select(index);selector.item_selected.emit(index);await settle()

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--dossier-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/dossier_native"
	check(not app.qa_save_path.is_empty(),"profile_isolated_from_user")
	if app.qa_save_path.is_empty():app.get_tree().quit(1);return
	var before=app.profiles.profile.duplicate(true)
	GeneralDossier.medal_choices.clear()
	app.war_room.hq_query="";app.war_room.show_headquarters("generals");await settle()
	await capture("headquarters")
	var search=control("HeadquartersSearch")
	check(search is LineEdit,"roster_has_live_search")
	if search is LineEdit:
		search.text="洪秀全";search.text_changed.emit(search.text);await settle()
		var visible=app.ui_nodes(app.screen).filter(func(n):return n is GeneralPortraitView and n.is_visible_in_tree())
		check(visible.size()==1 and visible[0].record.general_id=="hong_xiuquan","search_keeps_exact_historical_identity")
		await capture("roster_search_hong")
		search.text="";search.text_changed.emit("");await settle()
		check(app.ui_nodes(app.screen).filter(func(n):return n is GeneralPortraitView and n.is_visible_in_tree()).size()==mini(CommanderRoster.PAGE_SIZE,app.content.tables.generals.size()),"clearing_search_restores_bounded_first_page")
	app.show_general_growth("hong_xiuquan","young");await settle()
	var views=app.ui_nodes(app.overlay).filter(func(n):return n is GeneralPortraitView)
	check(views.size()==1 and views[0].size.x>=260,"dossier_uses_large_whole_portrait")
	check(views.size()==1 and app.get_viewport_rect().encloses(views[0].get_global_rect()),"whole_portrait_inside_actual_viewport")
	var close=app.ui_nodes(app.overlay).filter(func(n):return n is Button and n.text=="关闭")
	check(close.size()==1 and app.get_viewport_rect().encloses(close[0].get_global_rect()),"fixed_close_remains_inside_viewport")
	if app.mobile_layout():check(close.size()==1 and close[0].size.y>=95 and control("GeneralAgeStage").size.y>=95,"close_and_age_selector_keep_mobile_touch_height")
	var promotion=control("PromoteGeneral_hong_xiuquan")
	check(control("DossierEraLabel").get_line_count()==1,"era_caption_does_not_wrap_vertically")
	var ability_labels=app.ui_nodes(app.overlay).filter(func(n):return n is Label and n.get_meta("dossier_ability_caption",false))
	check(ability_labels.size()==6 and ability_labels.all(func(n):return n.get_line_count()==1),"all_six_ability_captions_are_readable_on_one_line")
	check(promotion is Button and promotion.disabled,"promotion_disabled_until_real_xp_requirement")
	var upgrade=control("UpgradeSkill_staff_morale")
	check(upgrade is Button and upgrade.disabled,"skill_disabled_until_real_xp_requirement")
	await capture("dossier_hong_young")
	await select("GeneralAgeStage",2)
	await capture("dossier_hong_middle")
	check(ContentRegistry.fingerprint(before)==ContentRegistry.fingerprint(app.profiles.profile),"search_and_age_preview_never_spend_profile_resources")
	await select("GeneralAgeStage",0)
	await select("MedalRank_marksmanship",2)
	var unaffordable=control("EquipMedal_marksmanship")
	check(unaffordable is Button and unaffordable.disabled and unaffordable.tooltip_text.contains("功勋不足"),"unaffordable_medal_explains_real_shortage")
	await reveal(unaffordable)
	await capture("unaffordable_medal")
	await select("MedalRank_marksmanship",0)
	var first_cost=int(app.content.definition("medals","marksmanship").cost_merit[0])
	await press("EquipMedal_marksmanship")
	check(app.profiles.profile.merit==int(before.merit)-first_cost,"medal_charges_registered_price_once")
	check(control("GeneralAgeStage").selected==0,"successful_growth_keeps_selected_young_stage")
	check(is_instance_valid(control("UnequipMedal_marksmanship")) and not is_instance_valid(control("EquipMedal_marksmanship")),"duplicate_medal_not_offered")
	await reveal(control("UnequipMedal_marksmanship"))
	await capture("medal_equipped")
	await press("EquipMedal_steadfast")
	var third=control("EquipMedal_logistics_medal")
	check(third is Button and third.disabled and third.tooltip_text.contains("槽已满"),"third_medal_disabled_with_two_real_slots_full")
	await reveal(third)
	var sticky=app.ui_nodes(app.overlay).filter(func(n):return n is GeneralPortraitView)
	check(sticky.size()==1 and app.get_viewport_rect().encloses(sticky[0].get_global_rect()),"medal_scroll_keeps_whole_portrait_visible")
	await capture("medal_slots_full")
	var paid=int(app.profiles.profile.merit)
	await press("UnequipMedal_steadfast")
	check(app.profiles.profile.merit==paid,"unequip_preserves_existing_no_refund_rule")
	check(app.profiles.profile.medals.filter(func(m):return m.general_id=="hong_xiuquan").size()==1,"unequip_updates_actual_profile")
	await reveal(control("EquipMedal_steadfast"))
	await capture("medal_removed")
	check(app.profiles.commit(before),"restore_isolated_profile_after_real_action_checks")
	check(ContentRegistry.fingerprint(before)==ContentRegistry.fingerprint(app.profiles.profile),"isolated_profile_restored_exactly")
	GeneralDossier.medal_choices.clear();app.war_room.hq_query=""
	var report={"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"passed":checks.all(func(c):return c.passed),"checks":checks,"captures":captures,"viewport":app.get_viewport_rect().size,"ui_scale":app.settings.ui_scale,"physical_android_device_tested":OS.has_feature("android"),"raw_godot_captures":true,"isolated_profile_restored":ContentRegistry.fingerprint(before)==ContentRegistry.fingerprint(app.profiles.profile)}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("DOSSIER_QA ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"captures":captures.size()}))
	app.get_tree().quit(0 if report.passed else 1)
