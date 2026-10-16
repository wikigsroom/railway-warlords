class_name BattleCinema
extends Control

var playback: BattlePlayback
var assets: AssetLibrary
var content: ContentRegistry
var label_scale=1.0

func _ready() -> void:
	mouse_filter=Control.MOUSE_FILTER_IGNORE;set_process(true)

func _process(_delta: float) -> void:
	visible=playback!=null and playback.active and playback.current.get("cinematic",false)
	if visible:queue_redraw()

func text_at(text: String, point: Vector2, size_px: int, color: Color, centered: bool=false) -> void:
	var font=assets.map_font
	if centered:point.x-=font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,size_px).x*.5
	draw_string_outline(font,point,text,HORIZONTAL_ALIGNMENT_LEFT,-1,size_px,1,Color(.08,.14,.17,.6))
	draw_string(font,point,text,HORIZONTAL_ALIGNMENT_LEFT,-1,size_px,color)

func illustration(texture: Texture2D, center: Vector2, bound: Vector2, tint: Color=Color.WHITE) -> void:
	if texture==null:return
	var dimensions=texture.get_size()*minf(bound.x/texture.get_width(),bound.y/texture.get_height())
	draw_texture_rect(texture,Rect2(center-dimensions*.5,dimensions),false,tint)

func die(center: Vector2, face: int, rolling: bool, phase: float, red: bool) -> void:
	var angle=sin(phase*25)*.22 if rolling and not playback.reduced_motion else 0.0
	var s=Vector2.ONE*(40+sin(phase*24)*2 if rolling else 40)
	var points=PackedVector2Array()
	for v in [Vector2(-.5,-.5),Vector2(.5,-.5),Vector2(.5,.5),Vector2(-.5,.5)]:points.append(center+(v*s).rotated(angle))
	var shadow=PackedVector2Array()
	for point in points:shadow.append(point+Vector2(3,4))
	draw_colored_polygon(shadow,Color(.06,.13,.16,.65))
	draw_colored_polygon(points,Color("a34740") if red else Color("f4edd4"))
	var border=points.duplicate();border.append(points[0]);draw_polyline(border,Color("dfd6b9"),1.5,true)
	draw_line(points[0],points[1],Color(1,1,.89,.85),2,true)
	var dots=[]
	match face:
		1:dots=[Vector2.ZERO]
		2:dots=[Vector2(-1,-1),Vector2(1,1)]
		3:dots=[Vector2(-1,-1),Vector2.ZERO,Vector2(1,1)]
		4:dots=[Vector2(-1,-1),Vector2(1,-1),Vector2(-1,1),Vector2(1,1)]
		5:dots=[Vector2(-1,-1),Vector2(1,-1),Vector2.ZERO,Vector2(-1,1),Vector2(1,1)]
		6:dots=[Vector2(-1,-1),Vector2(1,-1),Vector2(-1,0),Vector2(1,0),Vector2(-1,1),Vector2(1,1)]
	for dot in dots:draw_circle(center+(dot*9).rotated(angle),2.7,Color("f9eed4") if red else Color("26313a"))

func _draw() -> void:
	if playback==null or not playback.active or not playback.current.get("cinematic",false):return
	var action=playback.current;var p=playback.progress()
	modulate.a=minf(1,p*14)*minf(1,(1-p)*14)
	var canvas_size=Vector2(720,300)
	draw_set_transform(Vector2.ZERO,0,size/canvas_size)
	var rect=Rect2(Vector2.ZERO,canvas_size);draw_style_box(panel_style(),rect)
	var stage=Rect2(Vector2(5,45),Vector2(canvas_size.x-10,canvas_size.y-103))
	var landscape=assets.texture("background","background_battle_field")
	if landscape!=null:draw_texture_rect(landscape,stage,false,Color(.75,.84,.81))
	draw_rect(stage,Color(.05,.13,.15,.12))
	var middle=canvas_size.x*.5;var attacker=action.attacker;var target=action.target;var city=action.city
	var title="火炮压制" if action.family=="artillery" else "步兵交战" if action.family=="infantry" else action.title
	text_at(action.title+" / "+title,Vector2(18,29),20,Color("f0ead8"))
	text_at("战斗演出 · 可跳过",Vector2(canvas_size.x-174,28),14,Color("b3c9ce"))
	draw_line(Vector2(8,38),Vector2(canvas_size.x-8,38),Color("788f99"),1,true)
	var from=Vector2(canvas_size.x*.19,stage.position.y+stage.size.y*.56);var to=Vector2(canvas_size.x*.81,from.y)
	var attack_color=MapView.TERRITORY_COLORS.get(attacker.owner_id,Color("6199d0"))
	var defense_color=MapView.TERRITORY_COLORS.get(target.get("owner_id",city.get("owner_id","")),Color("dc826c"))
	draw_circle(from+Vector2(0,45),37,Color(attack_color,.20));draw_circle(to+Vector2(0,45),37,Color(defense_color,.20))
	var anticipation=sin(clampf(p/.35,0,1)*PI)*4;var recoil=sin(clampf((p-.35)/.2,0,1)*PI)*12
	if playback.reduced_motion:anticipation=0;recoil=0
	# Stage positions are left/right; select the real side views so both actors
	# face their opponent, independently of their heading on the north-up map.
	illustration(assets.unit_action_texture(attacker,"e",playback.pose_of(attacker)),from-Vector2(recoil+anticipation,0),Vector2(192,157))
	var defender_texture=assets.unit_action_texture(target,"w",playback.pose_of(target)) if not target.is_empty() else assets.texture("scenery","scenery_walled_city")
	var shake=sin(p*95)*4 if p>.65 and p<.8 and not playback.reduced_motion else 0.0
	illustration(defender_texture,to+Vector2(shake,0),Vector2(192,157),Color(1.25,1.10,.96) if p>.65 and p<.7 else Color.WHITE)
	text_at(content.definition("units",attacker.def_id).name,Vector2(from.x,stage.end.y-12),18,Color("f6f0d8"),true)
	text_at(content.definition("units",target.def_id).name if not target.is_empty() else city.get("name","城防"),Vector2(to.x,stage.end.y-12),18,Color("f6f0d8"),true)
	var rolling=p<.30;var roll=action.roll
	die(Vector2(middle-27,88),1+(int(p*80)%6) if rolling else roll.attack_die,rolling,p,false)
	die(Vector2(middle+27,88),1+(int(p*73+2)%6) if rolling else roll.defense_die,rolling,p,true)
	text_at("攻势 / 防守" if rolling else "战况 %+.1f%%"%((roll.modifier_permille-1000)/10.0),Vector2(middle,126),16,Color("f1e7c1"),true)
	if p>=.35 and p<.69:
		var shots=5 if action.attacker.def_id=="machine_gun" else 3 if action.family=="infantry" else 1
		for shot in range(shots):
			var flight=clampf((p-.35-shot*.035)/(.34-shot*.012),0,1)
			if flight<=0 or flight>=1:continue
			var projectile=from.lerp(to,flight);projectile.y-=sin(flight*PI)*(45 if action.family=="artillery" else 4);projectile.y+=shot*3
			draw_line(projectile-Vector2(20,0),projectile,Color("f6dda2"),2,true);draw_circle(projectile,3 if action.family=="artillery" else 1.5,Color("fff0bc"))
		if p<.47:illustration(assets.texture("fx","fx_muzzle"),from+Vector2(46,-3),Vector2(58,52),Color(1,1,1,clampf(1-(p-.35)/.12,0,1)))
	var amount=0;var fort=0
	for event in action.impacts:
		if event.type=="FortDamaged":fort+=event.amount
		else:amount+=event.amount
	if p>=.65:
		if p<.92:illustration(assets.texture("fx","fx_cannon_blast" if action.family=="artillery" else "fx_bullet_hit"),to,Vector2(125,105),Color(1,1,1,clampf(1-(p-.65)/.27,0,1)))
		text_at("城防 −%d"%fort if fort>0 else "兵力 −%d"%amount,Vector2(middle,181),25,Color("f9d29a"),true)
		if fort>0 and amount>0:text_at("守军 −%d"%amount,Vector2(middle,207),16,Color("ede5cc"),true)
	var step="整队瞄准" if p<.30 else "骰子已定" if p<.35 else "发起攻击" if p<.65 else "命中结算"
	draw_rect(Rect2(Vector2(5,canvas_size.y-56),Vector2(canvas_size.x-10,51)),Color("152a35"))
	text_at(step,Vector2(18,canvas_size.y-22),17,Color("d9e5de"))
	text_at("%d  :  %d"%[roll.attack_die,roll.defense_die] if not rolling else "战况判定中",Vector2(middle,canvas_size.y-22),20,Color("e9d3a0"),true)
	draw_rect(Rect2(Vector2(canvas_size.x-147,canvas_size.y-34),Vector2(128,7)),Color("071c24"))
	draw_rect(Rect2(Vector2(canvas_size.x-147,canvas_size.y-34),Vector2(128*p,7)),Color("8eb2bd"))

func panel_style() -> StyleBoxFlat:
	var box=StyleBoxFlat.new();box.bg_color=Color("162833");box.border_color=Color("9aadb3");box.set_border_width_all(2);box.shadow_color=Color(0,0,0,.45);box.shadow_size=12;box.set_corner_radius_all(4);return box

