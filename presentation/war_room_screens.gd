class_name WarRoomScreens
extends RefCounted

# Shared native layouts. Every action still goes through the existing profile
# repository or command worker; the presentation does not duplicate game rules.
var app
var browser_mode="campaign"
var browser_id=""
var browser_owner=""
var browser_era="all"
var atlas: WarRoomAtlas
var browser_list: VBoxContainer
var browser_brief: VBoxContainer
var browser_actions: VBoxContainer
var browser_buttons: Dictionary={}
var hq_tab="generals"
var tech_branch="infantry"

const TITLES={"campaign":"战役档案","conquest":"时代征服","legion":"军团训练"}
const OBJECTIVES={"capture":"突破城防，占领目标城市","hold":"占领并连续守住目标","escort":"护送指定编队抵达接应点","survive":"保全主力，坚持至事件结束","repair":"派遣工兵，抢通受损铁路","destroy":"消灭指定敌军编队","capture_commander":"俘获或击溃目标将领","unify":"统一战略节点，或在期限内以积分获胜"}
const BRANCHES={"infantry":"步兵","artillery":"炮兵","cavalry":"骑兵","navy":"海军","aviation":"航空","logistics":"后勤","staff":"参谋"}
const RESOURCE_NAMES={"cash":"军费","food":"粮秣","arms":"军械","fuel":"燃油","silver":"白银"}

func scale() -> float:return float(app.settings.ui_scale)
func touch_height() -> float:return maxf(96 if app.mobile_layout() else 48,48*scale())

func card(parent: Node) -> VBoxContainer:
	var shell=app.ui_panel(parent,"ui_dialog_frame",Color(1.025,1.025,1.015,1),14)
	shell.set_meta("ui_light",true);shell.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	var v=app.column(shell);v.add_theme_constant_override("separation",8);return v

func grid(parent: Node, minimum_width: float=390) -> GridContainer:
	var g=GridContainer.new();g.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	g.add_theme_constant_override("h_separation",14);g.add_theme_constant_override("v_separation",14);parent.add_child(g)
	g.resized.connect(func():fit_grid(g,minimum_width));fit_grid(g,minimum_width);return g

func fit_grid(g: GridContainer, minimum_width: float) -> void:
	if not is_instance_valid(g):return
	var available=g.get_parent().size.x
	if available<100:available=app.get_viewport_rect().size.x-128
	g.columns=clampi(int((available+14)/(minimum_width*scale()+14)),1,4)

func cost_text(cost: Dictionary) -> String:
	var pieces=PackedStringArray()
	for key in RESOURCE_NAMES:
		if int(cost.get(key,0))>0:pieces.append("%d%s"%[cost[key],RESOURCE_NAMES[key]])
	return " / ".join(pieces) if not pieces.is_empty() else "无资源消耗"

func status(parent: Node) -> Label:
	var l=app.label(parent,"正在核对条件…",16,Color("7a6650"));l.custom_minimum_size.y=24*scale();return l

func action(parent: Node, text: String, command: Dictionary, reason: Label) -> Button:
	return app.command_button(parent,text,command,reason)

func option(parent: Node, values: Array) -> OptionButton:
	var control=OptionButton.new();control.custom_minimum_size.y=touch_height();control.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	control.add_theme_font_size_override("font_size",int(19*scale()));control.clip_text=true
	for text in values:control.add_item(str(text))
	parent.add_child(control);return control

func page(title: String, subtitle: String) -> VBoxContainer:
	app.new_screen();app.background("background_campaign")
	var m=app.margin(app.screen,24);m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var outer=app.ui_panel(m,"ui_hud_plate",Color.WHITE,16);var v=app.column(outer)
	var head=app.row(v);app.label(head,title,34);app.button(head,"返回",app.show_home)
	app.label(v,subtitle,17,app.UI_MUTED);return v

func show_terrain_atlas(section: int=0) -> void:
	var v=app.modal("地形图鉴 · 区域地表")
	app.label(v,"查看地图上的地表纹理。通行消耗与掩护以所选地格的地貌为准。",18,Color("65716b"))
	var sections=["草地与荒漠","寒带与林带","河谷与峰岭"]
	var tabs=app.row(v)
	for index in range(sections.size()):
		var tab=app.button(tabs,sections[index],func():show_terrain_atlas(index))
		tab.custom_minimum_size.y=touch_height()
		if index==section:tab.add_theme_stylebox_override("normal",app.material_box("ui_button_plate",Color(1.2,1.13,.91),10))
	if not MapTerrainSurfaces.available():app.label(v,"地表素材尚未安装",22);return
	var groups=[[
		"temperate_meadow","dry_steppe","desert_steppe","dune_sand","gravel_gobi","saline_meadow","alpine_meadow","alpine_steppe"],[
		"tundra_moss","boreal_litter","temperate_litter","conifer_litter","subtropical_humus","tropical_moist_humus","dry_woodland_litter","savanna_red_soil"],[
		"flood_meadow","alluvial_loam","weathered_rock","alpine_scree"]]
	var g=grid(v,310)
	for family in groups[clampi(section,0,2)]:
		var definition: Dictionary=MapTerrainSurfaces.data().types[family]
		var originals: Array=definition.assets.duplicate()
		var macro=MapTerrainSurfaces.macro_id(family)
		if not macro.is_empty():originals.push_front(macro)
		var body=card(g);body.set_meta("terrain_surface",family)
		app.label(body,definition.name,23,Color("39484a"))
		var picture=app.image_view(body,app.assets.texture("tile",originals[0]),Vector2(180,132))
		picture.name="TerrainMaterialPreview";picture.set_meta("variant",0);picture.set_meta("variant_count",originals.size())
		var caption=app.label(body,"连续底材" if not macro.is_empty() else "细节底纹 1 / 4",16,Color("65716b"))
		var change=app.button(body,"查看另一幅底纹",func():
			var variant=(int(picture.get_meta("variant",0))+1)%originals.size()
			picture.set_meta("variant",variant);picture.texture=app.assets.texture("tile",originals[variant])
			caption.text=("连续底材" if variant==0 else "细节底纹 %d / 4"%variant) if not macro.is_empty() else "细节底纹 %d / 4"%(variant+1))
		change.name="TerrainVariant";change.custom_minimum_size.y=touch_height()
	app.label(v,"地表按区域生态与高程资料配置；林带底材与实际树林分开显示。",16,Color("65716b"))
	var bottom_space=Control.new();bottom_space.custom_minimum_size.y=16*scale();v.add_child(bottom_space)

func scenario_ids(mode: String, era: String="all") -> Array:
	var result: Array=[]
	for id in app.content.scenarios:
		var r=app.content.scenarios[id]
		if r.mode==mode and (era=="all" or r.anchor_date.substr(0,4)==era):result.append(id)
	result.sort_custom(func(a,b):return app.content.scenarios[a].anchor_date<app.content.scenarios[b].anchor_date if app.content.scenarios[a].anchor_date!=app.content.scenarios[b].anchor_date else a<b)
	return result

func show_browser(mode: String) -> void:
	if browser_mode!=mode:browser_era="all";browser_id=""
	browser_mode=mode
	var v=page(TITLES[mode],"选择时代与任务，查看真实地理战区，再进入部署。")
	app.audio.set_music("menu")
	var tabs=v.get_child(0);var index=1
	for key in TITLES:
		var tab=app.button(tabs,"%s %d"%[{"campaign":"战役","conquest":"征服","legion":"军团"}[key],scenario_ids(key).size()],func():app.show_scenario_browser(key));tabs.move_child(tab,index);index+=1
		if key==mode:tab.add_theme_stylebox_override("normal",app.material_box("ui_button_plate",Color(1.23,1.15,.88),10))
	var body=app.row(v);body.size_flags_vertical=Control.SIZE_EXPAND_FILL;body.add_theme_constant_override("separation",16)
	var left=app.column(body);left.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	var map_shell=app.ui_panel(left,"ui_hud_plate",Color.WHITE,6);map_shell.size_flags_vertical=Control.SIZE_EXPAND_FILL
	var map_content=app.column(map_shell);app.ui_kicker(map_content,"战区沙盘  /  北向固定 · 当期铁路 · 城市节点",app.UI_MUTED,13)
	atlas=WarRoomAtlas.new();atlas.name="WarRoomAtlas";atlas.configure(app.content,app.assets,scale());atlas.custom_minimum_size=Vector2(260,180);atlas.size_flags_horizontal=Control.SIZE_EXPAND_FILL;atlas.size_flags_vertical=Control.SIZE_EXPAND_FILL;map_content.add_child(atlas)
	atlas.faction_selected.connect(func(owner):browser_owner=owner;select_recipe(browser_id))
	var brief_shell=app.ui_panel(left,"ui_dialog_frame",Color.WHITE,16);brief_shell.set_meta("ui_light",true)
	browser_brief=app.column(brief_shell)
	var sidebar=app.ui_panel(body,"ui_hud_plate",Color.WHITE,12)
	sidebar.custom_minimum_size.x=clampf(app.get_viewport_rect().size.x*.30,330*minf(scale(),1.25),570)
	var side=app.column(sidebar);app.ui_kicker(side,"作战计划",app.UI_BRASS,14)
	var eras: Array=["全部年代"];var years: Array=["all"]
	for id in scenario_ids(mode):
		var year=app.content.scenarios[id].anchor_date.substr(0,4)
		if not years.has(year):years.append(year);eras.append(year+" 年")
	var era_select=option(side,eras);era_select.name="EraSelector";era_select.select(maxi(0,years.find(browser_era)))
	era_select.item_selected.connect(func(index):browser_era=years[index];fill_scenarios())
	if mode!="legion":
		var difficulties=option(side,["普通 · 成长档案","困难 · 敌军攻击 +10%","挑战 · 标准化成长"]);difficulties.name="DifficultySelector"
		difficulties.select(maxi(0,["normal","hard","challenge"].find(app.difficulty)))
		difficulties.item_selected.connect(func(index):app.difficulty=["normal","hard","challenge"][index];select_recipe(browser_id);style_scenario_buttons())
	browser_list=app.scroll_column(side);browser_list.add_theme_constant_override("separation",9)
	app.ui_rule(side,Color("576368"));browser_actions=app.column(side)
	fill_scenarios()

func fill_scenarios() -> void:
	app.clear(browser_list);browser_buttons={}
	var ids=scenario_ids(browser_mode,browser_era)
	if not ids.has(browser_id):browser_id=str(ids[0]) if not ids.is_empty() else ""
	for id in ids:
		var r=app.content.scenarios[id]
		var control=app.button(browser_list,"",func():browser_owner="";select_recipe(id))
		control.name="Scenario_"+id;control.set_meta("scenario_id",id);control.clip_text=true;control.alignment=HORIZONTAL_ALIGNMENT_LEFT
		control.custom_minimum_size.y=maxf(touch_height(),100*minf(scale(),1.5));control.add_theme_font_size_override("font_size",int(18*scale()))
		control.tooltip_text=r.name+"\n"+r.anchor_date+"\n"+OBJECTIVES.get(r.objective_type,"完成指定任务")
		browser_buttons[id]=control
	if not browser_id.is_empty():select_recipe(browser_id)

func style_scenario_buttons() -> void:
	for id in browser_buttons:
		var r=app.content.scenarios[id];var b:Button=browser_buttons[id]
		var stars=int(app.profiles.profile.victories.get(id+":"+app.difficulty,0))
		var locked=r.mode=="campaign" and not app.profiles.profile.campaign_unlocked.has(id)
		b.text="%s%s\n%s  ·  %d 回合\n%s"%["▶ " if id==browser_id else "",r.name,r.anchor_date,r.round_limit,"★".repeat(stars) if stars>0 else ("前置任务未完成" if locked else "待部署")]
		b.add_theme_stylebox_override("normal",app.material_box("ui_button_plate",Color(1.2,1.13,.91) if id==browser_id else Color(.80,.87,.88),10))

func reveal_selected_scenario(id: String, list: VBoxContainer) -> void:
	# Selection may be restored far down the chronology or changed by the map.
	# Wait for containers to settle before revealing the actual selected card.
	for frame in range(2):await app.get_tree().process_frame
	if id!=browser_id or not is_instance_valid(list) or list!=browser_list:return
	var button=browser_buttons.get(id)
	if is_instance_valid(button) and list.get_parent() is ScrollContainer:
		list.get_parent().ensure_control_visible(button)

func select_recipe(id: String) -> void:
	if id.is_empty() or not is_instance_valid(browser_brief):return
	browser_id=id;var r=app.content.scenarios[id];var source_map=app.content.maps[r.map_id]
	var playable=app.content.playable_factions(id) if r.mode=="conquest" else [r.player_default]
	if not playable.has(browser_owner):browser_owner=r.player_default if playable.has(r.player_default) else (str(playable[0]) if not playable.is_empty() else "")
	atlas.select_scenario(id,browser_owner);app.clear(browser_brief);app.clear(browser_actions);style_scenario_buttons()
	reveal_selected_scenario.call_deferred(id,browser_list)
	var headline=app.row(browser_brief);app.label(headline,r.name,24,Color("39484a"));var date=app.label(headline,r.anchor_date,16,Color("66716a"));date.name="ScenarioDate";date.autowrap_mode=TextServer.AUTOWRAP_OFF;date.size_flags_horizontal=Control.SIZE_SHRINK_END
	var scope=" · ".join(r.get("province_scope",[]))
	var goal=OBJECTIVES.get(r.objective_type,"完成指定任务")
	var target=source_map.cities.filter(func(c):return c.id==r.get("target_city_id",""))
	if r.objective_type in ["capture","hold","escort"] and not target.is_empty():goal+="  ·  "+str(target[0].name)
	var summary=app.row(browser_brief);app.label(summary,goal,19,Color("6e583b"))
	app.label(summary,"%d回合 · %d将领席位 · %d城市节点"%[r.round_limit,r.general_slots,source_map.cities.size()],15)
	if r.mode=="conquest":
		app.label(browser_brief,"城市标记表示开局控制；自由发展后，外交与领土随玩家行动改变。",14,Color("65716b"))
	else:app.label(browser_brief,(scope+"  /  " if not scope.is_empty() else "")+"地理据真实资料抽象；战术部署与任务目标属于游戏设计。",14,Color("65716b"))
	app.label(browser_actions,"选择阵营" if r.mode=="conquest" else "出战阵营",17,app.UI_MUTED)
	if r.mode=="conquest":
		var names: Array=[]
		for owner in playable:names.append(app.content.definition("factions",owner).get("name",owner))
		var factions=option(browser_actions,names);factions.name="FactionSelector";factions.select(maxi(0,playable.find(browser_owner)))
		factions.item_selected.connect(func(index):browser_owner=playable[index];select_recipe(id))
	else:app.label(browser_actions,app.content.definition("factions",browser_owner).get("name",browser_owner),24,app.UI_BRASS_BRIGHT)
	app.label(browser_actions,cost_text(r.starting_resources),16,app.UI_MUTED)
	var unlocked=r.mode!="campaign" or app.profiles.profile.campaign_unlocked.has(id)
	var launch=app.button(browser_actions,"编组并训练" if r.mode=="legion" else ("开始征服" if r.mode=="conquest" else "开始任务"),func():if r.mode=="legion":app.show_legion_deployment(id) else:app.start_game(id,browser_owner),unlocked and not playable.is_empty())
	launch.name="LaunchScenario";launch.custom_minimum_size.y=maxf(touch_height(),64*scale())
	if not unlocked:
		var prerequisites: Array=[]
		for previous in r.get("unlock_after",[]):prerequisites.append(app.content.scenarios.get(previous,{}).get("name",previous))
		app.label(browser_actions,"先完成："+"、".join(prerequisites),16,Color("e2bca2"))

func city_banner(v: Node, city: Dictionary) -> void:
	var h=app.row(v);app.label(h,city.name+"  ·  "+str(city.level)+"级城市",27,Color("39484a"))
	app.label(h,"稳定 %d%%  ·  兵源 %d"%[city.stability,city.recruit_reserve],18)
	var faction=StateAccess.faction(app.match_controller.state,app.match_controller.state.player_faction_id)
	app.label(v,"现有军需  "+cost_text(faction.resources),18,Color("6e583b"))
	app.ui_rule(v,Color("9aa39d"))

func production_queues(v: Node, city: Dictionary, construction: bool=false) -> void:
	var queues=city.construction_queue if construction else city.recruit_queue
	app.label(v,("建设队列" if construction else "征募队列")+"  %d / %d"%[queues.size(),1 if construction else 3],20,Color("6d5e44"))
	if queues.is_empty():app.label(v,"队列空闲 · 选择下方卡片部署生产",16,Color("68756f"));return
	for queued in queues:
		var r=app.row(v)
		var name="城市升级" if queued.target_def_id=="city_level" else app.content.definition("buildings" if construction else "units",queued.target_def_id).name
		app.label(r,"%s · %s"%[name,"待部署" if queued.get("ready",false) else "余 %d 阶段"%queued.remaining_own_phases],18)
		var progress=ProgressBar.new();progress.size_flags_horizontal=Control.SIZE_EXPAND_FILL;progress.custom_minimum_size=Vector2(100,14);progress.show_percentage=false;progress.max_value=maxi(1,int(queued.get("total_own_phases",queued.remaining_own_phases)));progress.value=progress.max_value-queued.remaining_own_phases;r.add_child(progress)
		app.command_button(r,"撤销",app.match_controller.command("CancelQueue",{"city_id":city.id,"queue_id":queued.id,"construction":construction}))

func show_recruit(city_id: String) -> void:
	var city=StateAccess.find(app.match_controller.state,"cities",city_id);var v=app.modal("城市征募 · 选择兵种与编制")
	city_banner(v,city);production_queues(v,city)
	var g=grid(v)
	for d in app.content.tables.units:recruit_card(g,city_id,d,{})
	app.label(v,"精锐编制  /  科技与章节解锁",24,Color("6d5e44"));var elites=grid(v)
	for elite in app.content.tables.elite_variants:recruit_card(elites,city_id,app.content.definition("units",elite.base_unit),elite)

func recruit_card(parent: Node, city_id: String, definition: Dictionary, elite: Dictionary) -> void:
	var v=card(parent);var d=EffectRules.scaled_definition({"def_id":definition.id,"elite_id":elite.get("id")},app.content)
	v.set_meta("recruit_unit",elite.get("id",d.id));var head=app.row(v)
	app.image_view(head,app.assets.texture("unit","unit_"+str(elite.get("id",d.id))+"_se"),Vector2(115,100)*minf(scale(),1.2))
	var copy=app.column(head);app.label(copy,elite.get("name",d.name),24);app.label(copy,"兵力 %d  ·  攻击 %d\n防御 %d  ·  行动 %d"%[d.hp,d.attack,d.defense,d.ap],17)
	app.label(v,"射程 %d—%d  ·  %d阶段完成  ·  %s"%[d.range_min,d.range_max,d.build_turns,"可占城" if d.can_occupy else "支援兵种"],16)
	var selectors=app.row(v);app.label(selectors,"编制层数",17);var values: Array=[]
	for stack in range(1,int(d.max_stack)+1):values.append("%d 层  ·  %d兵力"%[stack,int(d.hp)*stack])
	var stacks=option(selectors,values);stacks.name="RecruitStack"
	var offer=app.column(v)
	stacks.item_selected.connect(func(index):recruit_offer(offer,city_id,d,int(index)+1,elite))
	recruit_offer(offer,city_id,d,1,elite)

func recruit_offer(parent: Node, city_id: String, d: Dictionary, stack: int, elite: Dictionary) -> void:
	app.clear(parent)
	var state=app.match_controller.state;var cost=EconomyRules.recruit_cost(state,state.player_faction_id,d.id,stack,elite.get("id"),app.content)
	app.label(parent,cost_text(cost)+"  ·  %d兵源"%(stack*10),17,Color("735d3e"))
	var reason=status(parent);var command=app.match_controller.command("Recruit",{"city_id":city_id,"def_id":d.id,"stack":stack})
	if not elite.is_empty():command.elite_id=elite.id
	action(parent,"征募 · %d 层"%stack,command,reason).size_flags_horizontal=Control.SIZE_EXPAND_FILL

func show_buildings(city_id: String) -> void:
	var city=StateAccess.find(app.match_controller.state,"cities",city_id);var v=app.modal("城市建设 · 设施与升级")
	city_banner(v,city);production_queues(v,city,true)
	var used=0
	for record in city.buildings:used+=int(app.content.definition("buildings",record.def_id).get("slot_cost",0))
	app.label(v,"一般设施槽 %d / 4 · 工事不占槽 · 完工后生效，升级期间原设施继续工作。"%used,17)
	var g=grid(v)
	for d in app.content.tables.buildings:
		var vcard=card(g);var current=EconomyRules.building_level(city,d.id);var next=mini(current+1,d.max_level)
		var damaged=city.buildings.filter(func(b):return b.def_id==d.id and b.get("damaged",false))
		if not damaged.is_empty():next=int(damaged[0].level)
		var target_level=d.level_definitions[next-1];var head=app.row(vcard)
		app.image_view(head,app.assets.texture("building","building_"+d.id+"_intact"),Vector2(120,96)*minf(scale(),1.2))
		var info=app.column(head);app.label(info,d.name,25);app.label(info,"受损 · 修复至 %d级"%next if not damaged.is_empty() else "当前 %d / %d 级"%[current,d.max_level],18)
		app.label(vcard,building_description(d),17)
		app.label(vcard,"%d级 · %s · %d阶段"%[next,cost_text(target_level.cost),target_level.build_own_phases],17,Color("735d3e"))
		var reason=status(vcard);var actions=app.row(vcard)
		action(actions,"修复" if not damaged.is_empty() else ("建设" if current==0 else "升级"),app.match_controller.command("Build",{"city_id":city_id,"def_id":d.id}),reason).size_flags_horizontal=Control.SIZE_EXPAND_FILL
		if current>0:app.command_button(actions,"拆除",app.match_controller.command("DemolishBuilding",{"city_id":city_id,"def_id":d.id}))

func building_description(d: Dictionary) -> String:
	return {"barracks":"训练步兵、骑兵与工兵编制。","workshop":"训练炮兵与机械化编队。","arsenal":"增加城市军械生产收入。","market":"提高军费收入，支撑建设与军饷。","granary":"增加城市军粮收入，维持军队给养。","station":"接入铁路投送，增加车站运输能力。","port":"提供港口与舰艇生产、海上运输支持。","hospital":"提升驻地补员与持续作战能力。","supply_depot":"增强驻地军需与补给保障。","telegraph":"增加指挥点与通信支持。","fortification":"强化城市防御，不占一般设施槽。","airfield":"在剧本允许的城市开放航空支援。"}.get(d.id,"设施作用与部署条件由本局规则决定。")

func show_generals(unit_id: String) -> void:
	var v=app.modal("将领任命 · 本阶段不能再攻击")
	app.label(v,"选定编队任命后会消耗本阶段攻击机会。可用名单以当前剧本为准。",18)
	var g=grid(v)
	for general in app.match_controller.state.generals:
		var d=app.content.definition("generals",general.id);var c=card(g);general_portrait(c,d,general.rank)
		var reason=status(c);action(c,"任命到选定编队",app.match_controller.command("AssignGeneral",{"unit_id":unit_id,"general_id":general.id}),reason)

func general_portrait(parent: Node, d: Dictionary, rank: int) -> void:
	var head=app.row(parent);app.image_view(head,app.assets.texture("portrait","portrait_"+d.id),Vector2(110,130)*minf(scale(),1.2))
	var copy=app.column(head);app.label(copy,d.name,27);app.label(copy,"军衔  %d / %d"%[rank,d.max_rank],18,Color("735d3e"))
	app.label(copy,"步 %d  炮 %d  骑 %d\n海 %d  航 %d  后 %d"%[d.stars.infantry,d.stars.artillery,d.stars.cavalry,d.stars.navy,d.stars.aviation,d.stars.logistics],17)
	app.label(parent,app.content.definition("skills",d.passive_skill).name+" / "+app.content.definition("skills",d.active_skill).name,17)

func show_diplomacy() -> void:
	var state=app.match_controller.state;var player=StateAccess.faction(state,state.player_faction_id);var v=app.modal("外交事务 · 关系与条约")
	app.label(v,"本阶段  提案 %d  ·  宣战 %d  ·  援助 %d"%[player.diplomacy_orders_left,player.war_orders_left,player.aid_orders_left],22,Color("735d3e"))
	app.label(v,"停战与同盟包含借道、补给权；行动消耗、冷却与最低条约期限由当前战局核对。",17)
	var g=grid(v,420)
	for faction in state.factions:
		if faction.id==state.player_faction_id or faction.eliminated:continue
		var relation=StateAccess.relation(state,state.player_faction_id,faction.id);var acceptance=DiplomacyRules.acceptance(state,state.player_faction_id,faction.id)
		var c=card(g);var top=app.row(c);var strip=ColorRect.new();strip.color=MapView.TERRITORY_COLORS.get(faction.id,Color("70838a"));strip.custom_minimum_size=Vector2(7,52);top.add_child(strip)
		var text=app.column(top);app.label(text,StateAccess.faction_name(state,faction.id,app.content),25)
		app.label(text,{"WAR":"交战","NEUTRAL":"中立","TRUCE":"停战","ALLIANCE":"同盟"}.get(relation.state,relation.state),18,Color("915b49") if relation.state=="WAR" else Color("526e65"))
		var meter=ProgressBar.new();meter.max_value=100;meter.value=clampf(acceptance.score,0,100);meter.show_percentage=false;meter.custom_minimum_size.y=12;c.add_child(meter)
		app.label(c,"提案评分 %d / 接受门槛 50"%acceptance.score,18);app.label(c," · ".join(acceptance.reasons),16)
		if relation.minimum_until_round>state.round:app.label(c,"最低条约期限：第 %d 回合"%relation.minimum_until_round,16,Color("735d3e"))
		if relation.break_at_round>0:app.label(c,"解约生效：第 %d 回合"%relation.break_at_round,16,Color("915b49"))
		var buttons=grid(c,150)
		for entry in [["declare_war","宣战"],["truce","停战"],["alliance","结盟"],["break","通知解约"],["aid","援助50军费"]]:
			var slot=app.column(buttons);var reason=status(slot)
			var command=app.match_controller.command("Diplomacy",{"target_faction_id":faction.id,"action":entry[0],"passage":true,"supply":true})
			if entry[0]=="aid":command.resources={"cash":50}
			action(slot,entry[1],command,reason)

func show_headquarters(tab: String="", branch: String="") -> void:
	if not tab.is_empty():hq_tab=tab
	if not branch.is_empty():tech_branch=branch
	var profile=app.profiles.profile
	var v=page("指挥部","成长于下一局开局时生效；标准化挑战与军团训练使用独立快照。")
	var resources=app.row(v);app.ui_stat(resources,"功勋",str(profile.merit),"icon_resource_cash");app.ui_stat(resources,"研究",str(profile.research),"icon_tech_logistics")
	var tabs=app.row(v)
	for entry in [["generals","将领名册 · %d"%app.content.tables.generals.size()],["technology","军备研究 · %d"%app.content.tables.technologies.size()]]:
		var b=app.button(tabs,entry[1],func():show_headquarters(entry[0]));b.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		if hq_tab==entry[0]:b.add_theme_stylebox_override("normal",app.material_box("ui_button_plate",Color(1.2,1.12,.90),10))
	if hq_tab=="technology":
		var names: Array=[];var keys=BRANCHES.keys()
		for key in keys:names.append(BRANCHES[key]+"研究")
		var selector=option(v,names);selector.name="TechnologyBranch";selector.select(maxi(0,keys.find(tech_branch)));selector.item_selected.connect(func(index):show_headquarters("technology",keys[index]))
	var list=app.scroll_column(v);var g=grid(list,420)
	if hq_tab=="generals":
		for d in app.content.tables.generals:
			var c=card(g);var rank=int(profile.general_ranks.get(d.id,0));general_portrait(c,d,rank)
			var experience=int(profile.general_xp.get(d.id,0));app.label(c,"将领经验  %d"%experience,17)
			var can_upgrade=rank<d.max_rank;var price=0;var xp=0
			if can_upgrade:price=int(app.content.rules.progression.general_rank_cost_merit[rank]);xp=int(app.content.rules.progression.general_rank_xp[rank]);app.label(c,"晋升需要 %d 功勋 / %d 经验"%[price,xp],17,Color("735d3e"))
			var actions=app.row(c)
			app.button(actions,"晋升" if can_upgrade else "军衔已满",func():if not app.profiles.upgrade_general(d.id):app.show_profile_error() else:show_headquarters(),can_upgrade and profile.merit>=price and experience>=xp).size_flags_horizontal=Control.SIZE_EXPAND_FILL
			app.button(actions,"战法 / 勋章",func():app.show_general_growth(d.id)).size_flags_horizontal=Control.SIZE_EXPAND_FILL
	else:
		for d in app.content.tables.technologies:
			if d.branch!=tech_branch:continue
			technology_card(g,d)

func technology_card(parent: Node, d: Dictionary) -> void:
	var profile=app.profiles.profile;var rank=int(profile.tech_ranks.get(d.id,0));var c=card(parent);var head=app.row(c)
	app.image_view(head,app.assets.texture("icon","icon_tech_"+d.branch),Vector2(74,74));var info=app.column(head);app.label(info,d.name,25);app.label(info,"研究等级 %d / %d"%[rank,d.max_rank],18,Color("735d3e"))
	app.label(c,tech_effect(d,rank),18)
	var reason="";var cost=0
	for prerequisite in d.prerequisite:
		var name=app.content.definition("technologies",prerequisite.id).name
		app.label(c,"前置：%s %d级"%[name,prerequisite.rank],16)
		if int(profile.tech_ranks.get(prerequisite.id,0))<prerequisite.rank:reason="先研究 %s %d级"%[name,prerequisite.rank]
	if rank>=d.max_rank:reason="研究已完成"
	else:
		cost=int(d.cost_research_by_rank[rank])
		if reason.is_empty() and profile.research<cost:reason="研究点不足：还需 %d"%(cost-profile.research)
	app.label(c,reason if not reason.is_empty() else "可研究 · 下一局生效",16,Color("8d5e49") if not reason.is_empty() else Color("526f60"))
	app.button(c,"研究 · %d 研究点"%cost if rank<d.max_rank else "已完成",func():if not app.profiles.upgrade_tech(d.id):app.show_profile_error() else:show_headquarters(),reason.is_empty())

func tech_effect(d: Dictionary, rank: int) -> String:
	var names={"attack_bonus":"攻击加成","defense_flat":"防御","ap_flat":"行动点","vision_flat":"视野","recruit_cost_reduction":"征募费用降低","upkeep_cash_reduction":"军饷降低","reserve_cap_flat":"储粮容量","transport_pool_flat":"铁路运力","fort_bonus":"攻坚加成","reinforce_efficiency_bonus":"补员效率","ammo_refill_reduction":"补弹费用降低","cargo_survival_bonus":"运输生存率","command_pool_flat":"指挥点","food_upkeep_reduction":"粮食消耗降低","general_xp_bonus":"经验获取","morale_recovery_flat":"士气恢复","repair_cost_reduction":"抢修费用降低","reveal_radius_flat":"侦察半径","sortie_cap_flat":"航空出动上限","support_cost_reduction":"航空费用降低","support_damage_bonus":"航空伤害加成","suppression_flat":"压制","trade_cost_reduction":"交易费用降低"}
	var name=names.get(d.effect,"兵种能力")
	var next_rank=mini(rank+1,d.max_rank);var value=d.effect_by_rank[next_rank-1]
	var percentage=d.effect.ends_with("bonus") or d.effect.ends_with("reduction")
	return "%s%d级：%s +%s%s"%["下一" if rank<d.max_rank else "当前",next_rank,name,str(value/10.0) if percentage else str(value),"%" if percentage else ""]
