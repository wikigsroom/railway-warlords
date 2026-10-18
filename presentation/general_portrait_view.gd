class_name GeneralPortraitView
extends Control

var assets: AssetLibrary
var record: Dictionary={}
var portrait: Texture2D
var paper: Texture2D

func setup(library: AssetLibrary, general_id: String, bound: Vector2, date: String="", stage: String="") -> void:
	assets=library;record=assets.general_portraits.resolve(general_id,date,stage)
	custom_minimum_size=bound;mouse_filter=Control.MOUSE_FILTER_PASS
	name="GeneralPortrait_"+general_id
	set_meta("general_id",general_id);set_meta("portrait_record",record)
	portrait=assets.texture("portrait",record.asset_id) if record.kind=="portrait" else null
	paper=assets.texture("ui","ui_paper_panel")
	tooltip_text=str(record.name)+" · "+str(record.caption)+"\n"+str(record.get("reference_caption",""))
	resized.connect(queue_redraw)

func _draw() -> void:
	if assets==null:return
	var frame=Rect2(Vector2.ZERO,size)
	draw_rect(frame,Color("aebbb6"))
	draw_rect(Rect2(Vector2(6,6),size-Vector2(12,12)),Color("c7cfbf"))
	draw_rect(frame.grow(-1),Color("6d7e7e"),false,1.0)
	draw_line(Vector2(7,size.y-6),Vector2(size.x-7,size.y-6),Color("ac9560"),2.0)
	var inset=frame.grow(-8)
	if portrait!=null:
		var source=portrait.get_size()
		var factor=minf(inset.size.x/source.x,inset.size.y/source.y)
		var extent=source*factor
		draw_texture_rect(portrait,Rect2(inset.position+(inset.size-extent)*.5,extent),false)
	else:
		# Explicit identity plaque for undocumented likenesses; no invented face.
		var emblem=str(record.get("identity_text",str(record.name).left(1)))
		var font_size=int(minf(size.x*.48,size.y*.42))
		var font=assets.map_font
		var width=font.get_string_size(emblem,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size).x
		var seal=Rect2(Vector2((size.x-minf(size.x*.68,72))*.5,size.y*.16),Vector2(minf(size.x*.68,72),size.y*.53))
		draw_rect(seal,Color("84513b"),false,2)
		draw_string(font,Vector2((size.x-width)*.5,size.y*.50+font.get_ascent(font_size)*.28),emblem,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,Color("733e2c"))
		var role=str(record.get("identity_role","身份牌"))
		var role_size=maxi(12,int(minf(size.x*.12,17)))
		width=assets.font.get_string_size(role,HORIZONTAL_ALIGNMENT_LEFT,-1,role_size).x
		draw_string(assets.font,Vector2((size.x-width)*.5,size.y*.84),role,HORIZONTAL_ALIGNMENT_LEFT,-1,role_size,Color("534d3e"))
