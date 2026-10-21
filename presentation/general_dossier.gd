class_name GeneralDossier
extends RefCounted

# UI-only preferences; all payments and loadout changes use ProfileRepository.
static var medal_choices: Dictionary={}
const FAMILIES={"infantry":"步兵","artillery":"炮兵","cavalry":"骑兵","navy":"海军","aviation":"航空","logistics":"后勤"}

static func show(app, id: String, age_stage: String="middle") -> void:
	var d=app.content.definition("generals",id)
	var profile=app.profiles.profile
	var rank=int(profile.general_ranks.get(id,0))
	var root=app.modal(d.name+" · 将领档案",false)
	root.name="GeneralDossier"
	var tools=app.row(root)
	var era_label=app.label(tools,"肖像年代",17,MilitaryUI.MUTED)
	era_label.name="DossierEraLabel";era_label.size_flags_horizontal=Control.SIZE_SHRINK_BEGIN
	era_label.autowrap_mode=TextServer.AUTOWRAP_OFF
	var stages=app.assets.general_portraits.records.get(id,{}).get("stages",[])
	var selector=OptionButton.new();selector.name="GeneralAgeStage"
	selector.custom_minimum_size=Vector2(270,maxf(58,app.war_room.touch_height()))
	selector.size_flags_horizontal=Control.SIZE_EXPAND_FILL;selector.clip_text=true
	var selected=0
	for index in stages.size():
		var stage=stages[index]
		selector.add_item("%s · %d年"%[stage.label,stage.reference_year])
		if stage.id==age_stage:selected=index
	tools.add_child(selector);selector.select(selected)
	selector.item_selected.connect(func(index):show(app,id,str(stages[index].id)))
	var layout=HBoxContainer.new();layout.name="DossierColumns"
	layout.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	layout.size_flags_vertical=Control.SIZE_EXPAND_FILL
	layout.add_theme_constant_override("separation",22)
	root.add_child(layout)
	var identity_scroll=preload("res://presentation/touch_scroll.gd").new();identity_scroll.name="DossierIdentityScroll"
	identity_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	identity_scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL
	identity_scroll.custom_minimum_size.x=286*minf(float(app.settings.ui_scale),1.12)+44
	layout.add_child(identity_scroll)
	var identity=app.ui_panel(identity_scroll,"ui_steel_panel",Color.WHITE,18)
	identity.name="DossierIdentity";identity.set_meta("ui_light",false)
	identity.size_flags_horizontal=Control.SIZE_SHRINK_BEGIN
	identity.size_flags_vertical=Control.SIZE_SHRINK_BEGIN
	var left=app.column(identity)
	var portrait=GeneralPortraitView.new()
	portrait.setup(app.assets,id,Vector2(286,296)*minf(float(app.settings.ui_scale),1.12),"",age_stage)
	left.add_child(portrait)
	app.label(left,d.name,32,MilitaryUI.PALE)
	app.label(left,str(portrait.record.caption),18,Color("ccd2c6"))
	app.label(left,str(portrait.record.get("reference_caption","")),16,Color("c1cbbf"))
	app.ui_rule(left,Color("738582"))
	var life=app.assets.general_portraits.records.get(id,{})
	app.label(left,"%d — %d"%[life.get("birth_year",0),life.get("death_year",0)],20,MilitaryUI.BRASS)
	var service=CommanderRoster.service(app.content,id)
	app.label(left,CommanderRoster.grade(service),17,MilitaryUI.BRASS)
	if not str(service.get("documented_title","")).is_empty():app.label(left,str(service.documented_title),17,MilitaryUI.PALE)
	app.label(left,"成长等级  %d / %d"%[rank,d.max_rank],19,MilitaryUI.PALE)
	app.label(left,"将领经验  %d"%int(profile.general_xp.get(id,0)),18,Color("ccd2c6"))
	if life.get("late_stage_is_last_living_period",false):app.label(left,"末期形象取自生前年代",16,MilitaryUI.BRASS)
	var right=app.scroll_column(layout);right.name="DossierDevelopment"
	section(app,right,"兵种专长","星级与战法为游戏平衡参数")
	var abilities=app.war_room.grid(right,170)
	abilities.set_meta("max_columns",3)
	for family in FAMILIES:
		var cell=app.ui_panel(abilities,"ui_paper_panel",Color.WHITE,10)
		cell.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		var line=app.row(cell)
		var caption=app.label(line,FAMILIES[family],17,MilitaryUI.MUTED)
		caption.set_meta("dossier_ability_caption",true);caption.autowrap_mode=TextServer.AUTOWRAP_OFF
		caption.vertical_alignment=VERTICAL_ALIGNMENT_CENTER
		var value=app.label(line,str(d.stars[family])+" / 5",23,MilitaryUI.INK)
		value.autowrap_mode=TextServer.AUTOWRAP_OFF;value.horizontal_alignment=HORIZONTAL_ALIGNMENT_RIGHT
	promotion(app,right,d,rank,age_stage)
	var chosen=profile.get("active_skills",{}).get(id,d.active_skill)
	section(app,right,"战法","成长在下一局生效")
	if d.stars.cavalry>=3:
		var choices=app.row(right)
		for skill_id in [d.active_skill,"cavalry_sweep"]:
			var b=app.button(choices,("✓ " if chosen==skill_id else "")+app.content.definition("skills",skill_id).name,func():app.profiles.choose_active_skill(id,skill_id);show(app,id,age_stage))
			b.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	var skills=app.war_room.grid(right,330)
	skills.set_meta("max_columns",2)
	for skill_id in [d.passive_skill,chosen]:skill_card(app,skills,d,skill_id,age_stage)
	section(app,right,"勋章","最多装备 %d 枚，同类不可重复"%app.content.rules.progression.medal_slots)
	var medals=app.war_room.grid(right,260)
	for medal in app.content.tables.medals:medal_card(app,medals,d,medal,age_stage)
	section(app,right,"历史军职与来源","任职年代与战役出场分别核对")
	app.label(right,str(service.documented_title) if not str(service.get("documented_title","")).is_empty() else "军职资料尚待补充",19,MilitaryUI.INK)
	if service.get("documented_year")!=null:app.label(right,"文献见载于 %d 年；不表示完整任期"%int(service.documented_year),17,MilitaryUI.MUTED)
	if not str(service.get("life_year_note","")).is_empty():app.label(right,str(service.life_year_note),16,MilitaryUI.MUTED)
	if not str(service.get("name_correction_note","")).is_empty():app.label(right,str(service.name_correction_note),16,MilitaryUI.MUTED)
	app.label(right,"历史军职不等于游戏成长等级。开局是否出场及其所属部队以该战役名单为准。",17,MilitaryUI.MUTED)
	for source_id in service.get("source_ids",[]):
		var source=app.content.definition("commander_sources",str(source_id))
		app.label(right,str(source.get("title",source.get("publisher",source_id))),16,MilitaryUI.MUTED)
		app.label(right,str(source.get("url","")),15,MilitaryUI.MUTED)
	selector.tooltip_text="对局按日期自动选择形象；此处可预览各阶段。标准化挑战使用默认成长配置。"

static func section(app, parent: Node, title: String, subtitle: String) -> void:
	var head=app.row(parent)
	app.label(head,title,25,MilitaryUI.INK)
	var note=app.label(head,subtitle,16,MilitaryUI.MUTED)
	note.horizontal_alignment=HORIZONTAL_ALIGNMENT_RIGHT
	app.ui_rule(parent,Color("acb8b4"))

static func promotion(app, parent: Node, d: Dictionary, rank: int, stage: String) -> void:
	var card=app.war_room.card(parent)
	var line=app.row(card);var info=app.column(line);app.label(info,"成长晋升",22,MilitaryUI.INK)
	var reason="军衔已满";var enabled=false;var caption="已达最高等级"
	if rank<int(d.max_rank):
		var price=int(app.content.rules.progression.general_rank_cost_merit[rank])
		var xp=int(app.content.rules.progression.general_rank_xp[rank])
		enabled=int(app.profiles.profile.merit)>=price and int(app.profiles.profile.general_xp.get(d.id,0))>=xp
		reason="需要 %d 功勋 · %d 将领经验"%[price,xp]
		caption="晋升 · %d 功勋"%price
	app.label(info,reason,17,MilitaryUI.MUTED)
	var b=app.button(line,caption,func():if not app.profiles.upgrade_general(d.id):app.show_profile_error() else:show(app,d.id,stage),enabled,reason)
	b.size_flags_horizontal=Control.SIZE_SHRINK_END
	b.name="PromoteGeneral_"+str(d.id)

static func skill_card(app, parent: Node, d: Dictionary, skill_id: String, stage: String) -> void:
	var skill=app.content.definition("skills",skill_id)
	var rank=int(app.profiles.profile.skill_ranks.get(d.id+":"+skill_id,1))
	var c=app.war_room.card(parent);var top=app.row(c)
	app.image_view(top,app.assets.texture("icon","icon_"+skill_id),Vector2(58,58))
	var copy=app.column(top);app.label(copy,skill.name,22,MilitaryUI.INK)
	app.label(copy,("主动" if skill.kind=="active" else "被动")+" · %d / %d 级"%[rank,skill.max_rank],16,MilitaryUI.MUTED)
	if skill.kind=="active":app.label(c,"指挥 %d · 冷却 %d 日"%[skill.command_cost,skill.cooldown_own_phases],16,MilitaryUI.MUTED)
	var enabled=false;var reason="战法已满级";var caption="已达最高等级"
	if rank<int(skill.max_rank):
		var price=int(app.content.rules.progression.skill_upgrade_cost_merit[rank-1])
		var xp=int(app.content.rules.progression.skill_upgrade_cost_xp[rank-1])
		reason="需要 %d 功勋 · %d 将领经验"%[price,xp]
		enabled=int(app.profiles.profile.merit)>=price and int(app.profiles.profile.general_xp.get(d.id,0))>=xp
		caption="升级 · %d 功勋"%price
	app.label(c,reason,16,MilitaryUI.MUTED)
	var b=app.button(c,caption,func():if not app.profiles.upgrade_skill(d.id,skill_id):app.show_profile_error() else:show(app,d.id,stage),enabled,reason)
	b.name="UpgradeSkill_"+skill_id

static func medal_card(app, parent: Node, d: Dictionary, medal: Dictionary, stage: String) -> void:
	var c=app.war_room.card(parent);c.name="MedalCard_"+str(medal.id)
	var head=app.row(c)
	app.image_view(head,app.assets.texture("icon","icon_medal_"+str(medal.id).trim_suffix("_medal")+"_v023"),Vector2(54,54))
	app.label(head,medal.name,22,MilitaryUI.INK)
	var owned=app.profiles.profile.medals.filter(func(m):return m.general_id==d.id)
	var equipped=owned.filter(func(m):return m.medal_id==medal.id)
	if not equipped.is_empty():
		app.label(c,"已装备 · %d 级"%equipped[0].rank,18,Color("526f60"))
		app.label(c,medal_effect(medal,int(equipped[0].rank)),17,MilitaryUI.MUTED)
		var remove=app.button(c,"卸下",func():app.profiles.unequip_medal(d.id,medal.id);show(app,d.id,stage))
		remove.name="UnequipMedal_"+str(medal.id)
		return
	var rank=int(medal_choices.get(medal.id,1));var price=int(medal.cost_merit[rank-1])
	var selector=app.war_room.option(c,["1 级 · %d 功勋"%medal.cost_merit[0],"2 级 · %d 功勋"%medal.cost_merit[1],"3 级 · %d 功勋"%medal.cost_merit[2]])
	selector.name="MedalRank_"+str(medal.id);selector.select(rank-1)
	selector.item_selected.connect(func(index):medal_choices[medal.id]=index+1;show(app,d.id,stage))
	app.label(c,medal_effect(medal,rank),17,MilitaryUI.MUTED)
	var reason="" if app.profiles.profile.merit>=price else "功勋不足，还需 %d"%(price-app.profiles.profile.merit)
	if owned.size()>=int(app.content.rules.progression.medal_slots):reason="两个勋章槽已满"
	app.label(c,"可装备" if reason.is_empty() else reason,16,Color("526f60") if reason.is_empty() else Color("875c4b"))
	var equip=app.button(c,"装备 · %d 功勋"%price,func():if not app.profiles.equip_medal(d.id,medal.id,rank):app.show_profile_error() else:show(app,d.id,stage),reason.is_empty(),reason)
	equip.name="EquipMedal_"+str(medal.id)

static func medal_effect(medal: Dictionary, rank: int) -> String:
	match str(medal.effect):
		"attack_bonus":return "对应兵种攻击 +%s%%"%str(float(medal.values_permille[rank-1])/10.0)
		"defense_flat":return "防御 +%d"%medal.values[rank-1]
		"food_upkeep_reduction":return "粮秣消耗 −%s%%"%str(float(medal.values_permille[rank-1])/10.0)
	return ""
