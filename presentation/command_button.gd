class_name CommandCardButton
extends Button

# Native Button behavior (focus, mouse/touch, disabled and pressed signals) is
# preserved. The independent immutable Sub2 icon is simply drawn in its bounds.
var artwork: Texture2D
var badge: Texture2D
var caption_font: Font
var caption_size=16
var accent=Color("d8c99e")
var short_caption=""
var compact_menu=false

func _ready() -> void:
	for state in ["font_color","font_hover_color","font_pressed_color","font_focus_color","font_disabled_color","font_hover_pressed_color"]:
		add_theme_color_override(state,Color.TRANSPARENT)
	add_theme_constant_override("outline_size",0)

func _draw() -> void:
	if compact_menu:return
	var ink=Color("e9e6d9") if not disabled else Color("858e8f")
	var icon_tint=Color.WHITE if not disabled else Color(.55,.59,.60,.64)
	if is_hovered() and not disabled:icon_tint=Color(1.12,1.08,.94)
	var span=minf(size.x-8,size.y-29)
	var center=Vector2(size.x*.5,span*.5+4)
	if badge!=null:draw_contained(badge,Rect2(center-Vector2.ONE*span*.5,Vector2.ONE*span),icon_tint)
	if artwork!=null:
		var icon_size=span*.57 if badge!=null else span*.68
		draw_contained(artwork,Rect2(center-Vector2.ONE*icon_size*.5,Vector2.ONE*icon_size),icon_tint)
	else:
		# Text is kept readable when an optional image is not yet generated. This
		# is code-native UI, not a fabricated replacement raster asset.
		var glyph="Ⅱ" if text=="设置" else "→" if text.begins_with("结束") else "＋" if text.contains("整补") else "•"
		var glyph_size=caption_size+11
		var glyph_width=caption_font.get_string_size(glyph,HORIZONTAL_ALIGNMENT_LEFT,-1,glyph_size).x
		draw_string(caption_font,center+Vector2(-glyph_width*.5,glyph_size*.30),glyph,HORIZONTAL_ALIGNMENT_LEFT,-1,glyph_size,accent if not disabled else ink)
	var caption=short_caption if not short_caption.is_empty() else text
	var caption_width=caption_font.get_string_size(caption,HORIZONTAL_ALIGNMENT_LEFT,-1,caption_size).x
	draw_string(caption_font,Vector2((size.x-caption_width)*.5,size.y-7),caption,HORIZONTAL_ALIGNMENT_LEFT,-1,caption_size,ink)
	if has_focus():draw_rect(Rect2(Vector2(2,2),size-Vector2(4,4)),accent,false,2)

func draw_contained(texture: Texture2D, rect: Rect2, tint: Color) -> void:
	var dimensions=texture.get_size()*minf(rect.size.x/texture.get_width(),rect.size.y/texture.get_height())
	draw_texture_rect(texture,Rect2(rect.get_center()-dimensions*.5,dimensions),false,tint)
