extends Control

const INK=Color("172731")
const PAPER=Color("eef0e3")
const BRASS=Color("c9ba8a")
# EW6-inspired hierarchy: steel command chrome, warm brass affordances and
# a restrained paper surface for objectives/city information. These are UI
# colors only; faction ownership continues to come from MapView.TERRITORY_COLORS.
const UI_STEEL=Color("172731")
const UI_STEEL_SOFT=Color("243742")
const UI_BRASS=Color("c9ba8a")
const UI_BRASS_BRIGHT=Color("e7d49c")
const UI_PAPER=Color("e5e8d9")
const UI_MUTED=Color("aebfc1")
const CommandCard = preload("res://presentation/command_button.gd")
const TouchScroll = preload("res://presentation/touch_scroll.gd")
var content=ContentRegistry.new()
var assets: AssetLibrary
var saves: SaveService
var profiles: ProfileRepository
var match_controller: MatchController
var audio: GameAudio
var screen: Control
var overlay: Control
var map_view: MapView
var header: VBoxContainer
var inspector: VBoxContainer
var orders: HFlowContainer
var busy_orders: HFlowContainer
var busy_auto_start: Button
var busy_auto_stop: Button
var busy_skip: Button
var busy_planning: Label
var busy_animation: Label
var notice: Label
var selected_unit_id=""
var selected_city_id=""
var selected_poi_id=""
var selected_terrain_hex: Variant=null
var pending: Dictionary={}
var order_mode=""
var auto_slot=0
var last_auto_phase=-1
var difficulty="normal"
var settings={"music":true,"sound":true,"grid":false,"tutorial":true,"music_volume":.25,"sfx_volume":.65,"ai_speed":1,"ui_scale":1.0,"animation_speed":1.0,"battle_cinematics":true,"reduced_motion":false}
var result_shown=false
var background_was_paused=false
var legion_draft: Dictionary={}
var legion_generals: Array=[]
var legion_draft_label: Label
var qa_save_path=""
var mission_card: VBoxContainer
var skip_button: Button
var selection_job: RulesJob
var selection_state: Dictionary={}
var selection_key=""
var selection_result: Dictionary={}
var target_card: PanelContainer
var qa_presentation_timings: Array=[]
var qa_order_timings: Array=[]
var file_operation_pending=false
var exit_requested=false
var battle_ui_epoch=0
# Native territory-color evidence renders the complete sourced country map once
# in a constrained QA pass.  It is deliberately opt-in and never changes a
# shipped play session or any rules state.
var territory_qa_mode=false
var inspector_shell: PanelContainer
var mission_shell: PanelContainer
var layer_shell: PanelContainer
var footer_shell: PanelContainer
var header_shell: PanelContainer
var war_room=WarRoomScreens.new()
var battle_hud: BattleHUD

func hud_line(parent: Node, text: String, font_size: int, color: Color = PAPER) -> Label:
	var line=label(parent,text,font_size,color)
	line.autowrap_mode=TextServer.AUTOWRAP_OFF
	line.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS
	line.tooltip_text=text
	return line

func _ready() -> void:
	get_tree().auto_accept_quit=false
	if not OS.has_feature("mobile"):DisplayServer.window_set_min_size(Vector2i(1280,720))
	Engine.max_fps=60
	assets=AssetLibrary.new()
	war_room.app=self
	if mobile_layout():settings.ui_scale=1.2
	var args=OS.get_cmdline_user_args()
	if "--qa-session" in args and qa_save_path.is_empty():qa_save_path="user://qa/native_%d"%Time.get_ticks_usec()
	saves=SaveService.new(qa_save_path,content) if not qa_save_path.is_empty() else SaveService.new("user://saves",content)
	var saved_settings=saves.load_slot("settings")
	if not saved_settings.is_empty():settings.merge(saved_settings,true)
	if "--ui-scale" in args and args.find("--ui-scale")+1<args.size():settings.ui_scale=clampf(float(args[args.find("--ui-scale")+1]),1.0,1.5)
	setup_theme()
	if not content.load_all():
		var label=Label.new();label.text="内容加载失败\n"+"\n".join(content.errors);add_child(label);return
	profiles=ProfileRepository.new(content,saves)
	match_controller=MatchController.new();add_child(match_controller);match_controller.setup(content)
	match_controller.presentation_enabled=true
	match_controller.changed.connect(on_changed);match_controller.rejected.connect(toast);match_controller.busy_changed.connect(refresh_orders);match_controller.ai_status.connect(func(t):if is_instance_valid(notice) and not t.is_empty():notice.text=t)
	audio=GameAudio.new();add_child(audio);apply_audio_settings()
	if not territory_qa_mode:show_home()
	get_viewport().size_changed.connect(on_resize)
	if "--smoke-battle" in args:start_game("campaign_1920_01","zhili")
	if "--scenario" in args:
		var index=args.find("--scenario")
		if index+1<args.size() and content.scenarios.has(args[index+1]):start_game(args[index+1],content.scenarios[args[index+1]].player_default)
	if "--capture" in args:capture_frame.call_deferred()
	if "--ui-test" in args:ui_smoke.call_deferred()
	if "--progression-ui-test" in args:progression_ui_smoke.call_deferred()
	if "--war-room-test" in args:WarRoomQA.run.call_deferred(self)
	if "--terrain-surface-test" in args:TerrainSurfaceQA.run.call_deferred(self)
	if "--control-land-test" in args:ControlLandQA.run.call_deferred(self)
	if "--ground-continuity-test" in args:GroundContinuityQA.run.call_deferred(self)
	if "--water-continuity-test" in args:WaterContinuityQA.run.call_deferred(self)
	if "--ground-coverage-test" in args:GroundCoverageQA.run.call_deferred(self)
	if "--music-test" in args:MusicPlaybackQA.run.call_deferred(self)
	if "--general-portrait-test" in args:GeneralPortraitQA.run.call_deferred(self)
	if "--commander-roster-test" in args:CommanderRosterQA.run.call_deferred(self)
	if "--dossier-test" in args:DossierQA.run.call_deferred(self)
	if "--relief-shade-test" in args:ReliefShadeQA.run.call_deferred(self)
	if "--map-symbol-test" in args:MapSymbolQA.run.call_deferred(self)
	if "--benchmark" in args:benchmark.call_deferred()
	if "--capacity-benchmark" in args:CapacityBenchmark.run.call_deferred(self)
	if "--unit-layer-test" in args:UnitLayerQA.run.call_deferred(self)
	if "--visual-playtest" in args:VisualPlaytest.run.call_deferred(self)
	if "--support-playtest" in args:VisualPlaytest.run_support.call_deferred(self)
	if "--responsiveness-test" in args:ResponsivenessQA.run.call_deferred(self)

func setup_theme() -> void:
	var t=Theme.new();t.default_font=assets.font;t.default_font_size=int(20*settings.ui_scale)
	t.set_color("font_color","Label",PAPER);t.set_color("font_color","Button",PAPER)
	t.set_stylebox("normal","Button",material_box("ui_button_plate",Color.WHITE,10))
	t.set_stylebox("hover","Button",material_box("ui_button_plate",Color(1.18,1.14,.96,1.0),10))
	t.set_stylebox("pressed","Button",material_box("ui_button_plate",Color(.78,.84,.82,1.0),10))
	t.set_stylebox("disabled","Button",material_box("ui_button_plate",Color(.58,.64,.65,.64),10))
	t.set_stylebox("focus","Button",box(Color(0,0,0,0),UI_BRASS_BRIGHT,2,10))
	t.set_color("font_disabled_color","Button",Color("939e9c"))
	t.set_constant("separation","VBoxContainer",7);t.set_constant("separation","HBoxContainer",8)
	t.set_stylebox("panel","PanelContainer",box(Color("233139"),Color("778184"),0,12))
	t.set_stylebox("panel","PopupMenu",box(INK,BRASS,2,14))
	t.set_stylebox("separator","HSeparator",box(Color("6f644e"),Color("6f644e"),0,0))
	t.set_color("font_color","OptionButton",PAPER);t.set_stylebox("normal","OptionButton",box(Color("465158"),Color("828b8d"),0,12))
	t.set_stylebox("hover","OptionButton",box(Color("586367"),UI_BRASS_BRIGHT,0,12));t.set_stylebox("pressed","OptionButton",box(Color("303b40"),UI_BRASS,0,12))
	t.set_stylebox("focus","OptionButton",box(Color(0,0,0,0),UI_BRASS_BRIGHT,2,9))
	t.set_color("font_color","CheckButton",PAPER);t.set_color("font_pressed_color","CheckButton",UI_BRASS_BRIGHT)
	t.set_stylebox("scroll","VScrollBar",box(Color("9caaac"),Color.TRANSPARENT,0,0))
	t.set_stylebox("grabber","VScrollBar",box(Color("485c64"),Color("bac1c1"),0,0))
	t.set_stylebox("grabber_highlight","VScrollBar",box(Color("76613f"),UI_BRASS,0,0))
	MilitaryUI.install(t,float(settings.ui_scale),assets)
	theme=t

func material_box(id: String, color: Color, padding: int) -> StyleBox:
	if id in ["ui_button_plate","ui_order_card","ui_dialog_frame","ui_hud_plate","ui_steel_panel","ui_paper_panel"]:
		return MilitaryUI.skin(id,color,padding)
	var style=StyleBoxTexture.new();style.texture=assets.texture("ui",id);style.modulate_color=color
	for side in [SIDE_LEFT,SIDE_TOP,SIDE_RIGHT,SIDE_BOTTOM]:style.set_texture_margin(side,24);style.set_content_margin(side,padding)
	return style

func box(fill: Color, border: Color, radius: int = 0, padding: int = 0) -> StyleBoxFlat:
	var s=StyleBoxFlat.new();s.bg_color=fill;s.border_color=border;s.set_border_width_all(1);s.set_corner_radius_all(radius);s.content_margin_left=padding;s.content_margin_right=padding;s.content_margin_top=padding;s.content_margin_bottom=padding;return s

func ui_panel(parent: Node, texture_id: String = "ui_steel_panel", tint: Color = Color.WHITE, padding: int = 10) -> PanelContainer:
	var p=PanelContainer.new()
	p.set_meta("ui_light",texture_id in ["ui_dialog_frame","ui_paper_panel"])
	# Optional newly generated art falls back to a native style while production
	# is pending. No raster is synthesized or edited by this fallback.
	if ResourceLoader.exists("res://assets/ui/"+texture_id+".png"):
		p.add_theme_stylebox_override("panel",material_box(texture_id,tint,padding))
	else:p.add_theme_stylebox_override("panel",box(Color("c7c9ca") if texture_id=="ui_dialog_frame" else Color(.10,.14,.16,.93),Color("7e888a"),0,padding))
	parent.add_child(p);return p

func ui_rule(parent: Node, color: Color = Color("9b8a64")) -> HSeparator:
	var line=HSeparator.new();line.add_theme_stylebox_override("separator",box(color,color,0,0));line.custom_minimum_size.y=2;parent.add_child(line);return line

func ui_kicker(parent: Node, text: String, color: Color = UI_BRASS, font_size: int = 13) -> Label:
	var l=label(parent,text,font_size,color);l.uppercase=true;l.add_theme_constant_override("outline_size",0);return l

func ui_stat(parent: Node, caption: String, value: String, icon_id: String = "") -> Control:
	var r=row(parent);r.size_flags_horizontal=Control.SIZE_SHRINK_BEGIN;r.add_theme_constant_override("separation",5);r.custom_minimum_size=Vector2(106,42)
	if not icon_id.is_empty() and ResourceLoader.exists("res://assets/icon/"+icon_id+".png"):image_view(r,assets.texture("icon",icon_id),Vector2(32,34))
	var c=column(r);c.add_theme_constant_override("separation",0);ui_kicker(c,caption,UI_MUTED,12);label(c,value,24,PAPER);return r

func clear(node: Node) -> void:
	for child in node.get_children():node.remove_child(child);child.queue_free()

func new_screen() -> void:
	battle_ui_epoch+=1
	if is_instance_valid(overlay):overlay.queue_free();overlay=null
	if is_instance_valid(screen):remove_child(screen);screen.queue_free()
	screen=Control.new();screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);add_child(screen)
	map_view=null;header=null;inspector=null;orders=null;busy_orders=null;notice=null;battle_hud=null
	selected_terrain_hex=null

func label(parent: Node, text: String, font_size: int = 22, color: Color = PAPER) -> Label:
	# Light EW6-style information dialogs opt into dark body copy while the
	# battle HUD keeps its pale text on steel. The metadata is inherited through
	# nested columns and never changes gameplay or map labels.
	var probe:Node=parent
	while probe!=null:
		if probe.has_meta("ui_light"):
			if not bool(probe.get_meta("ui_light")):break
			if color==PAPER:color=Color("354344")
			elif color in [BRASS,UI_BRASS_BRIGHT]:color=Color("765f3d")
			elif color.get_luminance()>.34:color=color.darkened(.46)
			break
		probe=probe.get_parent()
	var l=Label.new();l.add_theme_font_override("font",assets.map_font if font_size>=28 else assets.font);l.add_theme_font_size_override("font_size",int(font_size*settings.ui_scale));l.text=text;l.add_theme_color_override("font_color",color);l.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;l.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	parent.add_child(l);return l

func button(parent: Node, text: String, action: Callable, enabled: bool = true, tooltip: String = "") -> Button:
	var b=Button.new();b.add_theme_font_override("font",assets.font);b.add_theme_font_size_override("font_size",int(20*settings.ui_scale));b.text=text;b.custom_minimum_size=Vector2(96 if mobile_layout() else 0,maxf(96 if mobile_layout() else 48,48*settings.ui_scale));b.disabled=not enabled;b.tooltip_text=tooltip;b.mouse_filter=Control.MOUSE_FILTER_STOP;b.pressed.connect(func():audio.play("ui_select") if is_instance_valid(audio) else null;action.call());parent.add_child(b);return b

func row(parent: Node) -> HBoxContainer:
	var h=HBoxContainer.new();h.size_flags_horizontal=Control.SIZE_EXPAND_FILL;parent.add_child(h);return h

func column(parent: Node) -> VBoxContainer:
	var v=VBoxContainer.new();v.size_flags_horizontal=Control.SIZE_EXPAND_FILL;parent.add_child(v);return v

func margin(parent: Node, amount: int) -> MarginContainer:
	var insets=safe_insets() if parent==screen else Vector4.ZERO
	var m=MarginContainer.new();m.add_theme_constant_override("margin_left",amount+int(insets.x));m.add_theme_constant_override("margin_right",amount+int(insets.z));m.add_theme_constant_override("margin_top",amount+int(insets.y));m.add_theme_constant_override("margin_bottom",amount+int(insets.w));parent.add_child(m);return m

func mobile_layout() -> bool:return OS.has_feature("mobile") or "--mobile-ui-test" in OS.get_cmdline_user_args()

func safe_insets() -> Vector4:
	if not OS.has_feature("mobile"):return Vector4(40,0,20,0) if mobile_layout() else Vector4.ZERO
	var safe=DisplayServer.get_display_safe_area()
	if safe.size.x<=0 or safe.size.y<=0:return Vector4.ZERO
	var transform=get_viewport().get_screen_transform().affine_inverse();var a=transform*Vector2(safe.position);var b=transform*Vector2(safe.end);var extent=get_viewport_rect().size
	return Vector4(maxf(0,a.x),maxf(0,a.y),maxf(0,extent.x-b.x),maxf(0,extent.y-b.y))

func image_view(parent: Node, texture: Texture2D, size_min: Vector2) -> TextureRect:
	var view=TextureRect.new();view.texture=texture;view.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;view.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED;view.custom_minimum_size=size_min;view.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(view);return view

func scroll_column(parent: Node) -> VBoxContainer:
	var scroll=TouchScroll.new();scroll.size_flags_horizontal=Control.SIZE_EXPAND_FILL;scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL;scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;scroll.follow_focus=true;parent.add_child(scroll);return column(scroll)

func background(id: String) -> void:
	var image=TextureRect.new();image.texture=assets.texture("background",id);image.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;image.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_COVERED;image.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);image.mouse_filter=Control.MOUSE_FILTER_IGNORE;screen.add_child(image)
	var wash=ColorRect.new();wash.color=Color(.06,.09,.08,.42);wash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);wash.mouse_filter=Control.MOUSE_FILTER_IGNORE;screen.add_child(wash)

func show_home() -> void:
	new_screen();background("background_campaign");audio.set_music("menu")
	var m=margin(screen,64);m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var v=column(m)
	ui_kicker(v,"中国战区 · 真实地理 · 1840—1940",UI_BRASS_BRIGHT,15)
	label(v,"铁道烽烟",64);label(v,"军阀时代  /  亚洲全境",28,BRASS)
	label(v,"沿着真实铁路，调动军队、争夺城市、维持补给。",23,PAPER)
	var spacer=Control.new();spacer.size_flags_vertical=Control.SIZE_EXPAND_FILL;v.add_child(spacer)
	var hero=row(v);hero.size_flags_vertical=Control.SIZE_EXPAND;hero.add_theme_constant_override("separation",24)
	var dossier=ui_panel(hero,"ui_paper_panel",Color(1.0,1.0,1.0,.93),18);dossier.custom_minimum_size=Vector2(560,270);dossier.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	var dossier_copy=column(dossier);ui_kicker(dossier_copy,"战区档案 · 地理与铁路",Color("75633f"),14);label(dossier_copy,"亚洲战场总览",38,INK);ui_rule(dossier_copy,Color("9b8a64"));label(dossier_copy,"从鸦片战争、太平天国、义和团、护法、北伐到中日战场，按时间锚点进入局部战区。",21,Color("4e5c58"));label(dossier_copy,"沿真实海岸、河流与铁路争夺城市节点；各时代控制、战术部署与军力采用剧本抽象。",18,Color("65736d"))
	var menu=column(hero);menu.custom_minimum_size.x=390;menu.add_theme_constant_override("separation",6);ui_kicker(menu,"主战场",UI_BRASS_BRIGHT,14)
	for item in [["战役","%d场局部战区任务"%war_room.scenario_ids("campaign").size(),"campaign"],["自由世界","7个亚洲时间锚点 · 3个军阀开局","conquest"],["军团挑战","%d项标准化战术训练"%war_room.scenario_ids("legion").size(),"legion"]]:
		var main_button=button(menu,item[0],func():show_scenario_browser(item[2]));main_button.custom_minimum_size=Vector2(390,70);main_button.add_theme_font_size_override("font_size",int(26*settings.ui_scale));main_button.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		label(menu,item[1],15,UI_MUTED)
	var links=row(v)
	for item in [["指挥部",show_headquarters],["战报与成就",show_achievements],["读取存档",func():show_save_dialog(false)],["作战手册",show_manual],["设置",show_settings]]:hud_button(links,item[0],item[1]).size_flags_horizontal=Control.SIZE_EXPAND_FILL
	label(v,"本地单机  ·  铁路投送  ·  粮弹补给    /    地图据真实地理作战略抽象",18,Color("d2d4c0"))
	if not OS.has_feature("mobile"):button(v,"退出",func():get_tree().quit()).custom_minimum_size.x=120

func show_scenario_browser(mode: String) -> void:
	war_room.show_browser(mode)

func start_game(id: String, owner: String, deployment: Array = [], general_ids: Array = []) -> void:
	var start_profile=profiles.profile.duplicate(true)
	if not deployment.is_empty():start_profile._legion_deployment=deployment
	if content.scenarios[id].mode=="legion" and not deployment.is_empty():start_profile._legion_generals=general_ids
	if not match_controller.start(id,owner,start_profile,"normal" if content.scenarios[id].mode=="legion" else difficulty):return
	close_overlay();selected_unit_id="";selected_city_id="";selected_poi_id="";pending={};order_mode="";result_shown=false;last_auto_phase=-1
	build_battle();map_view.focus_player.call_deferred();audio.set_music("campaign")
	var commander=match_controller.state.units.filter(func(u):return u.owner_id==owner and u.position!=null and u.general_id!=null)
	if not commander.is_empty():selected_unit_id=commander[0].id;refresh_battle()
	if settings.tutorial and not territory_qa_mode:show_tutorial()

func build_battle() -> void:
	assets.prepare_battle_glyphs(settings.ui_scale)
	new_screen()
	map_view=MapView.new();map_view.territory_qa_mode=territory_qa_mode;map_view.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);map_view.custom_minimum_size=Vector2(600,400);screen.add_child(map_view);map_view.setup(content,assets);map_view.label_scale=settings.ui_scale;map_view.hex_selected.connect(on_hex_selected);map_view.place_selected.connect(on_place_selected);map_view.show_grid=settings.grid
	map_view.playback.speed=settings.animation_speed;map_view.playback.cinematics=settings.battle_cinematics;map_view.playback.reduced_motion=settings.reduced_motion;map_view.playback.cue.connect(audio.play)
	match_controller.presentation_options={"cinematics":settings.battle_cinematics,"reduced_motion":settings.reduced_motion}
	if territory_qa_mode:
		map_view.restore_headings(match_controller.facing_memory)
		map_view.set_state(match_controller.state)
		return
	# Edge HUD, inspired by the official EW6 native battlefield: the map fills
	# the viewport and compact information floats at its perimeter. No permanent
	# full-height inspector or oversized framed strip removes map width.
	header_shell=ui_panel(screen,"ui_hud_plate",Color.WHITE,8);header_shell.z_index=30;header_shell.anchor_right=1;header_shell.offset_left=12;header_shell.offset_right=-12;header_shell.offset_top=12
	header=column(header_shell);header.add_theme_constant_override("separation",4)
	mission_shell=ui_panel(screen,"ui_hud_plate",Color.WHITE,10);mission_shell.z_index=30;mission_shell.custom_minimum_size.x=282;mission_card=scroll_column(mission_shell);mission_card.add_theme_constant_override("separation",3)
	layer_shell=ui_panel(screen,"ui_hud_plate",Color.WHITE,4);layer_shell.z_index=30;layer_shell.anchor_left=1;layer_shell.anchor_right=1;layer_shell.offset_left=-110;layer_shell.offset_right=-12
	var layers=scroll_column(layer_shell);layers.set_meta("hud_layers",true);layers.add_theme_constant_override("separation",3)
	for item in [["势力",func():map_view.show_control=not map_view.show_control;map_view.queue_redraw();map_view.minimap.queue_redraw()],["地形",func():map_view.show_terrain=not map_view.show_terrain;map_view.queue_redraw()],["地名",func():map_view.show_places=not map_view.show_places;map_view.queue_redraw()],["查地名",func():selected_unit_id="";selected_city_id="";selected_poi_id="";pending={};order_mode="";refresh_battle();toast("点选村镇图标，查看地方与归属")],["铁路",func():map_view.show_rail=not map_view.show_rail;map_view.queue_redraw()],["补给",func():map_view.show_supply=not map_view.show_supply;map_view.queue_redraw()],["全图",show_strategic_map]]:hud_button(layers,item[0],item[1])
	var mini=StrategicMinimap.new();screen.add_child(mini);mini.z_index=30;mini.anchor_left=0;mini.anchor_right=0;mini.anchor_top=0;mini.anchor_bottom=0;mini.focused.connect(func(world):map_view.focus_world(world));map_view.minimap=mini
	inspector_shell=ui_panel(screen,"ui_hud_plate",Color.WHITE,10);inspector_shell.z_index=30;inspector=scroll_column(inspector_shell);inspector.add_theme_constant_override("separation",5)
	footer_shell=ui_panel(screen,"ui_hud_plate",Color.WHITE,8);footer_shell.z_index=30;footer_shell.anchor_top=1;footer_shell.anchor_bottom=1;footer_shell.anchor_right=1;footer_shell.offset_left=12;footer_shell.offset_right=-12;footer_shell.grow_vertical=Control.GROW_DIRECTION_BEGIN
	var c=column(footer_shell);c.add_theme_constant_override("separation",2);orders=HFlowContainer.new();orders.add_theme_constant_override("h_separation",12);orders.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.add_child(orders);notice=label(c,"选择部队 · 选择目标 · 再次点击确认；拖动平移，滚轮缩放。",14,UI_MUTED)
	map_view.label_obstacle_controls=[header_shell,mission_shell,layer_shell,mini,inspector_shell,footer_shell]
	battle_hud=BattleHUD.new();battle_hud.setup(self)
	# Put the cinema in the HUD canvas, above its plates. Previously it inherited
	# the map's lower canvas order and the footer concealed the result/roll row.
	map_view.cinema.reparent(screen);map_view.cinema.z_index=45
	map_view.restore_headings(match_controller.facing_memory)
	map_view.set_state(match_controller.state);refresh_battle()
	build_busy_orders(c)
	layout_battle_hud.call_deferred()

func layout_battle_hud() -> void:
	if not is_instance_valid(header_shell) or not is_instance_valid(map_view):return
	if battle_hud!=null:battle_hud.layout()

func build_busy_orders(parent: VBoxContainer) -> void:
	# These command controls are reused throughout the match. Constructing their
	# text and theme caches during an AI handoff caused the measured first-use stall.
	busy_orders=HFlowContainer.new();busy_orders.add_theme_constant_override("h_separation",8);parent.add_child(busy_orders);parent.move_child(busy_orders,1)
	busy_auto_start=hud_button(busy_orders,"自动作战",func():match_controller.toggle_auto_player();refresh_orders())
	busy_auto_stop=hud_button(busy_orders,"停止自动",func():match_controller.toggle_auto_player();refresh_orders())
	busy_skip=hud_button(busy_orders,"跳过演出  »",func():if is_instance_valid(map_view):map_view.playback.skip())
	busy_planning=label(busy_orders,"正在执行部署 · 可平移地图",20,BRASS)
	busy_animation=label(busy_orders,"行军 / 交战演出中",20,BRASS)
	busy_orders.visible=false

func on_changed(events: Array) -> void:
	if match_controller.state.is_empty():return
	var s=match_controller.state;var token=match_controller.generation;var f=StateAccess.faction(s,s.player_faction_id)
	audio.score_events(events,str(s.status))
	if s.status=="playing" and s.turn_order[s.phase_index]==s.player_faction_id and int(f.own_phase_index)!=last_auto_phase:
		last_auto_phase=f.own_phase_index;auto_slot=(auto_slot%3)+1
		autosave_snapshot(s,"auto_%d"%auto_slot)
	if is_instance_valid(map_view):
		var before=map_view.state
		if events.is_empty():map_view.playback.skip()
		var prepared=match_controller.prepared_presentation if not events.is_empty() else {}
		var timed=Time.get_ticks_usec()
		map_view.restore_headings(match_controller.facing_memory)
		map_view.set_state(s,events,prepared)
		var map_finished=Time.get_ticks_usec()
		if not before.is_empty() and not events.is_empty():
			if prepared.has("playback"):map_view.playback.adopt(prepared.playback)
			else:map_view.playback.begin(before,s,events,content)
		var playback_finished=Time.get_ticks_usec()
		match_controller.presentation_busy=map_view.playback.active
		if match_controller.presentation_busy:refresh_orders();toast("正在执行命令 · 可跳过演出")
		if "--responsiveness-test" in OS.get_cmdline_user_args():qa_presentation_timings.append({"map_us":map_finished-timed,"playback_us":playback_finished-map_finished,"orders_us":Time.get_ticks_usec()-playback_finished})
		while is_instance_valid(map_view) and map_view.playback.active and token==match_controller.generation:await get_tree().process_frame
		if token!=match_controller.generation:return
		match_controller.presentation_busy=false;refresh_battle(true)
	for event in events:
		if event.type=="MatchFinished":audio.play("victory" if s.status=="won" else "danger");audio.set_music("victory" if s.status=="won" else "campaign")
	if s.status!="playing" and not result_shown:show_result.call_deferred()

func refresh_battle(slice_work: bool = false) -> void:
	if not is_instance_valid(header):return
	battle_ui_epoch+=1;var epoch=battle_ui_epoch
	var s=match_controller.state;var f=StateAccess.faction(s,s.player_faction_id)
	if slice_work:
		await get_tree().process_frame
		if epoch!=battle_ui_epoch or not is_same(s,match_controller.state) or not is_instance_valid(header):return
	battle_hud.refresh_header(s,f)
	if slice_work:
		await get_tree().process_frame
		if epoch!=battle_ui_epoch or not is_same(s,match_controller.state) or not is_instance_valid(mission_card):return
	clear(mission_card);ui_kicker(mission_card,content.scenarios[s.scenario_id].name,UI_BRASS);var heading=row(mission_card);label(heading,"战役目标" if s.mode=="campaign" else "作战目标",18,PAPER);button(heading,"⋯",show_battle_briefing).custom_minimum_size=Vector2(96,96) if mobile_layout() else Vector2(38,34)
	for objective in s.objectives:
		var target=StateAccess.find(s,"cities",str(objective.target_ids[0])) if not objective.target_ids.is_empty() else {}
		var target_name=target.get("name","")
		if objective.type in ["escort","disembark"] and objective.has("destination"):
			var destination=StateAccess.at(s,"cities",HexGrid.coordinate(objective.destination))
			var protected_unit=StateAccess.find(s,"units",str(objective.target_ids[0])) if not objective.target_ids.is_empty() else {}
			var unit_name=content.definition("units",protected_unit.get("def_id","")).get("name","保护编队")
			target_name=unit_name+" → "+destination.get("name","目标格 %d,%d"%[objective.destination.q,objective.destination.r])+"（一格内）"
		if objective.type=="destroy":target_name="目标编队"
		if objective.type=="capture_commander" and not objective.target_ids.is_empty():target_name=content.definition("generals",str(objective.target_ids[0])).get("name",str(objective.target_ids[0]))
		var verb={"capture":"占领","hold":"守住","escort":"抵达","survive":"保全主力","repair":"修复铁路","disembark":"抵达卸载","destroy":"消灭","capture_commander":"俘获或击溃","metric":"战术训练"}.get(objective.type,objective.type)
		if objective.type=="hold" and target.get("owner_id",s.player_faction_id)!=s.player_faction_id:verb="夺取并守住"
		label(mission_card,verb+" "+target_name+"  %d/%d"%[objective.progress,objective.required],16,PAPER)
	if s.mode=="conquest":label(mission_card,"统一战略城市 · 同盟共同结算",16,PAPER)
	elif s.get("round_limit",0)>0:label(mission_card,"期限：第%d回合 · 每完整回合一天"%s.round_limit,14,UI_BRASS)
	label(mission_card,{"clear":"晴","rain":"雨 · 野外移动+1","snow":"雪 · 粮耗增加"}[s.weather.current]+"  /  指挥 %d · 运力 %d"%[f.command_points,f.transport_pool],13,UI_MUTED)
	if slice_work:
		await get_tree().process_frame
		if epoch!=battle_ui_epoch or not is_same(s,match_controller.state) or not is_instance_valid(inspector):return
	clear(inspector)
	var u=StateAccess.find(s,"units",selected_unit_id);var city=StateAccess.find(s,"cities",selected_city_id)
	if not u.is_empty() and VisibilityRules.unit_visible(s,s.player_faction_id,u):unit_details(u,pending.get("type","")=="Attack")
	elif not city.is_empty():city_details(city)
	elif not selected_poi_id.is_empty():
		var points=s.map.get("reference_pois",[]).filter(func(p):return p.id==selected_poi_id)
		if not points.is_empty():geography_details(points[0])
		elif map_view.places.index.has(selected_poi_id):place_details(map_view.places.index[selected_poi_id])
	elif selected_terrain_hex!=null:terrain_details(selected_terrain_hex)
	else:
		label(inspector,"战地指挥",30,BRASS);label(inspector,StateAccess.faction_name(s,s.player_faction_id,content),22)
		label(inspector,"选中一支编队，查看移动范围、攻击目标及战法。",20)
		hud_button(inspector,"选择待命部队",select_next_unit);hud_button(inspector,"外交与援助",show_diplomacy);hud_button(inspector,"作战手册",show_manual)
	map_view.selected_unit_id=selected_unit_id;map_view.selected_city_id=selected_city_id;map_view.pending_hex=HexGrid.coordinate(pending.target_hex) if pending.has("target_hex") else null
	map_view.selected_place_id=selected_poi_id
	map_view.selected_terrain_hex=selected_terrain_hex if u.is_empty() and city.is_empty() and selected_poi_id.is_empty() else null
	map_view.reachable={};map_view.attack_targets={};map_view.command_preview={}
	if not territory_qa_mode:queue_selection_query()
	map_view.queue_redraw();refresh_orders();layout_battle_hud.call_deferred()

func autosave_snapshot(snapshot: Dictionary, slot: String) -> void:
	var token=match_controller.generation
	var job=match_controller.worker.submit("save",snapshot,{"path":saves.root_path,"slot":slot,"presentation":{"facing":match_controller.facing_memory.snapshot()}},content)
	while not job.is_completed():await get_tree().process_frame
	if token==match_controller.generation and not job.result.get("valid",false):toast(job.result.get("reason","自动存档失败"))

func queue_selection_query() -> void:
	var s=match_controller.state
	if s.is_empty() or match_controller.presentation_busy or match_controller.command_busy:return
	if not pending.is_empty():pending.expected_version=s.state_version
	var key=selected_unit_id+"/"+ContentRegistry.fingerprint(pending)
	if is_same(selection_state,s) and key==selection_key:
		if not selection_result.is_empty():apply_selection_query()
		return
	if selection_job!=null:selection_job.cancel()
	selection_state=s;selection_key=key;selection_result={}
	var job=match_controller.worker.submit("selection",s,{"unit_id":selected_unit_id,"pending":pending},content)
	selection_job=job;var token=match_controller.generation
	while token==match_controller.generation and not job.is_completed():await get_tree().process_frame
	if token!=match_controller.generation or selection_job!=job or not is_same(match_controller.state,s) or not is_instance_valid(map_view):return
	selection_job=null;selection_result=job.result
	apply_selection_query();refresh_orders()

func apply_selection_query() -> void:
	if not is_instance_valid(map_view) or selection_result.is_empty():return
	map_view.reachable=selection_result.reachable;map_view.attack_targets=selection_result.attack_targets;map_view.command_preview=selection_result.preview
	if pending.get("type")=="Attack" and map_view.command_preview.get("valid",false):target_preview(map_view.command_preview)
	map_view.queue_redraw()

func unit_details(u: Dictionary, compact: bool = false) -> void:
	var s=match_controller.state;var d=EffectRules.scaled_definition(u,content);var own=u.owner_id==s.player_faction_id
	ui_kicker(inspector,"编队检查器 · %s"%StateAccess.faction_name(s,u.owner_id,content),UI_BRASS)
	var faction_strip=ColorRect.new();faction_strip.color=MapView.TERRITORY_COLORS.get(u.owner_id,Color("788d8f"));faction_strip.custom_minimum_size.y=5;inspector.add_child(faction_strip)
	var portrait=ui_panel(inspector,"ui_order_card",Color.WHITE,4)
	var portrait_height=120 if get_viewport_rect().size.y<850 else 176
	if u.general_id!=null:
		var general_view=GeneralPortraitView.new();general_view.setup(assets,str(u.general_id),Vector2(232,portrait_height),str(s.date));portrait.add_child(general_view)
	else:image_view(portrait,assets.unit_texture(u),Vector2(232,portrait_height))
	label(inspector,content.definition("generals",u.general_id).name if u.general_id!=null else d.name,27,Color("e3cfaa"))
	label(inspector,StateAccess.faction_name(s,u.owner_id,content)+" · "+d.name+" · %d层编制"%u.stack,17)
	label(inspector,"兵力  %d / %d"%[u.hp,u.max_hp],22)
	var health=ProgressBar.new();health.max_value=u.max_hp;health.value=u.hp;health.show_percentage=false;health.custom_minimum_size.y=11
	health.add_theme_stylebox_override("background",box(Color("151d1c"),Color("766950"),0,0));health.add_theme_stylebox_override("fill",box(Color("879c6f") if own else Color("9b4c3e"),Color("879c6f") if own else Color("9b4c3e"),0,0));inspector.add_child(health)
	label(inspector,"攻击  %d      防御  %d"%[d.attack,CombatRules.defense(s,u,content)],20)
	label(inspector,"行动  %d      射程  %d—%d"%[u.ap_left,d.range_min,d.range_max],20)
	label(inspector,"士气 %d  /  压制 %d  /  弹药 %d"%[u.morale,u.suppression,u.ammo],16,Color("b9b095"))
	label(inspector,VeterancyRules.NAMES[VeterancyRules.rank_for(int(u.get("experience",0)))]+" · 战斗经验 %d/80"%int(u.get("experience",0)),15,BRASS)
	label(inspector,"补给"+{"FULL":"充足","LOW":"紧张","NONE":"中断"}[u.supply_state]+" · 储粮%d阶段"%u.food_reserve,17,Color("a3b68c") if u.supply_state=="FULL" else Color("d6aa70"))
	ui_rule(inspector,Color("75684d"))
	if not own or compact:return
	if u.general_id!=null:
		var g=StateAccess.find(s,"generals",u.general_id);var skill=content.definition("skills",GeneralRules.active_skill(g,content))
		hud_button(inspector,skill.name+"  ·  %d指挥"%skill.command_cost,func():order_mode="skill";toast("选择战法目标，再确认命令。"),u.skill_ready and int(g.cooldowns.get(skill.id,0))==0)
	else:hud_button(inspector,"任命将领",func():show_generals(u.id))
	hud_button(inspector,"铁路投送  ·  运力 %d"%StateAccess.faction(s,s.player_faction_id).transport_pool,func():show_rail_destinations(u.id))
	hud_button(inspector,"更多部队命令",func():show_unit_orders(u.id))
	var city=StateAccess.at(s,"cities",HexGrid.coordinate(u.position)) if u.position!=null else {}
	if not city.is_empty():hud_button(inspector,city.name+" · 生产与建设",func():selected_unit_id="";selected_city_id=city.id;pending={};refresh_battle())

func city_details(city: Dictionary) -> void:
	var s=match_controller.state;ui_kicker(inspector,"城市检查器 · %s"%StateAccess.faction_name(s,city.owner_id,content),UI_BRASS);var city_strip=ColorRect.new();city_strip.color=MapView.TERRITORY_COLORS.get(city.owner_id,Color("788d8f"));city_strip.custom_minimum_size.y=5;inspector.add_child(city_strip);label(inspector,city.name,34)
	label(inspector,HistoricalPlaces.kind_label(city,s.date),22,BRASS)
	label(inspector,"当前控制：%s · %d级城市"%[StateAccess.faction_name(match_controller.state,city.owner_id,content),city.level],22)
	label(inspector,"%s年行政归属：%s"%[s.date.substr(0,4),ContentRegistry.administration_name(city,s.date)],19,BRASS)
	label(inspector,"城防 %d/%d · 稳定 %d%%"%[city.fort_hp,city.fort_max_hp,city.stability],21)
	var income=EconomyRules.income(city,content);label(inspector,"阶段收入  %d军费 / %d粮 / %d械"%[income.cash,income.food,income.arms],20)
	label(inspector,"本地兵源 %d"%city.recruit_reserve,20,BRASS)
	ui_rule(inspector,Color("75684d"))
	for b in city.buildings:label(inspector,"%s  %d级%s"%[content.definition("buildings",b.def_id).name,b.level," · 受损" if b.damaged else ""],20)
	if city.owner_id!=s.player_faction_id:return
	button(inspector,"征募部队",func():show_recruit(city.id));button(inspector,"建设与升级设施",func():show_buildings(city.id))
	command_button(inspector,"提升城市等级",match_controller.command("UpgradeCity",{"city_id":city.id}))
	command_button(inspector,"修复城防",match_controller.command("RepairFort",{"city_id":city.id}))
	button(inspector,"军需交易",func():show_trade(city.id))
	if EconomyRules.building_level(city,"airfield")>0:
		button(inspector,"航空侦察",func():order_mode="air_recon";toast("选择机场八格范围内侦察中心"))
		button(inspector,"航空轰炸",func():order_mode="air_bomb";toast("选择已侦察敌军或城防"))
	for q in city.recruit_queue:
		var r=row(inspector);label(r,content.definition("units",q.target_def_id).name+" · "+("待部署" if q.ready else "%d阶段"%q.remaining_own_phases),19);command_button(r,"撤销",match_controller.command("CancelQueue",{"city_id":city.id,"queue_id":q.id,"construction":false}))
	for q in city.construction_queue:
		var r=row(inspector);label(r,("城市升级" if q.target_def_id=="city_level" else content.definition("buildings",q.target_def_id).name)+" · %d阶段"%q.remaining_own_phases,19);command_button(r,"撤销",match_controller.command("CancelQueue",{"city_id":city.id,"queue_id":q.id,"construction":true}))

func terrain_details(hex: Vector2i) -> void:
	var s=match_controller.state;var cell=StateAccess.cell(s,hex)
	if cell.is_empty():return
	var kind=str(cell.terrain_id);var terrain=content.definition("terrains",kind)
	var visual=map_view.presentation_cells.get(hex,cell);var appearance=MapView.TerrainVisuals.kind_for_cell(visual)
	ui_kicker(inspector,"战场地形",UI_MUTED,13);label(inspector,str(terrain.name),30,BRASS)
	var picture={"plain":"tile_plain_01","hill":"tile_hill_01","mountain":"tile_mountain_01","peak":"tile_peak_01","river":"tile_river_01","wetland":"tile_wetland_01","sea":"tile_sea_01","forest":"tile_forest_01"}.get(appearance,"")
	if MapArtBank.available():picture=map_view.map_details.surfaces.get(HexGrid.key(hex),picture)
	if not picture.is_empty():image_view(inspector,assets.texture("tile",picture),Vector2(120,108))
	var ground_name=MapSurfaceRegions.material_label(visual)
	if not ground_name.is_empty():label(inspector,"地表："+ground_name,18,UI_MUTED)
	var natural=str(cell.get("natural_terrain_id",kind))
	if natural!=kind:label(inspector,"自然地貌："+str(content.definition("terrains",natural).get("name",natural)),18)
	if appearance!=kind and visual.has("presentation_terrain_id"):label(inspector,"附近有史料记载的林地 / 湿地",18,UI_MUTED)
	if cell.get("elevation_m")!=null:label(inspector,"采样高程约 %d 米"%roundi(float(cell.elevation_m)),19)
	if cell.get("relief_sample_m")!=null:label(inspector,"格内采样起伏约 %d 米"%roundi(float(cell.relief_sample_m)),18,UI_MUTED)
	ui_rule(inspector)
	for movement in [["步兵","cost_foot"],["骑兵","cost_cavalry"],["车辆","cost_motor"],["舰船","cost_water"]]:
		var cost=int(terrain.get(movement[1],0))
		label(inspector,movement[0]+(" · 地形消耗 %d 行动点"%cost if cost>0 else " · 无法通行"),18)
	label(inspector,"地形掩护  +%d 防御"%int(terrain.get("cover_defense",0)),19,BRASS)
	label(inspector,"天气、敌军控制区和线路状态会进一步影响通行。",16,UI_MUTED)
	button(inspector,"地形图鉴",show_terrain_atlas)
	button(inspector,"返回待命部队",select_next_unit)

func geography_details(poi: Dictionary) -> void:
	var s=match_controller.state;label(inspector,poi.name,34)
	label(inspector,"%s年行政归属：%s"%[s.date.substr(0,4),ContentRegistry.administration_name(poi,s.date)],22,BRASS)
	label(inspector,"地理坐标：%.3f°E / %.3f°N"%[poi.lon_e6/1000000.0,poi.lat_e6/1000000.0],19)
	if poi.poi_reason=="historical_occupation":
		label(inspector,"日军占领青岛。1922年12月10日中方接收。此节点接收前不参与军阀争夺。",22)
		label(inspector,"胶济铁路存在；中方全路路警接管完成前不开放本游戏的军运。",21)
	else:label(inspector,"地方军政地区，保留地理位置与行政归属，当前未列为可争夺节点。",22)
	button(inspector,"返回待命部队",select_next_unit)

func place_details(poi: Dictionary) -> void:
	var s=match_controller.state;label(inspector,poi.name,34)
	label(inspector,HistoricalPlaces.kind_label(poi,s.date)+" · "+poi.get("rank_period","1920—1924"),22,BRASS)
	label(inspector,"民初行政归属："+poi.administration,21)
	label(inspector,poi.note,20)
	var city=map_view.places.control_city(s,poi.at)
	if not city.is_empty():
		label(inspector,"周边战局势力："+StateAccess.faction_name(s,city.owner_id,content),21,BRASS)
		var km=poi.at.distance_to(Vector2(city.render_position[0],city.render_position[1]))*s.map.hex_radius_m/(48.0*1000)
		label(inspector,"邻近据点：%s · 约 %.1f 公里"%[city.name,km],20)
		button(inspector,"定位邻近据点",func():map_view.focus_world(HexGrid.to_world(HexGrid.coordinate(city.position)));selected_poi_id="";selected_city_id=city.id;refresh_battle())
	else:label(inspector,"地方参考节点 · 未列入当前战区据点",20)
	label(inspector,"地理位置约 %.3f°E / %.3f°N"%[poi.longitude,poi.latitude],18)
	label(inspector,"村镇符号表示聚落位置；色块随战局控制变化。",18,Color("74694f"))
	button(inspector,"返回待命部队",select_next_unit)

func on_place_selected(place_id: String) -> void:
	if match_controller.paused or match_controller.presentation_busy or match_controller.command_busy or match_controller.auto_running:return
	if not map_view.places.index.has(place_id):return
	selected_poi_id=place_id;selected_unit_id="";selected_city_id="";pending={};order_mode="";refresh_battle()

func refresh_orders() -> void:
	if not is_instance_valid(orders):return
	var timed=Time.get_ticks_usec()
	var s=match_controller.state
	if s.is_empty():return
	var acting=s.status=="playing" and s.turn_order[s.phase_index]==s.player_faction_id and not match_controller.paused and not match_controller.presentation_busy and not match_controller.auto_running and not match_controller.command_busy
	if (match_controller.presentation_busy or match_controller.command_busy) and is_instance_valid(busy_orders):
		orders.visible=false;busy_orders.visible=true
		busy_auto_start.visible=not match_controller.auto_player;busy_auto_stop.visible=match_controller.auto_player
		busy_skip.visible=match_controller.presentation_busy;busy_animation.visible=match_controller.presentation_busy;busy_planning.visible=not match_controller.presentation_busy
		if "--responsiveness-test" in OS.get_cmdline_user_args():qa_order_timings.append({"kind":"animation" if match_controller.presentation_busy else "planning","reused_controls_us":Time.get_ticks_usec()-timed})
		if battle_hud!=null:battle_hud.refresh_orders()
		return
	orders.visible=true
	if is_instance_valid(busy_orders):busy_orders.visible=false
	clear(orders)
	hud_button(orders,"停止自动" if match_controller.auto_player else "自动作战",func():match_controller.toggle_auto_player();refresh_orders(),s.status=="playing")
	if not pending.is_empty():
		pending.expected_version=s.state_version;var p=selection_result.get("preview",{}) if is_same(selection_state,s) else {}
		var text={"Move":"确认移动","Attack":"确认攻击","ActivateSkill":"确认战法","AirRecon":"确认侦察","AirBomb":"确认轰炸","Disembark":"确认卸载"}.get(pending.type,"执行命令")
		hud_button(orders,text,func():var c=pending.duplicate(true);pending={};order_mode="";match_controller.request_command(c),p.get("valid",false) and acting,p.get("reason","正在核对目标"))
		var description=p.get("reason","")
		if p.get("valid",false):
			if p.has("damage"):description="伤害 %d—%d  ·  反击 %d—%d"%[p.get("damage_min",p.damage),p.get("damage_max",p.damage),p.get("counter_min",p.counter),p.get("counter_max",p.counter)]
			elif p.has("path"):description="消耗 %d 行动点 · 沿路径前进"%p.cost
			else:description="目标与资源已检查"
		label(orders,description,20,BRASS);hud_button(orders,"取消",func():pending={};order_mode="";refresh_battle())
		if battle_hud!=null:battle_hud.refresh_orders()
		return
	var selected_city=StateAccess.find(s,"cities",selected_city_id)
	if not selected_city.is_empty() and selected_city.owner_id==s.player_faction_id:
		hud_button(orders,"征募部队",func():show_recruit(selected_city.id),acting)
		hud_button(orders,"城市建设",func():show_buildings(selected_city.id),acting)
		var repair=match_controller.command("RepairFort",{"city_id":selected_city.id});var repair_check=match_controller.kernel.preview(s,repair)
		hud_button(orders,"修复城防",func():match_controller.request_command(repair),acting and repair_check.get("valid",false),repair_check.get("reason",""))
		hud_button(orders,"待命部队",select_next_unit,acting)
		hud_button(orders,"结束回合  →",request_end_phase,acting)
		if battle_hud!=null:battle_hud.refresh_orders()
		return
	var u=StateAccess.find(s,"units",selected_unit_id);var own=acting and not u.is_empty() and u.owner_id==s.player_faction_id
	hud_button(orders,"移动",func():order_mode="move";toast("蓝色格可达；选择目标格查看路径。"),own and u.get("ap_left",0)>0)
	hud_button(orders,"攻击",func():order_mode="attack";toast("红色标记是合法攻击目标；选择目标查看伤害与反击。"),own and u.get("attack_ready",false) and u.get("ammo",0)>0)
	hud_button(orders,"战法",func():order_mode="skill";toast("选择战法目标格。"),own and u.get("general_id")!=null and u.get("skill_ready",false))
	var c=match_controller.command("Reinforce",{"unit_id":selected_unit_id});var reinforce=selection_result.get("reinforce",{}) if is_same(selection_state,s) else {}
	hud_button(orders,"整补",func():match_controller.request_command(c),acting and reinforce.get("valid",false),reinforce.get("reason",""))
	var undo=match_controller.command("UndoMove");var undo_check=selection_result.get("undo",{}) if is_same(selection_state,s) else {}
	hud_button(orders,"撤销移动",func():match_controller.request_command(undo),acting and undo_check.get("valid",false),undo_check.get("reason",""))
	hud_button(orders,"待命部队",select_next_unit,acting)
	var end=hud_button(orders,"结束回合  →",request_end_phase,acting);end.custom_minimum_size.x=116 if mobile_layout() else 106;end.add_theme_stylebox_override("normal",box(Color(.38,.31,.22,.82),UI_BRASS,0,3))
	if battle_hud!=null:battle_hud.refresh_orders()

func command_button(parent: Node, text: String, c: Dictionary, reason: Label=null) -> Button:
	var control=button(parent,text,func():close_overlay();match_controller.request_command(c),false,"正在核对命令条件")
	if is_instance_valid(reason):control.set_meta("validation_label",reason)
	update_command_button(control,c)
	return control

func update_command_button(control: Button, c: Dictionary) -> void:
	var s=match_controller.state;var token=match_controller.generation
	var job=match_controller.worker.submit("preview",s,c,content)
	while is_instance_valid(control) and token==match_controller.generation and not job.is_completed():await get_tree().process_frame
	if not is_instance_valid(control) or token!=match_controller.generation:job.cancel();return
	if not is_same(s,match_controller.state):control.tooltip_text="战局已经更新，请重新选择";return
	control.disabled=not job.result.get("valid",false);control.tooltip_text=job.result.get("reason","")
	var validation_label=control.get_meta("validation_label") if control.has_meta("validation_label") else null
	if is_instance_valid(validation_label):
		validation_label.text=control.tooltip_text if control.disabled else "条件满足 · 可下达命令"
		validation_label.add_theme_color_override("font_color",Color("915f49") if control.disabled else Color("4e715e"))

func on_hex_selected(hex: Vector2i) -> void:
	if match_controller.presentation_busy or match_controller.paused or match_controller.command_busy:return
	var s=match_controller.state;var cell=StateAccess.cell(s,hex)
	if cell.is_empty():return
	if match_controller.auto_running:return
	selected_terrain_hex=hex
	if pending.has("target_hex") and HexGrid.coordinate(pending.target_hex)==hex:
		var check=selection_result.get("preview",{}) if is_same(selection_state,s) else {}
		if check.get("valid",false):
			var c=pending.duplicate(true);pending={};order_mode="";match_controller.request_command(c);return
	var target=StateAccess.at(s,"units",hex);var city=StateAccess.at(s,"cities",hex);var selected=StateAccess.find(s,"units",selected_unit_id)
	var points=s.map.get("reference_pois",[]).filter(func(p):return HexGrid.coordinate(p.position)==hex)
	if not target.is_empty() and not VisibilityRules.unit_visible(s,s.player_faction_id,target):target={}
	if order_mode in ["air_recon","air_bomb"]:
		pending=match_controller.command("AirRecon" if order_mode=="air_recon" else "AirBomb",{"city_id":selected_city_id,"target_hex":HexGrid.position(hex)})
	elif order_mode=="disembark":pending=match_controller.command("Disembark",{"unit_id":selected_unit_id,"target_hex":HexGrid.position(hex)})
	elif order_mode=="skill" and not selected.is_empty():pending=match_controller.command("ActivateSkill",{"unit_id":selected.id,"target_id":target.get("id",selected.id),"target_hex":HexGrid.position(hex)})
	elif not points.is_empty() and (points[0].poi_reason=="historical_occupation" or selected.is_empty()):
		selected_poi_id=points[0].id;selected_unit_id="";selected_city_id="";pending={}
	elif not target.is_empty() and target.owner_id==s.player_faction_id:
		selected_unit_id=target.id;selected_city_id="";pending={}
	elif order_mode!="move" and not selected.is_empty() and selected.owner_id==s.player_faction_id and ((not target.is_empty() and StateAccess.hostile(s,selected.owner_id,target.owner_id)) or (not city.is_empty() and city.fort_hp>0 and StateAccess.hostile(s,selected.owner_id,city.owner_id))):
		pending=match_controller.command("Attack",{"unit_id":selected.id,"target_hex":HexGrid.position(hex)})
	elif order_mode!="attack" and not selected.is_empty() and target.is_empty() and HexGrid.coordinate(selected.position)!=hex:pending=match_controller.command("Move",{"unit_id":selected.id,"target_hex":HexGrid.position(hex)})
	else:
		selected_unit_id=target.get("id","");selected_city_id=city.get("id","");selected_poi_id="";pending={}
	refresh_battle()

func select_next_unit() -> void:
	var s=match_controller.state;var candidates=s.units.filter(func(u):return u.owner_id==s.player_faction_id and u.position!=null and (u.ap_left>0 or u.attack_ready))
	if candidates.is_empty():toast("所有部队已完成本阶段行动");return
	var index=candidates.find(StateAccess.find(s,"units",selected_unit_id));var u=candidates[(index+1)%candidates.size()]
	selected_unit_id=u.id;selected_city_id="";selected_poi_id="";pending={};order_mode="";map_view.focus_world(HexGrid.to_world(HexGrid.coordinate(u.position)));refresh_battle()

func issue(type: String, arguments: Dictionary = {}) -> void:match_controller.request_command(match_controller.command(type,arguments))

func toast(text: String) -> void:
	if is_instance_valid(notice):notice.text=text
	else:print(text)

func modal(title: String, scroll_content: bool=true) -> VBoxContainer:
	close_overlay();overlay=Control.new();overlay.z_index=100;overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);add_child(overlay)
	if is_instance_valid(match_controller) and not match_controller.state.is_empty() and match_controller.state.status=="playing":match_controller.paused=true
	if is_instance_valid(map_view):map_view.playback_paused=true
	var shade=ColorRect.new();shade.color=Color(0,0,0,.65);shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);overlay.add_child(shade)
	var m=margin(overlay,24);m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var center=CenterContainer.new();m.add_child(center)
	var shell=ui_panel(center,"ui_hud_plate",Color.WHITE,7)
	# Bound the sheet to the actual viewport; the content scrolls independently
	# while the title and Close action remain reachable on touch and large type.
	var insets=safe_insets()
	shell.custom_minimum_size=Vector2(minf(1440*minf(settings.ui_scale,1.25),get_viewport_rect().size.x-48-insets.x-insets.z),minf(880*minf(settings.ui_scale,1.25),get_viewport_rect().size.y-48-insets.y-insets.w))
	var panel=ui_panel(shell,"ui_dialog_frame",Color.WHITE,16)
	panel.set_meta("ui_light",true)
	var v=column(panel);v.set_meta("ui_light",true);var heading=row(v);label(heading,title,34,Color("66533b"));button(heading,"关闭",close_overlay)
	if not scroll_content:
		var content=column(v);content.size_flags_vertical=Control.SIZE_EXPAND_FILL;return content
	return scroll_column(v)

func close_overlay() -> void:
	if is_instance_valid(overlay):
		remove_child(overlay);overlay.queue_free();overlay=null
		if is_instance_valid(match_controller):match_controller.paused=false
		if is_instance_valid(map_view):map_view.playback_paused=false

func show_recruit(city_id: String) -> void:
	war_room.show_recruit(city_id)

func show_legion_deployment(id: String) -> void:
	var recipe=content.scenarios[id];legion_draft={};legion_generals=["wu_peifu","feng_yuxiang"].slice(0,recipe.general_slots)
	for formation in LegionRules.default_army(content,recipe):
		var key=formation.def_id+"@1";legion_draft[key]=int(legion_draft.get(key,0))+1
	var v=modal("军团编组 · "+recipe.name);legion_draft_label=label(v,"",26,BRASS)
	label(v,"按层数与精锐价格支付部署预算，局内军需另行计算。将领、科技与精锐许可使用本题固定配置。",22)
	for choice_id in LegionRules.choices(content,recipe):
		var formation=LegionRules.entry(content,choice_id);var d=EffectRules.scaled_definition(formation,content)
		var name=content.definition("elite_variants",choice_id).name if formation.elite_id!=null else d.name
		var r=row(v);image_view(r,assets.texture("unit","unit_"+choice_id+"_se"),Vector2(90,74));label(r,name,23)
		var layers=OptionButton.new();layers.custom_minimum_size=Vector2(110,96 if mobile_layout() else 64)
		for stack in range(1,int(d.max_stack)+1):layers.add_item("%d层"%stack)
		r.add_child(layers)
		var counter=label(r,"",20)
		var refresh_counter=func():
			var stack=layers.selected+1
			counter.text="%d费 · 已选%d"%[LegionRules.price(content,LegionRules.entry(content,choice_id,stack)),int(legion_draft.get(choice_id+"@"+str(stack),0))]
		layers.item_selected.connect(func(_index):refresh_counter.call())
		button(r,"−",func():change_legion_draft(recipe,choice_id,layers.selected+1,-1);refresh_counter.call())
		button(r,"+",func():change_legion_draft(recipe,choice_id,layers.selected+1,1);refresh_counter.call())
		refresh_counter.call()
	label(v,"将领 · 最多%d位"%recipe.general_slots,27,BRASS)
	for gd in CommanderRoster.training_candidates(content,recipe):
		var checkbox=CheckButton.new();checkbox.text=gd.name;checkbox.custom_minimum_size.y=96 if mobile_layout() else 64;checkbox.button_pressed=legion_generals.has(gd.id);v.add_child(checkbox)
		checkbox.toggled.connect(func(value):
			if value and not legion_generals.has(gd.id):
				if legion_generals.size()<recipe.general_slots:legion_generals.append(gd.id)
				else:checkbox.set_pressed_no_signal(false)
			elif not value:legion_generals.erase(gd.id))
	button(v,"确认部署并开始",func():
		var check=LegionRules.validate(content,recipe,legion_army(),legion_generals)
		if not check.valid:toast(check.reason);return
		start_game(id,recipe.player_default,check.army,check.generals))
	update_legion_draft(recipe)

func legion_army() -> Array:
	var army: Array=[]
	for key in legion_draft:
		for i in range(int(legion_draft[key])):army.append(LegionRules.entry(content,key.get_slice("@",0),int(key.get_slice("@",1))))
	return army

func change_legion_draft(recipe: Dictionary, id: String, stack: int, delta: int) -> void:
	var key=id+"@"+str(stack);var prior=int(legion_draft.get(key,0));legion_draft[key]=maxi(0,prior+delta)
	if delta>0:
		var check=LegionRules.validate(content,recipe,legion_army(),legion_generals,false)
		if not check.valid:legion_draft[key]=prior;toast(check.reason)
	update_legion_draft(recipe)

func legion_spent() -> int:
	var total=0
	for formation in legion_army():total+=LegionRules.price(content,formation)
	return total

func update_legion_draft(recipe: Dictionary) -> void:
	var parts: Array=[]
	var elites=0
	for key in legion_draft:
		if legion_draft[key]<=0:continue
		var formation=LegionRules.entry(content,key.get_slice("@",0),int(key.get_slice("@",1)))
		if formation.elite_id!=null:elites+=int(legion_draft[key])
		var name=content.definition("elite_variants",formation.elite_id).name if formation.elite_id!=null else content.definition("units",formation.def_id).name
		parts.append(name+" %d层×%d"%[formation.stack,legion_draft[key]])
	legion_draft_label.text="部署预算 %d / %d · 精锐 %d / %d\n%s"%[legion_spent(),recipe.deployment_cash_budget,elites,recipe.elite_slots," · ".join(parts)]

func show_buildings(city_id: String) -> void:
	war_room.show_buildings(city_id)

func show_generals(unit_id: String) -> void:
	war_room.show_generals(unit_id)

func show_rail_destinations(unit_id: String) -> void:
	var v=modal("铁路运输 · 区间和车站共同限制运力")
	for city in match_controller.state.cities:
		if EconomyRules.building_level(city,"station")==0:continue
		command_button(v,"运至 "+city.name,match_controller.command("RailTransport",{"unit_id":unit_id,"destination_id":city.id}))

func show_engineer(unit_id: String) -> void:
	var v=modal("铁路工兵 · 靠近线路执行抢修或破坏")
	for edge in match_controller.state.map.rail_edges:
		var r=row(v);label(r,edge.name+" · "+("完整" if edge.damage=="intact" else "受损"),22)
		command_button(r,"抢修",match_controller.command("EngineerWork",{"unit_id":unit_id,"edge_id":edge.id,"action":"repair"}));command_button(r,"破坏",match_controller.command("EngineerWork",{"unit_id":unit_id,"edge_id":edge.id,"action":"demolish"}))
	for job in match_controller.state.engineer_jobs:
		if job.unit_id==unit_id:command_button(v,"取消抢修 · 剩余%d阶段"%job.remaining_own_phases,match_controller.command("CancelWork",{"job_id":job.id}))

func show_embark(unit_id: String) -> void:
	var v=modal("装载到运输船 · 港口相邻格 · 容量3层")
	for ship in match_controller.state.units:
		if ship.def_id=="transport_ship":command_button(v,"运输船 "+ship.id,match_controller.command("Embark",{"unit_id":unit_id,"ship_id":ship.id}))

func show_trade(city_id: String) -> void:
	var v=modal("军需交易 · 每阶段两次 · 出售按半价")
	for resource in ["food","arms"]:
		var r=row(v);label(r,"军粮" if resource=="food" else "军械",28)
		for amount in [10,20,40]:command_button(r,"购买%d"%amount,match_controller.command("Trade",{"city_id":city_id,"resource":resource,"amount":amount,"buy":true}))
		command_button(r,"出售20",match_controller.command("Trade",{"city_id":city_id,"resource":resource,"amount":20,"buy":false}))

func show_diplomacy() -> void:
	war_room.show_diplomacy()

func show_save_dialog(writing: bool) -> void:
	var v=modal("保存战局" if writing else "读取战局")
	var loading=label(v,"正在读取存档记录…",21)
	var job=match_controller.worker.submit("slots",{}, {"path":saves.root_path},content)
	while is_instance_valid(v) and not job.is_completed():await get_tree().process_frame
	if not is_instance_valid(v) or not v.is_inside_tree():job.cancel();return
	v.remove_child(loading);loading.queue_free()
	for slot in job.result.get("slots",[]):
		var r=row(v);label(r,("手动" if slot.id.begins_with("manual") else "自动")+slot.id.get_slice("_",1)+" · "+(slot.saved_at+" · 第%d回合"%slot.round if slot.exists else "空槽"),21)
		if writing and slot.id.begins_with("manual"):button(r,"保存",func():write_match_snapshot(slot.id))
		else:button(r,"读取备份" if slot.backup else "读取",func():load_match_snapshot(slot.id),slot.exists)

func write_match_snapshot(slot: String, return_home: bool = false) -> void:
	if file_operation_pending or match_controller.state.is_empty():return
	file_operation_pending=true;var token=match_controller.generation;toast("正在保存战局…")
	var job=match_controller.worker.submit("save",match_controller.state,{"path":saves.root_path,"slot":slot,"presentation":{"facing":match_controller.facing_memory.snapshot()}},content)
	while not job.is_completed():await get_tree().process_frame
	file_operation_pending=false
	if token!=match_controller.generation:return
	if not job.result.get("valid",false):toast(job.result.get("reason","战局保存失败"));return
	toast("已保存至 "+slot)
	if return_home:match_controller.abandon();show_home()
	else:close_overlay()

func load_match_snapshot(slot: String) -> void:
	if file_operation_pending:return
	file_operation_pending=true;var token=match_controller.generation;toast("正在读取战局…")
	var job=match_controller.worker.submit("load",{}, {"path":saves.root_path,"slot":slot},content)
	while not job.is_completed():await get_tree().process_frame
	file_operation_pending=false
	if token!=match_controller.generation:return
	if not job.result.get("valid",false):toast(job.result.get("reason","战局无法读取"));return
	close_overlay();selected_unit_id="";selected_city_id="";pending={};result_shown=false
	match_controller.load_prepared_state(job.result.state,job.result.get("presentation",{}));build_battle();map_view.focus_player();audio.set_music("campaign")

func show_headquarters() -> void:
	war_room.show_headquarters()

func show_profile_error() -> void:var v=modal("指挥部提示");label(v,profiles.error,26)

func show_general_growth(id: String, age_stage: String="middle") -> void:
	GeneralDossier.show(self,id,age_stage)

func show_achievements() -> void:
	var v=modal("战报与成就 · 成就奖励只领取一次")
	label(v,"已完成 %d / 24 · 获胜 %d局"%[profiles.profile.achievements.size(),profiles.profile.stats.get("wins",0)],26)
	for a in content.tables.achievements:
		var done=profiles.profile.achievements.has(a.id);label(v,("✓ " if done else "○ ")+a.name+" · %d功勋"%a.reward_merit,23,BRASS if done else PAPER)
		var progress=mini(int(a.criterion.value),int(profiles.profile.stats.get(a.criterion.metric,0)))
		label(v,achievement_description(a.criterion.metric)+" · %d / %d"%[progress,a.criterion.value],20,Color("aab49e"))
	label(v,"已获胜任务",27,BRASS)
	for key in profiles.profile.victories:
		var id=key.get_slice(":",0);var name=content.scenarios.get(id,{}).get("name",id)
		label(v,name+" · "+difficulty_name(key.get_slice(":",1))+"  "+"★".repeat(profiles.profile.victories[key]),20)
	label(v,"本机标准化战绩榜 · 按同题同阵营比较",27,BRASS)
	var groups=profiles.ranking_groups()
	if groups.is_empty():label(v,"完成标准化挑战后记录本题成绩。旧版战报保留在生涯中。",20)
	for group in groups:
		label(v,"%s · %s · %s"%[content.scenarios[group.scenario_id].name,difficulty_name(group.difficulty),content.definition("factions",group.faction_id).name],23,BRASS)
		var index=1
		for record in group.records.slice(0,5):
			label(v,"%d. %d回合 · 损失%d · %s"%[index,record.rounds,record.losses,"★".repeat(record.stars)],20);index+=1

func achievement_description(metric: String) -> String:
	return {"first_campaign_win":"赢得战役任务","chapter_1_complete":"完成直皖章不同任务","chapter_2_complete":"完成第一次直奉章不同任务","chapter_3_complete":"完成第二次直奉章不同任务","campaign_three_star_wins":"不同战役取得三星","campaign_all_normal_wins":"普通难度完成不同战役","first_conquest_win":"赢得征服对局","conquest_1920_wins":"赢得1920征服","conquest_1922_wins":"赢得1922征服","conquest_1924_wins":"赢得1924征服","distinct_weak_faction_conquest_wins":"使用不同弱势挑战阵营获胜","normalized_conquest_wins":"标准化挑战赢得不同年代征服","suppressed_target_capture_city":"压制守军后在同回合占城","cavalry_destroyed_artillery":"骑兵击破敌方炮兵编队","fort_breach_then_occupation":"击破敌方城防后占城","protected_observer_artillery_hits":"安全友军观测下的炮兵命中","naval_shore_support_then_capture":"舰炮支援后在同回合占城","general_active_skill_uses":"有效使用将领主动战法","rail_transfers_successful":"完成铁路投送","bridges_repaired":"完成桥梁抢修","rail_cut_changed_enemy_supply":"断路导致敌方编队补给下降","formations_restored_from_none":"断粮编队重新获得完整给养","safe_transport_disembark":"运输船安全卸载编队","legion_challenges_won":"完成不同军团训练"}.get(metric,"完成指定行动")

func difficulty_name(id: String) -> String:return {"normal":"普通","hard":"困难","challenge":"标准化挑战"}.get(id,id)

func show_event_log() -> void:
	var v=modal("前线战报")
	for e in match_controller.state.event_log.slice(-70):
		var text={"CityCaptured":"城市占领","UnitDefeated":"部队损失","UnitWithdrawn":"残军撤离","FactionEliminated":"势力退出战局","UnitMoved":"部队调动","DamageApplied":"交火","RailTransported":"铁路投送","RoundStarted":"新回合","HistoricalEvent":"历史局势","HistoricalEventSkipped":"局势条件未满足","ResourceChanged":"军需账目"}.get(e.type,e.type)
		if e.type=="ResourceChanged":text+=" %s %+d · %s"%[e.resource,e.delta,e.reason]
		elif e.type=="DamageApplied":text+=" %s −%d"%[e.unit_id,e.amount]
		elif e.type=="CombatDiceRolled":text=("反击战况" if e.counter else "攻击战况")+" %d : %d · 伤害%+.1f%%"%[e.attack_die,e.defense_die,(e.modifier_permille-1000)/10.0]
		elif e.type=="UnitPromoted":text="部队晋升 · "+e.name
		elif e.type=="HistoricalEvent":text+=" "+e.name
		elif e.type=="HistoricalEventSkipped":text+=" %s · %s"%[e.name,e.reason]
		elif e.type in ["FactionEliminated","UnitWithdrawn"]:text+=" "+StateAccess.faction_name(match_controller.state,e.owner_id,content)
		label(v,"第%d回合 · %s"%[e.round,text],20)

func show_strategic_map() -> void:
	var v=modal("战略全图 · 点击定位")
	var mini=StrategicMinimap.new();mini.custom_minimum_size=Vector2(900,540);v.add_child(mini);mini.update_map(match_controller.state,content,map_view)
	mini.focused.connect(func(world):map_view.focus_world(world);close_overlay())
	label(v,"城市位置取真实地理坐标；不同阵营以指挥标记颜色区分。",22,BRASS)

func show_manual() -> void:
	var v=modal("作战手册")
	button(v,"地形图鉴 · 20 类区域地表",show_terrain_atlas)
	for item in [["时间与年龄","各参战阵营依次完成本方阶段后，整回合日期前进1天；结束单个阵营阶段不会额外过一天。天气预报、日期事件与人物年龄使用同一公历。将领按当前日期切换青年、壮年、中年、暮年或生前晚期形象；完整生日已核实的记录按生日计算周岁，其余显示约岁。"],["基本操作","鼠标单击选中部队或城市，拖动地图平移，滚轮缩放。Android使用单指点选与拖动、双指缩放。选择目标后在下方确认命令。Tab切换待命部队，空格结束本方阶段，Esc打开暂停。"],["进攻与反击","移动可分段。每部队每阶段一次主攻击，攻击后行动点归零。攻击耗1弹药；反击使用命中后的兵力和压制，每整回合一次，机枪两次。伤害预览显示双方预计损失。"],["城市与城防","先击破城防，再由步兵、骑兵、工兵或装甲车占领空城。炮兵与舰艇不能占领。驻军受到城防实际损失15%的附带伤害；城防未破时不反击。失城会取消当地队列并降低稳定。"],["军需与补员","每本方阶段结算收入、军饷、粮食与弹药。地面补给半径为6移动成本，安全铁路延长覆盖。储粮降至0后持续断粮，第二个断粮阶段起损失兵力。在本方补给城市可消耗兵源和资源补员。"],["铁路与工兵","未行动部队在本方车站可运输，车站池与铁路区间分别限额。敌军控制区或受损轨道阻断运输。工兵靠近线路可修复；桥梁用两阶段，普通线路一阶段。工兵离开时任务暂停。"],["指挥与成长","将领专长、被动、军衔与勋章影响所属部队。主动战法消耗指挥点并有冷却。指挥部科技与将领成长冻结于开局快照。精锐需科技二级，并在战役章节结业后解锁。"],["外交与航空","停战最低3回合，同盟最低6回合，解约有2回合通知。借道运输后本阶段不能宣战。机场只能在剧本允许的城市建造，侦察揭示区域，轰炸消耗弹药、资源与出动数，雨天停飞轰炸。"],["历史与地图","海岸、河流来自真实地理，城市采用真实位置，铁路按年代开放。编队规模、交战部署、天气循环、关卡目标属于游戏抽象。军团挑战是训练题，不声称史实战役。征服首版使用中国东部战区。"]]:
		label(v,item[0],28,BRASS);label(v,item[1],22)

func show_terrain_atlas() -> void:war_room.show_terrain_atlas()

func show_tutorial() -> void:
	var v=modal("前线指挥 · 首次操作")
	label(v,"1  选中本方部队，查看绿色可达格。\n2  选择目标格，在下方确认移动或攻击。\n3  用炮兵摧毁城防，用步兵夺城。\n4  留意粮食、弹药与压制，再结束本方阶段。",26)
	label(v,"桌面：拖动平移、滚轮缩放。手机：单指拖动、双指缩放。",23,BRASS)
	button(v,"开始指挥",func():settings.tutorial=false;saves.write("settings",settings);close_overlay())

func show_pause() -> void:
	match_controller.paused=true;var v=modal("战局暂停")
	button(v,"继续指挥",func():match_controller.paused=false;close_overlay();refresh_battle())
	button(v,"保存战局",func():show_save_dialog(true));button(v,"读取战局",func():show_save_dialog(false));button(v,"设置",show_settings)
	button(v,"保存并返回主菜单",func():write_match_snapshot("auto_1",true))

func show_settings() -> void:
	var v=modal("设置")
	for entry in [["music","音乐"],["sound","音效"],["grid","加深六边格网格"],["tutorial","开局操作引导"],["battle_cinematics","战斗播片与骰子演出"],["reduced_motion","减少震动与位移晃动"]]:
		var cb=CheckButton.new();cb.text=entry[1];cb.button_pressed=settings[entry[0]];cb.custom_minimum_size.y=64;v.add_child(cb);cb.toggled.connect(func(value):settings[entry[0]]=value;apply_audio_settings();saves.write("settings",settings);if is_instance_valid(map_view):map_view.show_grid=settings.grid;map_view.playback.cinematics=settings.battle_cinematics;map_view.playback.reduced_motion=settings.reduced_motion;map_view.queue_redraw())
	for entry in [["music_volume","音乐音量"],["sfx_volume","音效音量"]]:
		label(v,entry[1],24);var slider=HSlider.new();slider.min_value=.01;slider.max_value=1;slider.step=.01;slider.value=settings[entry[0]];slider.custom_minimum_size.y=64;v.add_child(slider);slider.value_changed.connect(func(value):settings[entry[0]]=value;apply_audio_settings();saves.write("settings",settings))
	label(v,"动画速度",24)
	var speed_options=OptionButton.new();speed_options.custom_minimum_size.y=64
	for text in ["慢速 0.5×","标准 1×","快速 2×"]:speed_options.add_item(text)
	var speeds=[.5,1.0,2.0];speed_options.select(speeds.find(float(settings.animation_speed)));v.add_child(speed_options)
	speed_options.item_selected.connect(func(index):settings.animation_speed=speeds[index];audio.action_speed=settings.animation_speed;saves.write("settings",settings);if is_instance_valid(map_view):map_view.playback.speed=settings.animation_speed)
	label(v,"界面字号",24)
	var scale_options=OptionButton.new();scale_options.custom_minimum_size.y=96 if mobile_layout() else 64
	for text in ["100% · 标准","120% · 手机推荐","150% · 大字"]:scale_options.add_item(text)
	var scales=[1.0,1.2,1.5];scale_options.select(scales.find(float(settings.ui_scale)));v.add_child(scale_options)
	scale_options.item_selected.connect(func(index):apply_ui_scale(scales[index]))
	label(v,"所有数据保存在本机。Android退至后台时自动保存战局。",21,Color("aab49e"))

func apply_ui_scale(value: float) -> void:
	var camera=map_view.camera if is_instance_valid(map_view) else Vector2.ZERO;var zoom=map_view.zoom if is_instance_valid(map_view) else 1.0
	settings.ui_scale=value;saves.write("settings",settings);setup_theme();close_overlay()
	if is_instance_valid(map_view):build_battle();map_view.camera=camera;map_view.zoom=zoom;map_view.queue_redraw()
	else:show_home()

func apply_audio_settings() -> void:
	if is_instance_valid(match_controller):match_controller.presentation_options={"cinematics":settings.battle_cinematics,"reduced_motion":settings.reduced_motion}
	if not is_instance_valid(audio):return
	audio.enabled=settings.sound;audio.music_enabled=settings.music;audio.sfx_volume=settings.sfx_volume;audio.music_volume=settings.music_volume;audio.action_speed=settings.animation_speed
	if not audio.current_music.is_empty():audio.set_music(audio.current_music)

func show_result() -> void:
	if result_shown or match_controller.state.is_empty():return
	result_shown=true;var s=match_controller.state;var reward=profiles.settle(s);var v=modal("胜利 · "+"★".repeat(s.result_stars) if s.status=="won" else "任务结束")
	label(v,s.get("result_reason",""),32);label(v,"第%d回合 · 夺城%d · 击败%d · 损失%d"%[s.round,s.metrics.captures,s.metrics.kills,s.metrics.losses],24)
	label(v,"本次奖励：%d功勋 / %d研究"%[reward.merit,reward.research],26,BRASS)
	if reward.has("error"):label(v,"奖励保存失败："+reward.error,22)
	button(v,"返回主菜单",func():match_controller.abandon();show_home());button(v,"再战一次",func():start_game(s.scenario_id,s.player_faction_id))

func on_resize() -> void:
	if is_instance_valid(map_view):layout_battle_hud.call_deferred();map_view.queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:
			if is_instance_valid(overlay):close_overlay()
			elif battle_hud!=null and battle_hud.dismiss_drawer():pass
			elif not pending.is_empty():pending={};order_mode="";refresh_battle()
			elif not match_controller.state.is_empty():show_pause()
		elif event.keycode==KEY_SPACE and not match_controller.state.is_empty() and not is_instance_valid(overlay):
			if match_controller.presentation_busy:map_view.playback.skip()
			else:request_end_phase()
		elif event.keycode==KEY_TAB and not match_controller.state.is_empty() and not is_instance_valid(overlay) and not match_controller.presentation_busy:select_next_unit();get_viewport().set_input_as_handled()
		elif event.keycode==KEY_R and not selected_unit_id.is_empty() and not is_instance_valid(overlay):show_rail_destinations(selected_unit_id)
		elif event.keycode==KEY_G and not selected_unit_id.is_empty() and not is_instance_valid(overlay):show_generals(selected_unit_id)
		elif event.keycode==KEY_F and is_instance_valid(map_view) and not is_instance_valid(overlay):map_view.show_supply=not map_view.show_supply;map_view.queue_redraw()
		elif event.keycode==KEY_M and is_instance_valid(map_view) and not is_instance_valid(overlay):show_strategic_map()

func _exit_tree() -> void:
	if assets!=null:assets.finish_map_prefetch()

func _notification(what: int) -> void:
	if what==NOTIFICATION_APPLICATION_PAUSED and is_instance_valid(match_controller) and not match_controller.state.is_empty():
		background_was_paused=match_controller.paused;match_controller.paused=true
		# Android may suspend frames immediately. Complete this serialized disk
		# write before returning the lifecycle notification, outside active play.
		var job=match_controller.worker.submit("save",match_controller.state,{"path":saves.root_path,"slot":"auto_1"},content)
		while not job.is_completed():OS.delay_msec(1)
		if not job.result.get("valid",false):toast(job.result.get("reason","后台存档失败"))
	if what==NOTIFICATION_APPLICATION_RESUMED and is_instance_valid(match_controller):match_controller.paused=background_was_paused
	if what==NOTIFICATION_WM_CLOSE_REQUEST:
		finish_window_close()

func finish_window_close() -> void:
	if exit_requested:return
	exit_requested=true
	if is_instance_valid(match_controller) and not match_controller.state.is_empty():
		var was_paused=match_controller.paused;match_controller.paused=true
		var job=match_controller.worker.submit("save",match_controller.state,{"path":saves.root_path,"slot":"auto_1"},content)
		while not job.is_completed():await get_tree().process_frame
		if not job.result.get("valid",false):
			exit_requested=false;match_controller.paused=was_paused;toast(job.result.get("reason","退出前存档失败，请重试"));return
	get_tree().quit()

func capture_frame() -> void:
	close_overlay();await get_tree().process_frame;await get_tree().process_frame
	var args=OS.get_cmdline_user_args()
	if is_instance_valid(map_view) and "--atlas-view" in args:
		map_view.fit_map()
	if is_instance_valid(map_view) and not qa_save_path.is_empty() and "--capture-grid" in args:
		# Exercise the actual optional operation-grid layer in isolated QA only.
		map_view.show_grid=true;map_view.queue_redraw()
	if is_instance_valid(map_view) and "--focus-city" in args:
		var index=args.find("--focus-city")
		if index+1<args.size():
			for city in match_controller.state.cities+match_controller.state.map.get("reference_pois",[]):
				if city.id==args[index+1]:map_view.camera=HexGrid.to_world(HexGrid.coordinate(city.position));map_view.clamp_camera();map_view.queue_redraw();break
	if is_instance_valid(map_view) and "--focus-point" in args:
		# QA-only presentation camera. This accepts a world-space `x,y` pair so
		# authored terrain landmarks can be inspected without inventing a city,
		# changing a cell, or changing any scenario rule data.
		var index=args.find("--focus-point")
		if index+1<args.size():
			var parts=args[index+1].split(",")
			if parts.size()>=2 and parts[0].is_valid_float() and parts[1].is_valid_float():
				map_view.camera=Vector2(float(parts[0]),float(parts[1]));map_view.clamp_camera();map_view.queue_redraw()
	if is_instance_valid(map_view) and "--inspect-city" in args:
		var index=args.find("--inspect-city")
		if index+1<args.size():
			var id=args[index+1];var nodes=match_controller.state.cities+match_controller.state.map.get("reference_pois",[])
			for node in nodes:
				if node.id==id:on_hex_selected(HexGrid.coordinate(node.position));break
	if is_instance_valid(map_view) and "--focus-place" in args:
		var index=args.find("--focus-place")
		if index+1<args.size() and map_view.places.index.has(args[index+1]):map_view.camera=map_view.places.index[args[index+1]].at;map_view.clamp_camera();map_view.queue_redraw()
	if is_instance_valid(map_view) and "--capture-zoom" in args:
		var index=args.find("--capture-zoom")
		if index+1<args.size():map_view.zoom=clampf(float(args[index+1]),.10,2.20);map_view.clamp_camera();map_view.queue_redraw()
	if is_instance_valid(map_view) and "--inspect-place" in args:
		var index=args.find("--inspect-place")
		if index+1<args.size():on_place_selected(args[index+1])
	await RenderingServer.frame_post_draw
	var path="res://reports/screenshots/battle.png" if is_instance_valid(map_view) else "res://reports/screenshots/menu.png"
	if "--capture-path" in args:path=args[args.find("--capture-path")+1]
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var error=get_viewport().get_texture().get_image().save_png(path)
	var metadata=FileAccess.open(path.get_basename()+".json",FileAccess.WRITE)
	if metadata:
		var facts={"viewport":get_viewport_rect().size,"window":DisplayServer.window_get_size(),"ui_scale":settings.ui_scale,"mobile_layout_profile":mobile_layout(),"physical_android_device_tested":OS.has_feature("android"),"safe_insets":safe_insets(),"scenario_id":match_controller.state.get("scenario_id",""),"content_hash":content.content_hash,"build_version":ContentRegistry.APP_VERSION,"raw_godot_capture":true,"qa_save_isolated":not qa_save_path.is_empty(),"map_zoom":map_view.zoom if is_instance_valid(map_view) else 0.0,"relief":map_view.relief.diagnostics if is_instance_valid(map_view) else {},"city_labels":map_view.capture_labels() if is_instance_valid(map_view) else []}
		if is_instance_valid(map_view):facts["map_bank"]=map_view.map_details.diagnostics
		if is_instance_valid(map_view):facts["map_bank_visible"]=map_view.map_bank_capture_facts()
		if is_instance_valid(map_view):facts["map_composition"]=map_view.map_composition_facts()
		if is_instance_valid(map_view):
			var terrain_counts={}
			for cell in match_controller.state.map.get("cells",[]):
				var kind=str(cell.get("terrain_id",cell.get("natural_terrain_id","plain")))
				terrain_counts[kind]=int(terrain_counts.get(kind,0))+1
			var backdrop_tile_count=map_view.backdrop_view.terrain_tile_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_surface_variant_count=map_view.backdrop_view.terrain_surface_variant_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_depth_count=map_view.backdrop_view.terrain_depth_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_symbol_count=map_view.backdrop_view.terrain_symbol_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_micro_symbol_count=map_view.backdrop_view.terrain_micro_symbol_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_feature_sprite_count=map_view.backdrop_view.terrain_feature_sprite_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_cell_river_count=map_view.backdrop_view.terrain_cell_river_draw_count if is_instance_valid(map_view.backdrop_view) else 0
			var backdrop_landcover_patch_count=map_view.backdrop_view.historical_landcover_patch_cells if is_instance_valid(map_view.backdrop_view) else 0
			var presentation_terrain_counts={}
			for bucket in map_view.terrain_visual_buckets.values():
				for entry in bucket:
					var visual_kind=str(entry.get("kind","plain"));presentation_terrain_counts[visual_kind]=int(presentation_terrain_counts.get(visual_kind,0))+1
			facts["map_detail"]={"terrain_cell_counts":terrain_counts,"presentation_terrain_counts":presentation_terrain_counts,"terrain_layer_visible":map_view.show_terrain,"control_layer_visible":map_view.show_control,"crossing_markers":map_view.crossing_markers.size(),"river_lines":map_view.river_lines.size(),"detail_hydrography_lines":map_view.detail_river_lines.size(),"cell_river_segments":maxi(map_view.terrain_cell_river_draw_count,backdrop_cell_river_count),"coast_lines":map_view.coast_lines.size(),"rail_edges":match_controller.state.map.get("rail_edges",[]).size(),"terrain_tile_draw_count":maxi(map_view.terrain_tile_draw_count,backdrop_tile_count),"terrain_surface_variant_draw_count":maxi(map_view.terrain_surface_variant_draw_count,backdrop_surface_variant_count),"terrain_depth_draw_count":maxi(map_view.terrain_depth_draw_count,backdrop_depth_count),"terrain_symbol_draw_count":maxi(map_view.terrain_symbol_draw_count,backdrop_symbol_count),"terrain_micro_symbol_draw_count":maxi(map_view.terrain_micro_symbol_draw_count,backdrop_micro_symbol_count),"terrain_feature_sprite_draw_count":maxi(map_view.terrain_feature_sprite_draw_count,backdrop_feature_sprite_count),"historical_landcover_features":map_view.historical_landcover_features.size(),"historical_landcover_patch_cells":maxi(map_view.historical_landcover_patch_cells,backdrop_landcover_patch_count),"territory_field_opacity":MapView.TERRITORY_FIELD_OPACITY,"tactical_zone_opacity":MapView.TERRITORY_OPACITY}
			var place_catalog=HistoricalPlaces.data().get("maps",{})
			var additional_markers=place_catalog.get(map_view.places.map_key,{}).get("markers",[]).size()
			facts["historical_places"]={"additional_markers":additional_markers,"total_nodes":map_view.places.nodes.size(),"selected_id":selected_poi_id,"selected_kind":HistoricalPlaces.kind_label(map_view.places.index[selected_poi_id],match_controller.state.date) if map_view.places.index.has(selected_poi_id) else "","control_zones":map_view.places.zones.size(),"ownership":map_view.places.owners,"control_overlay_visible":map_view.show_control,"place_overlay_visible":map_view.show_places,"presentation_data_sha256":FileAccess.get_sha256("res://presentation/data/settlements_v023.json"),"historic_military_border_claimed":false}
			facts["territory_field"]=map_view.territory_field_diagnostics
			facts["control_land_clip"]=map_view.places.control_clip_diagnostics
			# Capture evidence for the authored cardinal facing layer. This is a
			# read-only presentation audit: it reports which immutable Sub2 source
			# views are available and the final world heading used by each formation;
			# it never changes the authoritative unit or movement state.
			var directional_assets: Dictionary={}
			var heading_records: Array=[]
			for unit in match_controller.state.get("units",[]):
				var unit_key: String=str(unit.get("elite_id") if unit.get("elite_id")!=null else unit.get("def_id",""))
				var available: Array=[]
				for direction in ["n","e","s","w"]:
					if assets.texture("unit","unit_%s_%s"%[unit_key,direction])!=null:available.append(direction)
				directional_assets[unit_key]=available
				var heading: Vector2=map_view.unit_headings.get(str(unit.get("id","")),Vector2.ZERO)
				heading_records.append({"unit_id":str(unit.get("id","")),"source_unit":unit_key,"available_cardinals":available,"heading":[heading.x,heading.y]})
			facts["unit_facing"]={"directional_source_families":directional_assets.size(),"directional_source_views":directional_assets.values().reduce(func(total,value):return int(total)+value.size(),0),"records":heading_records,"compact_idle_chevrons":true}
		metadata.store_string(JSON.stringify(facts,"\t"));metadata.close()
	print("Captured actual Godot viewport: ",path," status ",error);get_tree().quit(0 if error==OK else 1)

func benchmark() -> void:
	close_overlay()
	if not is_instance_valid(map_view):start_game("campaign_1920_01","zhili");close_overlay()
	select_next_unit()
	for i in range(60):await RenderingServer.frame_post_draw
	var frame_ms: Array=[];var previous=Time.get_ticks_usec()
	for i in range(180):
		await RenderingServer.frame_post_draw
		var now=Time.get_ticks_usec();frame_ms.append((now-previous)/1000.0);previous=now
	var ordered=frame_ms.duplicate();ordered.sort();var total=0.0
	for value in frame_ms:total+=value
	var report={"platform":OS.get_name(),"renderer":RenderingServer.get_current_rendering_method(),"gpu":RenderingServer.get_video_adapter_name(),"viewport":get_viewport_rect().size,"window":DisplayServer.window_get_size(),"ui_scale":settings.ui_scale,"mobile_layout_profile":mobile_layout(),"physical_android_device_tested":OS.has_feature("android"),"safe_insets":safe_insets(),"scenario_id":match_controller.state.scenario_id,"content_hash":content.content_hash,"sample_frames":frame_ms.size(),"frame_ms_p95":ordered[int(ordered.size()*.95)],"average_fps":1000.0/(total/frame_ms.size()),"frame_cap":Engine.max_fps,"measurement":"静止战场渲染，实际桌面窗口；不代表 Android 真机帧率"}
	var args=OS.get_cmdline_user_args();var path="res://reports/desktop_benchmark.json"
	if "--benchmark-path" in args and args.find("--benchmark-path")+1<args.size():path=args[args.find("--benchmark-path")+1]
	DirAccess.make_dir_recursive_absolute(path.get_base_dir());var file=FileAccess.open(path,FileAccess.WRITE)
	if file:file.store_string(JSON.stringify(report,"\t"));file.close()
	print("BENCHMARK ",JSON.stringify(report));await capture_frame()

func ui_smoke() -> void:
	close_overlay();await get_tree().process_frame
	if not is_instance_valid(map_view):start_game("campaign_1920_01","zhili");close_overlay()
	select_next_unit();await get_tree().process_frame
	show_recruit(match_controller.state.cities[0].id);await get_tree().process_frame;close_overlay()
	show_buildings(match_controller.state.cities[0].id);await get_tree().process_frame;close_overlay()
	show_diplomacy();await get_tree().process_frame;close_overlay()
	show_pause();await get_tree().process_frame;close_overlay()
	map_view.focus_player();print("UI_SMOKE_PASS");capture_frame()

func ui_nodes(parent: Node) -> Array:
	var result: Array=[]
	for child in parent.get_children():result.append(child);result.append_array(ui_nodes(child))
	return result

func capture_ui(path: String, surface: String="legion_deployment") -> bool:
	await get_tree().process_frame;await get_tree().process_frame;await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var error=get_viewport().get_texture().get_image().save_png(path)
	var metadata=FileAccess.open(path.get_basename()+".json",FileAccess.WRITE)
	if metadata:metadata.store_string(JSON.stringify({"viewport":get_viewport_rect().size,"window":DisplayServer.window_get_size(),"ui_scale":settings.ui_scale,"mobile_layout_profile":mobile_layout(),"physical_android_device_tested":OS.has_feature("android"),"content_hash":content.content_hash,"build_version":ContentRegistry.APP_VERSION,"raw_godot_capture":true,"qa_save_isolated":not qa_save_path.is_empty(),"surface":surface},"\t"));metadata.close()
	return error==OK

func progression_ui_smoke() -> void:
	await get_tree().process_frame
	show_legion_deployment("legion_12");await get_tree().process_frame
	var selected_row: Node
	for node in ui_nodes(overlay):
		if node is HBoxContainer and node.get_children().any(func(child):return child is Label and child.text=="炮兵教导队"):selected_row=node;break
	if not is_instance_valid(selected_row):push_error("Precision artillery draft row missing");get_tree().quit(1);return
	var selector=selected_row.get_children().filter(func(n):return n is OptionButton)[0]
	selector.select(1);selector.item_selected.emit(1)
	var plus=selected_row.get_children().filter(func(n):return n is Button and n.text=="+")[0];plus.pressed.emit()
	if mobile_layout() and (plus.size.x<96 or plus.size.y<96 or selector.size.y<96):push_error("Mobile draft controls are too small");get_tree().quit(1);return
	var check=LegionRules.validate(content,content.scenarios.legion_12,legion_army(),legion_generals)
	if not check.valid or check.elite_count!=1 or not check.army.any(func(u):return u.elite_id=="elite_artillery" and u.stack==2):push_error("Draft controls failed to add the selected elite stack");get_tree().quit(1);return
	var args=OS.get_cmdline_user_args();var path="res://reports/screenshots/legion_deployment_windows.png"
	if "--capture-path" in args:path=args[args.find("--capture-path")+1]
	if not await capture_ui(path):get_tree().quit(1);return
	var confirm=ui_nodes(overlay).filter(func(n):return n is Button and n.text=="确认部署并开始")[0];confirm.pressed.emit()
	await get_tree().process_frame;close_overlay()
	var state=match_controller.state
	if state.get("scenario_id","")!="legion_12" or not state.units.any(func(u):return u.owner_id==state.player_faction_id and u.elite_id=="elite_artillery" and u.stack==2):push_error("Confirmed elite draft did not reach the live battle");get_tree().quit(1);return
	show_achievements();await get_tree().process_frame
	var condition_labels=ui_nodes(overlay).filter(func(n):return n is Label and content.tables.achievements.any(func(a):return n.text.begins_with(achievement_description(a.criterion.metric)+" · ") and n.text.contains(" / ")))
	if condition_labels.size()!=24:push_error("Achievement progress labels missing");get_tree().quit(1);return
	var report={"passed":true,"content_hash":content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"viewport":get_viewport_rect().size,"ui_scale":settings.ui_scale,"physical_android_device_tested":OS.has_feature("android"),"controls_exercised":["layer_selector","elite_add","confirm_deployment"],"elite_id":"elite_artillery","stack":2,"deployment_spent":state.legion_deployment.spent,"achievement_conditions_visible":condition_labels.size(),"capture":path}
	var file=FileAccess.open(path.get_basename()+"_validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("PROGRESSION_UI_PASS ",JSON.stringify(report));get_tree().quit()

func hud_button(parent: Node, text: String, action: Callable, enabled: bool = true, tooltip: String = "") -> Button:
	var card_context=parent==orders or parent==busy_orders or parent.has_meta("hud_header") or parent.has_meta("hud_layers")
	if not card_context:
		var plain=button(parent,text,action,enabled,tooltip);plain.add_theme_font_size_override("font_size",int(17*settings.ui_scale));plain.custom_minimum_size.y=96 if mobile_layout() else 44;return plain
	var b=CommandCard.new();b.text=text;b.clip_text=true;b.caption_font=assets.font;b.caption_size=int(16*minf(1.3,float(settings.ui_scale)));b.disabled=not enabled;b.tooltip_text=tooltip
	b.add_theme_font_override("font",assets.font);b.add_theme_font_size_override("font_size",b.caption_size)
	b.custom_minimum_size=Vector2(96,96) if mobile_layout() else Vector2(82,88)*minf(1.25,float(settings.ui_scale))
	if parent.has_meta("hud_header") and not mobile_layout():b.custom_minimum_size=Vector2(66,66)*minf(1.25,float(settings.ui_scale))
	var artwork_id=""
	if text.contains("征募"):artwork_id="icon_inf_focus"
	elif text.contains("建设"):artwork_id="icon_field_repair"
	elif text.contains("城防"):artwork_id="icon_entrench_order"
	for key in ["移动","攻击","战法","整补","待命","铁路","补给","势力","地形","地名","全图","结束","外交","设置","自动","演出","战报","存档"]:
		if text.contains(key):
			artwork_id={"移动":"icon_order_move","攻击":"icon_order_attack","战法":"icon_order_tactics","整补":"icon_order_reinforce","待命":"icon_defense","铁路":"icon_rail_priority","补给":"icon_ration_order","势力":"icon_defense","地形":"icon_recon_order","地名":"icon_recon_order","全图":"icon_logistics","结束":"icon_command_endphase","外交":"icon_command_diplomacy","设置":"icon_command_pause","自动":"icon_assault_order","演出":"icon_order_move","战报":"icon_recon_order","存档":"icon_field_repair"}[key];break
	if not artwork_id.is_empty() and ResourceLoader.exists("res://assets/icon/"+artwork_id+".png"):b.artwork=assets.texture("icon",artwork_id)
	if ResourceLoader.exists("res://assets/ui/ui_action_hex.png"):b.badge=assets.texture("ui","ui_action_hex")
	b.short_caption={"结束回合  →":"结束回合","待命部队":"待命部队","跳过演出  »":"跳过演出","撤销移动":"撤销移动"}.get(text,text)
	b.add_theme_stylebox_override("normal",box(Color(.10,.14,.16,.58),Color(.38,.43,.43,.22),0,3))
	b.add_theme_stylebox_override("hover",box(Color(.24,.28,.27,.92),UI_BRASS,0,3))
	b.add_theme_stylebox_override("pressed",box(Color(.16,.20,.19,.95),UI_BRASS_BRIGHT,0,3))
	b.add_theme_stylebox_override("disabled",box(Color(.09,.12,.14,.18),Color(.35,.4,.4,.12),0,3))
	b.add_theme_stylebox_override("focus",StyleBoxEmpty.new())
	b.pressed.connect(func():audio.play("ui_select") if is_instance_valid(audio) else null;action.call())
	parent.add_child(b);return b

func show_battle_briefing() -> void:
	var v=modal("作战简报");var s=match_controller.state
	label(v,content.scenarios[s.scenario_id].name,30);label(v,"推演日期 "+s.date,22)
	label(v,"先用炮兵破防、机枪压制，再由步骑夺取车站；抢修线路后调动预备队。",23)
	for event in s.authored_events:
		if not event.get("fired",false) and s.date>=event.get("forecast_date",event.get("date","9999-12-31")):label(v,event.get("date","")+" · "+event.name,22,BRASS)
	label(v,"天气预报："+" / ".join(s.weather.forecast.map(func(x):return "第%d回合 %s"%[x.round,{"clear":"晴","rain":"雨","snow":"雪"}[x.weather]])),21)

func show_unit_orders(id: String) -> void:
	var u=StateAccess.find(match_controller.state,"units",id)
	if u.is_empty():return
	var v=modal("编队命令 · "+content.definition("units",u.def_id).name)
	command_button(v,"补充兵员",match_controller.command("Reinforce",{"unit_id":id}))
	if u.general_id!=null:command_button(v,"解除将领任命",match_controller.command("UnassignGeneral",{"unit_id":id}))
	if u.def_id=="engineer":button(v,"铁路抢修 / 破坏",func():show_engineer(id))
	if u.def_id=="transport_ship":
		for passenger in match_controller.state.units:
			if passenger.cargo_parent_id==id:button(v,"卸载："+content.definition("units",passenger.def_id).name,func():close_overlay();selected_unit_id=passenger.id;order_mode="disembark";toast("选择相邻港口陆格卸载"))
	else:button(v,"装载到运输船",func():show_embark(id))
	label(v,"补给优先级",20)
	for priority in [0,1,2]:button(v,["低","中","高"][priority],func():close_overlay();issue("SetSupplyPriority",{"unit_id":id,"priority":priority}))

func target_preview(preview: Dictionary) -> void:
	var s=match_controller.state;var target=StateAccess.find(s,"units",str(preview.get("target_id")));var city=StateAccess.find(s,"cities",str(preview.get("city_id")))
	if is_instance_valid(target_card) and target_card.get_parent()!=null:target_card.get_parent().remove_child(target_card);target_card.queue_free()
	var card=PanelContainer.new();card.add_theme_stylebox_override("panel",box(Color("d9c69e"),Color("735c3d"),0,10));inspector.add_child(card);var v=column(card)
	target_card=card
	label(v,"目标 · "+(city.name if not city.is_empty() else content.definition("units",target.get("def_id","")).get("name","编队")),19,INK)
	if not city.is_empty():label(v,"城防 %d / %d"%[city.fort_hp,city.fort_max_hp],17,INK)
	if not target.is_empty():label(v,"兵力 %d / %d"%[target.hp,target.max_hp],17,INK)
	label(v,"预计伤害 %d—%d"%[preview.damage_min,preview.damage_max],25,Color("7b302b"))
	if preview.fort_damage>0:label(v,"破防 %d—%d"%[preview.fort_damage_min,preview.fort_damage_max],18,INK)
	label(v,"反击风险 %d—%d"%[preview.counter_min,preview.counter_max],17,INK)
	label(v,"骰差影响火力 ±17.5%",14,Color("6c5c44"))

func request_end_phase() -> void:
	var s=match_controller.state
	if s.is_empty() or match_controller.paused or match_controller.presentation_busy or match_controller.command_busy or s.turn_order[s.phase_index]!=s.player_faction_id:return
	var remaining=s.units.filter(func(u):return u.owner_id==s.player_faction_id and u.position!=null and (u.ap_left>0 or u.attack_ready))
	if remaining.is_empty():pending={};issue("EndPhase");return
	var v=modal("结束本方回合")
	label(v,"还有 %d 支编队能够行动。结束后由其他势力依次行动。"%remaining.size(),24)
	button(v,"继续部署",close_overlay);button(v,"确认结束回合",func():close_overlay();pending={};issue("EndPhase"))
