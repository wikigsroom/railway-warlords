class_name MilitaryUI
extends RefCounted

# Native control skins; the independent Sub2 illustrations keep their bytes.
# Restrained steel edges frame the artwork rather than repeating an ornate rim.
const STEEL=Color("24323a")
const RAISED=Color("40515a")
const SILVER=Color("cbd0cd")
const PAPER=Color("e0e1d8")
const INK=Color("303f43")
const MUTED=Color("607073")
const BRASS=Color("b6a270")
const PALE=Color("f0f0e3")
static var library

static func flat(fill: Color, edge: Color, padding: int=12) -> StyleBoxFlat:
	var style=StyleBoxFlat.new()
	style.bg_color=fill;style.border_color=edge
	style.set_border_width_all(1);style.set_corner_radius_all(2)
	style.set_content_margin_all(padding)
	return style

static func skin(id: String, tint: Color, padding: int) -> StyleBox:
	var material="ui_officer_sheet_v023" if id=="ui_dialog_frame" else "ui_command_plate_v023" if id in ["ui_button_plate","ui_order_card"] else ""
	if library!=null and not material.is_empty() and ResourceLoader.exists("res://assets/ui/"+material+".png"):
		var texture_style=StyleBoxTexture.new();texture_style.texture=library.texture("ui",material)
		texture_style.modulate_color=tint
		for side in [SIDE_LEFT,SIDE_TOP,SIDE_RIGHT,SIDE_BOTTOM]:
			texture_style.set_texture_margin(side,8);texture_style.set_content_margin(side,padding)
		return texture_style
	var fill=STEEL;var edge=Color("728087")
	if id=="ui_dialog_frame":fill=SILVER;edge=Color("8d999a")
	elif id=="ui_paper_panel":fill=PAPER;edge=Color("b5b8aa")
	elif id in ["ui_button_plate","ui_order_card"]:fill=RAISED;edge=Color("7f8d91")
	var style=flat(fill*tint,edge*tint,padding)
	if id in ["ui_hud_plate","ui_steel_panel"]:
		style.shadow_color=Color(0,0,0,.22);style.shadow_size=5;style.shadow_offset=Vector2(0,2)
	return style

static func install(theme: Theme, scale: float, assets) -> void:
	library=assets
	for kind in ["Button","OptionButton"]:
		theme.set_stylebox("normal",kind,skin("ui_button_plate",Color.WHITE,12))
		theme.set_stylebox("hover",kind,skin("ui_button_plate",Color(1.12,1.12,1.10),12))
		theme.set_stylebox("pressed",kind,skin("ui_button_plate",Color(.78,.84,.84),12))
		theme.set_stylebox("disabled",kind,flat(Color("aeb8b6"),Color("99a6a6"),12))
		var focus=flat(Color.TRANSPARENT,BRASS,12);focus.set_border_width_all(2)
		theme.set_stylebox("focus",kind,focus)
		for state in ["font_color","font_hover_color","font_pressed_color","font_focus_color"]:theme.set_color(state,kind,PALE)
		theme.set_color("font_disabled_color",kind,Color("4f6265"))
		theme.set_constant("outline_size",kind,0)
		theme.set_constant("h_separation",kind,10)
	var field=flat(Color("e2e5dd"),Color("8c9b9b"),12)
	theme.set_stylebox("normal","LineEdit",field)
	theme.set_stylebox("focus","LineEdit",flat(PALE,BRASS,12))
	theme.set_color("font_color","LineEdit",INK)
	theme.set_color("font_placeholder_color","LineEdit",MUTED)
	theme.set_color("caret_color","LineEdit",INK)
	theme.set_font_size("font_size","LineEdit",int(19*scale))
	theme.set_stylebox("background","ProgressBar",flat(Color("aab5b4"),Color.TRANSPARENT,0))
	theme.set_stylebox("fill","ProgressBar",flat(Color("657f7c"),Color.TRANSPARENT,0))
	theme.set_stylebox("panel","PopupMenu",flat(STEEL,Color("7f8d91"),12))
	theme.set_color("font_color","PopupMenu",PALE)
	theme.set_color("font_hover_color","PopupMenu",PALE)
	theme.set_stylebox("hover","PopupMenu",flat(RAISED,BRASS,8))
