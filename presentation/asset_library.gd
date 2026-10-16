class_name AssetLibrary
extends RefCounted

var textures: Dictionary={}
var font: Font
var map_font: Font
var unit_actions: Dictionary={}
var map_texture_order: Array[String]=[]
const MAP_TEXTURE_CACHE_LIMIT=384

func prepare_battle_glyphs(ui_scale: float) -> void:
	# Font glyph creation is costly on first use. Warm the actual command/status
	# text while entering the battle, before an AI command or cue is submitted.
	var text="自动作战停止正在执行部署可平移地图行军交演出中命令跳过确认攻击伤害反风险消耗行动点沿路径前进目标与资源已检查取消移动战法整补撤销待回合对手方尚未轮到本暂停恢复保存重新选择已更新校验未通过保留后载入 当前战局势力城池控制区首都省城县村落集镇查地名直奉皖晋冯国民军苏浙粤滇川桂湘甘东江广州地方 %d0123456789/→»·—"
	var characters={}
	for index in range(text.length()):characters[text.unicode_at(index)]=true
	for font_size in [int(20*ui_scale),int(15*ui_scale)]:
		font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size)
		if font is FontFile:
			for cache_index in range(font.get_cache_count()):
				for character in characters:font.render_range(cache_index,Vector2i(font_size,0),character,character)

func _init() -> void:
	font=load("res://assets/font/SourceHanSansSC-Regular.otf")
	map_font=load("res://assets/font/SourceHanSerifSC-SemiBold.otf") if ResourceLoader.exists("res://assets/font/SourceHanSerifSC-SemiBold.otf") else font
	if FileAccess.file_exists("res://presentation/data/unit_actions.json"):
		var data=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/unit_actions.json"))
		if data is Dictionary:unit_actions=data.get("records",{})

func texture(category: String, id: String) -> Texture2D:
	var key=category+"/"+id
	if not textures.has(key):
		var path="res://assets/%s/%s.png"%[category,id]
		textures[key]=load(path) if ResourceLoader.exists(path) else null
	if id.contains("_bank_") or id.begins_with("tile_surface_") or id.begins_with("tile_ground_macro_") or id.begins_with("tile_ground_identity_"):
		map_texture_order.erase(key);map_texture_order.append(key)
		while map_texture_order.size()>MAP_TEXTURE_CACHE_LIMIT:
			textures.erase(map_texture_order.pop_front())
	return textures[key]

func unit_texture(u: Dictionary, direction: String="") -> Texture2D:
	var unit_id=str(u.elite_id if u.elite_id!=null else u.def_id)
	var requested=direction if not direction.is_empty() else str(u.get("facing","se"))
	var direct=texture("unit","unit_%s_%s"%[unit_id,requested])
	if direct!=null:return direct
	# Directional Sub2 views are optional at import time so older saves and
	# lightweight editor scans remain drawable while the approved source set is
	# being expanded. The fallback is still an immutable original view.
	var fallback="sw" if requested in ["w","sw","nw"] else "se"
	return texture("unit","unit_%s_%s"%[unit_id,fallback])

func unit_action_id(u: Dictionary, direction: String, pose: String) -> String:
	var family=str(u.elite_id if u.elite_id!=null else u.def_id)
	var action_id="unit_%s_%s%s"%[family,direction,"" if pose=="idle" else "_"+pose]
	return action_id if unit_actions.has(action_id) else ""

func unit_action_texture(u: Dictionary, direction: String, pose: String) -> Texture2D:
	var id=unit_action_id(u,direction,pose)
	return texture("unit",id) if not id.is_empty() else unit_texture(u,direction)

func unit_action_rect(u: Dictionary, direction: String, pose: String, bound: Vector2) -> Rect2:
	var id=unit_action_id(u,direction,pose)
	if id.is_empty():return Rect2()
	var record=unit_actions[id];var bounds=record.alpha_bounds
	var extent=Vector2(bounds[2]-bounds[0],bounds[3]-bounds[1])
	var scale=minf(bound.x*.94/extent.x,bound.y*.78/extent.y)
	var foot=Vector2((bounds[0]+bounds[2])*.5,bounds[3])*scale
	return Rect2(Vector2(0,12)-foot,Vector2(record.dimensions[0],record.dimensions[1])*scale)
