class_name BattleHUD
extends RefCounted

# Battlefield controls use real commands and source portraits. This class owns
# presentation only: opening a drawer never advances a turn or mutates a match.
var app
var rail: VBoxContainer
var objective_button: Button
var selection: Button
var extras_shell: PanelContainer
var extras: VBoxContainer
var details_open=false
var objectives_open=false
var layers_open=false
var extras_open=false
var summary_key=""
var selection_title="战地指挥"

func setup(scene) -> void:
	app=scene
	for panel in [app.header_shell,app.inspector_shell,app.mission_shell,app.layer_shell]:
		panel.add_theme_stylebox_override("panel",plate())
	app.footer_shell.add_theme_stylebox_override("panel",StyleBoxEmpty.new())
	app.header_shell.anchor_right=0
	app.footer_shell.anchor_left=0;app.footer_shell.anchor_right=0
	app.footer_shell.anchor_top=0;app.footer_shell.anchor_bottom=0
	app.inspector_shell.visible=false;app.mission_shell.visible=false;app.layer_shell.visible=false
	wrap_drawer(app.inspector_shell,"详细档案",func():toggle_details())
	wrap_drawer(app.mission_shell,"作战目标",func():toggle_objectives())
	app.map_view.minimap.hide()
	app.map_view.show_legends=false
	app.orders.add_theme_constant_override("h_separation",6)
	app.notice.add_theme_font_size_override("font_size",int(14*text_scale()))
	app.notice.autowrap_mode=TextServer.AUTOWRAP_OFF
	app.notice.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS
	var notice_style=StyleBoxFlat.new();notice_style.bg_color=Color(.08,.13,.16,.86);notice_style.set_content_margin_all(4)
	app.notice.add_theme_stylebox_override("normal",notice_style)
	app.notice.add_theme_color_override("font_color",Color("d4ded5"))
	rail=VBoxContainer.new();rail.name="BattleUtilities";rail.z_index=31
	rail.add_theme_constant_override("separation",5);rail.set_meta("hud_header",true);app.screen.add_child(rail)
	for item in [["设置",app.show_pause],["战报",app.show_event_log],["全图",app.show_strategic_map],["图层",toggle_layers],["军令",toggle_extras]]:
		var control=app.hud_button(rail,item[0],item[1]);control.name="Utility_"+item[0]
		if item[0] in ["图层","军令"]:control.artwork=app.assets.texture("icon","icon_recon_order" if item[0]=="图层" else "icon_order_tactics")
		style_command(control,true)
	objective_button=app.button(app.screen,"作战目标",toggle_objectives)
	objective_button.name="BattleObjectives";objective_button.z_index=31
	objective_button.alignment=HORIZONTAL_ALIGNMENT_LEFT
	objective_button.add_theme_stylebox_override("normal",plate())
	selection=Button.new();selection.name="BattleSelection";selection.z_index=31
	selection.add_theme_stylebox_override("normal",plate())
	selection.add_theme_stylebox_override("hover",plate(Color(.16,.23,.25,.97)))
	selection.add_theme_stylebox_override("pressed",plate(Color(.10,.16,.18,.97)))
	selection.pressed.connect(func():app.audio.play("ui_select");toggle_details())
	app.screen.add_child(selection)
	extras_shell=PanelContainer.new();extras_shell.name="BattleAdditionalOrders";extras_shell.z_index=32
	extras_shell.add_theme_stylebox_override("panel",plate());app.screen.add_child(extras_shell)
	extras=VBoxContainer.new();extras.add_theme_constant_override("separation",4);extras_shell.add_child(extras)
	rebuild_layers()
	app.map_view.label_obstacle_controls.append_array([rail,objective_button,selection,extras_shell])
	app.map_view.label_obstacle_controls.erase(app.map_view.minimap)

func text_scale() -> float:return float(app.settings.ui_scale)
func scale() -> float:return minf(1.25,text_scale())

func plate(fill: Color=Color(.08,.13,.16,.90)) -> StyleBoxFlat:
	var style=StyleBoxFlat.new();style.bg_color=fill
	style.border_color=Color(.66,.66,.53,.65);style.set_border_width_all(1)
	style.border_width_top=2;style.set_content_margin_all(8)
	style.shadow_color=Color(0,0,0,.22);style.shadow_size=5;style.shadow_offset=Vector2(0,2)
	return style

func line(parent: Node, text: String, font_size: int, color: Color=Color("e8e7d8")) -> Label:
	var label=Label.new();label.text=text;label.add_theme_font_override("font",app.assets.font)
	label.add_theme_font_size_override("font_size",int(font_size*text_scale()))
	label.add_theme_color_override("font_color",color);label.autowrap_mode=TextServer.AUTOWRAP_OFF
	label.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS;label.tooltip_text=text
	label.size_flags_horizontal=Control.SIZE_EXPAND_FILL;label.mouse_filter=Control.MOUSE_FILTER_IGNORE
	parent.add_child(label);return label

func wrap_drawer(panel: PanelContainer, title: String, close: Callable) -> void:
	var scroll=panel.get_child(0);panel.remove_child(scroll)
	var body=VBoxContainer.new();panel.add_child(body)
	var heading=HBoxContainer.new();body.add_child(heading)
	line(heading,title,18,Color("ddce9e"))
	var button=app.button(heading,"关闭",close);button.custom_minimum_size=Vector2(64,48)*scale()
	button.add_theme_font_size_override("font_size",int(15*text_scale()))
	body.add_child(scroll);scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL

func refresh_header(state: Dictionary, faction: Dictionary) -> void:
	app.clear(app.header)
	var row=HBoxContainer.new();row.add_theme_constant_override("separation",10);app.header.add_child(row)
	for item in [["军费","cash"],["粮秣","food"],["军备","arms"],["燃油","fuel"],["白银","silver"]]:
		var stat=HBoxContainer.new();stat.custom_minimum_size.x=70*scale();stat.add_theme_constant_override("separation",4)
		stat.tooltip_text=item[0];row.add_child(stat)
		var icon=TextureRect.new();icon.texture=app.assets.texture("icon","icon_resource_"+item[1])
		icon.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;icon.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.custom_minimum_size=Vector2(26,32)*scale();icon.mouse_filter=Control.MOUSE_FILTER_IGNORE;stat.add_child(icon)
		line(stat,str(faction.resources.get(item[1],0)),18).tooltip_text=item[0]+"："+str(faction.resources.get(item[1],0))
	var rule=VSeparator.new();row.add_child(rule)
	var context=VBoxContainer.new();context.custom_minimum_size.x=270*scale();context.add_theme_constant_override("separation",0);row.add_child(context)
	line(context,state.date.replace("-",".")+"  ·  第%d回合 / 1天"%state.round,16,Color("ddce9e"))
	line(context,StateAccess.faction_name(state,state.player_faction_id,app.content)+"  /  "+StateAccess.faction_name(state,state.turn_order[state.phase_index],app.content)+"行动",13,Color("b9c6c2"))
	objective_button.text="作战目标  %d/%d  ›"%[state.objectives.filter(func(o):return o.progress>=o.required).size(),state.objectives.size()]
	objective_button.tooltip_text=app.content.scenarios[state.scenario_id].name
	objective_button.add_theme_font_size_override("font_size",int(16*text_scale()))
	refresh_summary()

func rebuild_layers() -> void:
	var body=app.layer_shell.get_child(0).get_child(0);app.clear(body)
	line(body,"地图图层",18,Color("ddce9e"))
	for item in [["势力覆盖","show_control"],["自然地形","show_terrain"],["地方地名","show_places"],["铁路线","show_rail"],["补给线","show_supply"],["操作蜂窝","show_grid"]]:
		var property=str(item[1]);var caption=str(item[0]);var button=app.button(body,item[0],func():pass)
		button.set_meta("hud_caption",caption)
		button.toggle_mode=true;button.set_pressed_no_signal(app.map_view.get(property));button.alignment=HORIZONTAL_ALIGNMENT_LEFT
		button.text=("开 · " if button.button_pressed else "关 · ")+caption
		button.custom_minimum_size=Vector2(210,48)*scale();button.add_theme_font_size_override("font_size",int(16*text_scale()))
		button.toggled.connect(func(pressed):button.text=("开 · " if pressed else "关 · ")+caption;app.map_view.set(property,pressed);app.map_view.queue_redraw();app.map_view.minimap.queue_redraw())
	line(body,"当前势力 · 半透明地表覆盖",13,Color("aabbb5"))
	var state=app.match_controller.state
	for id in state.turn_order:
		var row=HBoxContainer.new();body.add_child(row)
		var swatch=ColorRect.new();swatch.color=MapView.TERRITORY_COLORS.get(id,Color("8d9e8d"));swatch.custom_minimum_size=Vector2(12,12)*scale();swatch.size_flags_vertical=Control.SIZE_SHRINK_CENTER;row.add_child(swatch)
		line(row,StateAccess.faction_name(state,id,app.content),14)
	var atlas=app.button(body,"地形图鉴与地块规则",app.show_terrain_atlas);atlas.custom_minimum_size.y=48*scale();atlas.add_theme_font_size_override("font_size",int(15*text_scale()))

func style_command(control: Button, utility: bool=false) -> void:
	var side=88 if app.mobile_layout() else 68
	control.custom_minimum_size=Vector2(side,side if utility else side+10)*scale()
	if control is CommandCardButton:
		control.caption_size=int((14 if utility else 15)*text_scale())
		control.badge=null
	control.add_theme_stylebox_override("normal",plate(Color(.09,.15,.18,.87)))
	control.add_theme_stylebox_override("disabled",plate(Color(.10,.15,.17,.65)))
	control.add_theme_stylebox_override("hover",plate(Color(.23,.28,.26,.96)))
	control.add_theme_stylebox_override("pressed",plate(Color(.14,.20,.21,.98)))
	if control.text.begins_with("结束"):
		var end=plate(Color(.36,.30,.18,.96));end.border_color=Color("d1ba7a")
		control.add_theme_stylebox_override("normal",end)

func refresh_orders() -> void:
	app.clear(extras)
	for control in app.orders.get_children():
		if control is Label:
			control.add_theme_font_size_override("font_size",int(16*text_scale()))
			control.add_theme_color_override("font_color",Color("e8e7d8"))
			control.custom_minimum_size.x=250*scale();control.size_flags_vertical=Control.SIZE_SHRINK_CENTER
			control.add_theme_stylebox_override("normal",plate())
		if not control is Button:continue
		if control.text in ["自动作战","停止自动","撤销移动"]:
			control.reparent(extras)
			control.custom_minimum_size=Vector2(216,52)*scale()
			if control is CommandCardButton:
				# The additional-orders menu uses native text, avoiding a tiny icon
				# and caption compressed into a one-line menu item.
				control.compact_menu=true
			for color in ["font_color","font_hover_color","font_pressed_color","font_focus_color","font_disabled_color","font_hover_pressed_color"]:control.remove_theme_color_override(color)
			control.add_theme_font_size_override("font_size",int(17*text_scale()))
		else:style_command(control)
	if extras.get_child_count()==0:line(extras,"当前命令正在执行",16)
	else:
		for item in [["侦看地块与地名",inspect_map],["外交与援助",app.show_diplomacy]]:
			var extra=app.button(extras,item[0],item[1]);extra.custom_minimum_size=Vector2(216,52)*scale()
			extra.add_theme_font_size_override("font_size",int(17*text_scale()))
	for control in app.busy_orders.get_children() if is_instance_valid(app.busy_orders) else []:
		if control is Button:style_command(control)
	refresh_summary();layout()

func inspect_map() -> void:
	app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.selected_terrain_hex=null
	app.pending={};app.order_mode="";extras_open=false;app.refresh_battle()
	app.toast("选择地块或村镇，查看地理资料与规则。")

func refresh_summary() -> void:
	var state=app.match_controller.state
	var unit=StateAccess.find(state,"units",app.selected_unit_id)
	if not unit.is_empty() and not VisibilityRules.unit_visible(state,state.player_faction_id,unit):unit={}
	var city=StateAccess.find(state,"cities",app.selected_city_id)
	var key=JSON.stringify([app.selected_unit_id,app.selected_city_id,app.selected_poi_id,app.selected_terrain_hex,unit.get("def_id"),unit.get("hp",0),unit.get("max_hp",0),unit.get("ap_left",0),unit.get("ammo",0),unit.get("morale",0),unit.get("general_id"),city.get("owner_id"),city.get("fort_hp",0),city.get("fort_max_hp",0),state.date,text_scale()])
	if key==summary_key:return
	summary_key=key;app.clear(selection)
	var row=HBoxContainer.new();row.mouse_filter=Control.MOUSE_FILTER_IGNORE
	row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);row.offset_left=8;row.offset_top=6;row.offset_right=-8;row.offset_bottom=-6
	row.add_theme_constant_override("separation",8);selection.add_child(row)
	selection_title="战地指挥";var description="选择部队、城市或地块";var detail="点击查看详细档案  ›"
	if not unit.is_empty():
		var picture: Control
		if unit.general_id!=null:
			picture=GeneralPortraitView.new();picture.setup(app.assets,str(unit.general_id),Vector2(72,88)*scale(),str(state.date))
		else:
			picture=TextureRect.new();picture.texture=app.assets.unit_texture(unit);picture.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;picture.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		picture.custom_minimum_size=Vector2(72,88)*scale();picture.mouse_filter=Control.MOUSE_FILTER_IGNORE;row.add_child(picture)
		selection_title=str(app.content.definition("generals",unit.general_id).name) if unit.general_id!=null else str(app.content.definition("units",unit.def_id).name)
		description="兵力 %d/%d · 行动 %d"%[unit.hp,unit.max_hp,unit.ap_left]
		detail="士气 %d · 弹药 %d  ›"%[unit.morale,unit.ammo]
	elif not city.is_empty():
		selection_title=city.name;description=StateAccess.faction_name(state,city.owner_id,app.content);detail="城防 %d/%d · 生产建设  ›"%[city.fort_hp,city.fort_max_hp]
	elif not app.selected_poi_id.is_empty():
		var point=app.map_view.places.index.get(app.selected_poi_id,{})
		if not point.is_empty():selection_title=point.name;description="历史地方资料"
	elif app.selected_terrain_hex!=null:
		var cell=StateAccess.cell(state,app.selected_terrain_hex)
		if not cell.is_empty():selection_title=app.content.definition("terrains",cell.terrain_id).name;description="地块地形与行动规则"
	var text=VBoxContainer.new();text.mouse_filter=Control.MOUSE_FILTER_IGNORE;text.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	text.alignment=BoxContainer.ALIGNMENT_CENTER;text.add_theme_constant_override("separation",1);row.add_child(text)
	line(text,selection_title+"  ›",20,Color("ddce9e"));line(text,description,14);line(text,detail,13,Color("b6c3b5"))
	selection.tooltip_text=selection_title+" · 点击打开详细档案"

func toggle_details() -> void:
	details_open=not details_open;objectives_open=false;layers_open=false;extras_open=false;layout()
func toggle_objectives() -> void:
	objectives_open=not objectives_open;details_open=false;layers_open=false;extras_open=false;layout()
func toggle_layers() -> void:
	layers_open=not layers_open;details_open=false;objectives_open=false;extras_open=false;layout()
func toggle_extras() -> void:
	extras_open=not extras_open;details_open=false;objectives_open=false;layers_open=false;layout()
func dismiss_drawer() -> bool:
	var open=details_open or objectives_open or layers_open or extras_open
	details_open=false;objectives_open=false;layers_open=false;extras_open=false;layout();return open

func layout() -> void:
	if not is_instance_valid(app.map_view):return
	var s=scale();var insets=app.safe_insets();var viewport=app.get_viewport_rect().size
	var left=12+insets.x;var right=viewport.x-12-insets.z;var top=12+insets.y;var bottom=viewport.y-12-insets.w
	var rail_width=88*s if app.mobile_layout() else 68*s
	rail.position=Vector2(right-rail_width,top);rail.size=Vector2(rail_width,rail.get_combined_minimum_size().y)
	app.header_shell.position=Vector2(left,top)
	app.header_shell.size=Vector2(minf(right-left-rail_width-16,app.header.get_combined_minimum_size().x+16),maxf(62*s,app.header.get_combined_minimum_size().y+16))
	var upper=app.header_shell.position.y+app.header_shell.size.y+8*s
	objective_button.position=Vector2(left,upper);objective_button.size=Vector2(228,48)*s
	selection.size=Vector2(344,104)*s;selection.position=Vector2(left,bottom-selection.size.y)
	# The order row is a floating group, rather than a full-width opaque footer.
	var order_count=app.orders.get_child_count() if app.orders.visible else 3
	var button_width=(88 if app.mobile_layout() else 68)*s
	var wanted=maxf(450*s,minf(690*s,order_count*(button_width+6)))
	var width=minf(right-selection.get_rect().end.x-16*s,wanted)
	app.footer_shell.position=Vector2(right-width,bottom-120*s)
	app.footer_shell.size=Vector2(width,120*s)
	# Let containers resolve the actual wrapped text/commands before positioning
	# against the viewport edge; minima must never push controls off-screen.
	var height=maxf(116*s,app.footer_shell.get_combined_minimum_size().y)
	app.footer_shell.position.y=bottom-height;app.footer_shell.size.y=height
	app.inspector_shell.visible=details_open;app.mission_shell.visible=objectives_open
	app.layer_shell.visible=layers_open;extras_shell.visible=extras_open
	var field_bottom=minf(selection.position.y,app.footer_shell.position.y)-10*s
	var field_right=right
	if details_open:
		app.inspector_shell.position=Vector2(right-rail_width-12*s-330*s,upper)
		app.inspector_shell.size=Vector2(330*s,maxf(180*s,field_bottom-upper-8*s))
		field_right=app.inspector_shell.position.x-10*s
	app.mission_shell.position=Vector2(left,objective_button.get_rect().end.y+8*s)
	app.mission_shell.size=Vector2(390*s,minf(300*s,maxf(170*s,field_bottom-app.mission_shell.position.y)))
	app.layer_shell.anchor_left=0;app.layer_shell.anchor_right=0
	app.layer_shell.position=Vector2(right-rail_width-12*s-256*s,upper)
	app.layer_shell.size=Vector2(256*s,minf(490*s,maxf(180*s,field_bottom-upper)))
	extras_shell.position=Vector2(right-rail_width-12*s-238*s,upper)
	extras_shell.size=Vector2(238*s,extras.get_combined_minimum_size().y+16)
	app.map_view.hud_map_rect=Rect2(Vector2(left,upper),Vector2(maxf(120,field_right-left),maxf(120,field_bottom-upper)))
	var cinema=app.map_view.cinema;cinema.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	var cinema_scale=minf(s,minf((right-left)/720,(field_bottom-upper-12*s)/300))
	cinema.size=Vector2(720,300)*maxf(.5,cinema_scale)
	cinema.position=Vector2((viewport.x-cinema.size.x)*.5,maxf(upper,field_bottom-cinema.size.y-8*s))
	app.map_view.queue_redraw()
