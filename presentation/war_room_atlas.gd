class_name WarRoomAtlas
extends Control

# A live geographical selector, drawn from the same immutable map records as
# the battlefield. It never creates a match, consumes RNG or invents borders.
signal faction_selected(owner: String)

var content: ContentRegistry
var assets: AssetLibrary
var recipe: Dictionary={}
var source_map: Dictionary={}
var selected_owner=""
var rail_lines: Array=[]
var cities: Array=[]
var bounds=Rect2()
var target=Vector2.ZERO
var target_exists=false
var scale_factor=1.0
var map_offset=Vector2.ZERO
var pin_rects: Array=[]
var map_revision=0
var label_scale=1.0
var landscape: MapView
var view_center=Vector2.ZERO
var view_multiplier=1.0
var dragging=false
var dragged=false
var drag_origin=Vector2.ZERO
var pointer_positions: Dictionary={}
var pinch_length=0.0
var settlement_originals_drawn=0
var reference_originals_drawn=0

func _ready() -> void:
	clip_contents=true;mouse_filter=Control.MOUSE_FILTER_STOP
	resized.connect(func():sync_landscape();queue_redraw())

func configure(registry: ContentRegistry, library: AssetLibrary, text_scale: float=1.0) -> void:
	content=registry;assets=library;label_scale=text_scale
	# This is the shipping terrain renderer, with no match, army, fog, orders,
	# ownership guesses or random stream. Markers remain this selector's layer.
	landscape=MapView.new();landscape.name="ScenarioLandscape"
	landscape.static_only=true;landscape.atlas_preview=true;landscape.content=content;landscape.assets=assets
	landscape.show_control=false;landscape.show_grid=false;landscape.show_rail=false;landscape.show_places=false
	landscape.label_scale=text_scale;landscape.mouse_filter=Control.MOUSE_FILTER_IGNORE
	landscape.show_behind_parent=true;landscape.clip_contents=true;landscape.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	landscape.set_process(false);add_child(landscape)

func points(coordinates: Array) -> PackedVector2Array:
	var result=PackedVector2Array()
	for xy in coordinates:result.append(Vector2(xy[0],xy[1]))
	return result

func select_scenario(id: String, owner: String) -> void:
	var changed=recipe.get("id","")!=id
	recipe=content.scenarios[id];selected_owner=owner
	if source_map.get("id","")!=recipe.map_id:
		source_map=content.maps[recipe.map_id];prepare_geometry();map_revision+=1
	landscape.state={"map":source_map,"date":recipe.anchor_date,"content_hash":"scenario-selector",
		"scenario_id":id,"player_faction_id":owner,"mode":recipe.mode,"round":1,
		"units":[],"cities":[],"factions":[],"visibility":[]}
	if landscape.geography_key!=landscape.geography_signature():landscape.prepare_geography()
	elif landscape.administration_key!=ContentRegistry.administration_year(recipe.anchor_date):landscape.prepare_administration(false)
	prepare_cities()
	if changed:view_multiplier=1.0;view_center=framing_bounds().get_center()
	sync_landscape();queue_redraw()

func prepare_geometry() -> void:
	var extent=points(source_map.get("render_extent",[]))
	bounds=Rect2(extent[0],Vector2.ONE) if not extent.is_empty() else Rect2(Vector2.ZERO,Vector2.ONE)
	for point in extent:bounds=bounds.expand(point)

func prepare_cities() -> void:
	cities=[];rail_lines=[];target_exists=false
	var playable=content.playable_factions(recipe.id) if recipe.mode=="conquest" else []
	for city in source_map.cities:
		if city.get("active_from","0000-00-00")>recipe.anchor_date or city.get("active_to","9999-12-31")<=recipe.anchor_date:continue
		var at=HexGrid.to_world(HexGrid.coordinate(city.position))
		var owner=ContentRegistry.conquest_owner(city,recipe.anchor_date,recipe.id)
		# Local campaign deployment is authored separately from dated reference
		# control. Only the objective is emphasized there; no false front is drawn.
		cities.append({"id":city.id,"name":city.name,"at":at,"owner":owner,"level":city.level,
			"playable":playable.has(owner)})
		if recipe.mode!="conquest" and city.id==recipe.get("target_city_id",""):target=at;target_exists=true
	for edge in source_map.rail_edges:
		if edge.get("active_from","0000-00-00")>recipe.anchor_date or edge.get("active_to","9999-12-31")<=recipe.anchor_date:continue
		var line=PackedVector2Array()
		for hex in edge.path_hexes:line.append(HexGrid.to_world(HexGrid.coordinate(hex)))
		if line.size()>1:rail_lines.append(line)

func framing_bounds() -> Rect2:
	if not source_map.get("strategic_scale",false) or recipe.mode!="campaign" or not target_exists:return bounds
	var radius=float(recipe.get("camera_radius_hex",18+maxi(0,recipe.get("province_scope",[]).size()-1)*5))
	return Rect2(target-Vector2(72,55)*radius,Vector2(144,110)*radius).intersection(bounds)

func project(world: Vector2) -> Vector2:return world*scale_factor+map_offset

func sync_landscape() -> void:
	if recipe.is_empty() or not is_instance_valid(landscape) or size.x<1 or size.y<1:return
	var frame=framing_bounds()
	var usable=Vector2(maxf(1,size.x-72),maxf(1,size.y-76))
	scale_factor=maxf(.001,minf(usable.x/maxf(1,frame.size.x),usable.y/maxf(1,frame.size.y)))*view_multiplier
	var half=usable/(2*scale_factor)
	view_center.x=frame.get_center().x if half.x>=frame.size.x*.5 else clampf(view_center.x,frame.position.x+half.x,frame.end.x-half.x)
	view_center.y=frame.get_center().y if half.y>=frame.size.y*.5 else clampf(view_center.y,frame.position.y+half.y,frame.end.y-half.y)
	map_offset=size*.5-view_center*scale_factor
	landscape.size=size;landscape.camera=view_center;landscape.zoom=scale_factor
	landscape.queue_redraw()

func zoom_at(factor: float, at: Vector2) -> void:
	if recipe.is_empty():return
	var before=(at-map_offset)/scale_factor
	view_multiplier=clampf(view_multiplier*factor,1.0,10.0);sync_landscape()
	view_center+=before-(at-map_offset)/scale_factor
	sync_landscape();queue_redraw()

func reset_view() -> void:
	view_multiplier=1.0;view_center=framing_bounds().get_center();sync_landscape();queue_redraw()

func pan(delta: Vector2) -> void:
	view_center-=delta/scale_factor;sync_landscape();queue_redraw()

func capture_facts() -> Dictionary:
	return {"map_id":source_map.get("id",""),"anchor_date":recipe.get("anchor_date",""),
		"renderer":"shipping_MapView_static_atlas","source_map_immutable":source_map.is_read_only(),
		"ground":landscape.continuous_ground_facts(),"relief":landscape.relief.diagnostics,
		"hydrography":landscape.hydrography_diagnostics,"material_cells_drawn":landscape.terrain_surface_variant_draw_count,
		"scenery_drawn":landscape.terrain_scenery_draw_count,"dated_rail_edges":rail_lines.size(),
		"settlement_originals_drawn":settlement_originals_drawn,"reference_originals_drawn":reference_originals_drawn,
		"zoom_multiplier":view_multiplier,"camera":view_center,"creates_match":false}

func _draw() -> void:
	if recipe.is_empty() or size.x<1 or size.y<1:return
	draw_set_transform(map_offset,0,Vector2.ONE*scale_factor)
	for source_line in rail_lines:
		var line=landscape.rounded_track(source_line)
		draw_polyline(line,Color(.94,.91,.75,.90),3.0/scale_factor,true)
		draw_polyline(line,Color("454d48"),1.1/scale_factor,true)
	draw_set_transform(Vector2.ZERO)
	# Fixed cardinal orientation and quiet edge rules keep the atlas readable
	# at a different scale without fabricating miniature terrain decorations.
	draw_rect(Rect2(Vector2(10,10),size-Vector2(20,20)),Color(.91,.90,.78,.5),false,1)
	var font_size=int(16*label_scale)
	draw_string(assets.font,Vector2(26,20+font_size),"N ↑",HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,Color("e8e8d4"))
	draw_reference_places(font_size)
	settlement_originals_drawn=0
	pin_rects.clear();var occupied: Array=[]
	var ordered=cities.duplicate();ordered.sort_custom(func(a,b):return city_priority(a)>city_priority(b))
	for city in ordered:
		var p=project(city.at)
		if not Rect2(Vector2(22,22),size-Vector2(44,44)).has_point(p):continue
		var own=city.owner==selected_owner;var color=MapView.TERRITORY_COLORS.get(city.owner,Color("909b90"))
		var radius=7.0 if own else 4.0
		if own:draw_circle(p,radius+4,Color(.97,.91,.70,.7),false,1.4,true)
		var art=str(landscape.settlement_choices.get(str(city.id)+":",""))
		if not art.is_empty() and (own or city.level>=3 or city.id==recipe.get("target_city_id","")):
			var image=assets.texture("building",art)
			if image!=null:
				settlement_originals_drawn+=1
				var rectangle=MapArtBank.source_rect(art,Vector2(38,34)*label_scale)
				rectangle.position+=p+Vector2(0,3)
				draw_texture_rect(image,rectangle,false)
		draw_circle(p+Vector2(1,2),radius+1,Color(0,0,0,.4));draw_circle(p,radius,color)
		draw_circle(p,radius,Color("e7e3ce"),false,1,true)
		if city.playable:pin_rects.append({"rect":Rect2(p-Vector2(22,22),Vector2(44,44)),"owner":city.owner})
		if not own and city.level<2 and city.id!=recipe.get("target_city_id",""):continue
		var text_size=assets.font.get_string_size(city.name,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size)
		var label_rect=Rect2(p+Vector2(-text_size.x*.5,10),text_size+Vector2(0,6))
		if label_rect.end.x>size.x-16 or label_rect.position.x<16 or label_rect.end.y>size.y-16:continue
		if occupied.any(func(rect):return rect.grow(5).intersects(label_rect)):continue
		occupied.append(label_rect)
		draw_style_box(label_style(),label_rect.grow(3))
		draw_string(assets.font,label_rect.position+Vector2(0,font_size+1),city.name,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,Color("efeddf"))
	if target_exists:
		var p=project(target)
		draw_arc(p,17,0,TAU,32,Color("f3d995"),2,true)
		draw_line(p+Vector2(-24,0),p+Vector2(-12,0),Color("f3d995"),2,true)
		draw_line(p+Vector2(12,0),p+Vector2(24,0),Color("f3d995"),2,true)

func label_style() -> StyleBoxFlat:
	var style=StyleBoxFlat.new();style.bg_color=Color(.12,.20,.22,.78);style.set_corner_radius_all(2);return style

func draw_reference_places(font_size: int) -> void:
	reference_originals_drawn=0
	var excluded: Dictionary={};var occupied: Array=[]
	for city in cities:excluded[city.id]=true;occupied.append(Rect2(project(city.at)-Vector2(26,30),Vector2(52,62)))
	var ordered=landscape.places.nodes.duplicate()
	ordered.sort_custom(func(a,b):return HistoricalPlaces.importance(a,recipe.anchor_date)>HistoricalPlaces.importance(b,recipe.anchor_date))
	for place in ordered:
		if excluded.has(place.id) or not HistoricalPlaces.visible_at(place,recipe.anchor_date,scale_factor*3.0):continue
		var at=project(place.at)
		if not Rect2(Vector2(30,42),size-Vector2(60,70)).has_point(at):continue
		var footprint=Rect2(at-Vector2(16,26)*label_scale,Vector2(32,48)*label_scale)
		if occupied.any(func(rect):return rect.intersects(footprint)):continue
		var art=str(landscape.settlement_choices.get(str(place.id)+":",""))
		if art.is_empty() or not place.get("sprite_on_land",false):continue
		var image=assets.texture("building",art)
		if image==null:continue
		var rectangle=MapArtBank.source_rect(art,Vector2(27,25)*label_scale)
		rectangle.position+=at;draw_texture_rect(image,rectangle,false)
		occupied.append(footprint);reference_originals_drawn+=1
		var type_size=maxi(12,font_size-2)
		var width=assets.font.get_string_size(place.name,HORIZONTAL_ALIGNMENT_LEFT,-1,type_size).x
		var caption=Rect2(at+Vector2(-width*.5,3),Vector2(width,type_size+4))
		if caption.position.x>12 and caption.end.x<size.x-12:
			draw_style_box(label_style(),caption.grow(2));draw_string(assets.font,caption.position+Vector2(0,type_size),place.name,HORIZONTAL_ALIGNMENT_LEFT,-1,type_size,Color("e3e4d7"))

func city_priority(city: Dictionary) -> int:
	return int(city.id==recipe.get("target_city_id",""))*100+int(city.owner==selected_owner)*10+int(city.level)

func select_pin(at: Vector2) -> void:
	var nearest="";var distance=INF
	for pin in pin_rects:
		var delta=pin.rect.get_center().distance_squared_to(at)
		if pin.rect.has_point(at) and delta<distance:nearest=pin.owner;distance=delta
	if not nearest.is_empty():faction_selected.emit(nearest)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			zoom_at(1.25 if event.button_index==MOUSE_BUTTON_WHEEL_UP else .8,event.position);accept_event()
		elif event.button_index==MOUSE_BUTTON_LEFT:
			if event.pressed:dragging=true;dragged=false;drag_origin=event.position
			else:
				if dragging and not dragged:select_pin(event.position)
				dragging=false
			accept_event()
	elif event is InputEventMouseMotion and dragging:
		if dragged or event.position.distance_to(drag_origin)>12:
			dragged=true;pan(event.relative);accept_event()
	elif event is InputEventScreenTouch:
		if event.pressed:
			if pointer_positions.is_empty():dragged=false;drag_origin=event.position
			pointer_positions[event.index]=event.position
			if pointer_positions.size()==2:pinch_length=pointer_positions.values()[0].distance_to(pointer_positions.values()[1]);dragged=true
		else:
			if pointer_positions.size()==1 and not dragged:select_pin(event.position)
			pointer_positions.erase(event.index);pinch_length=0.0
		accept_event()
	elif event is InputEventScreenDrag and pointer_positions.has(event.index):
		pointer_positions[event.index]=event.position
		if pointer_positions.size()==2:
			var fingers=pointer_positions.values();var distance=fingers[0].distance_to(fingers[1])
			if pinch_length>0:zoom_at(distance/pinch_length,(fingers[0]+fingers[1])*.5)
			pinch_length=distance;dragged=true
		elif dragged or event.position.distance_to(drag_origin)>12:dragged=true;pan(event.relative)
		accept_event()
