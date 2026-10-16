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
var land_mesh: ArrayMesh
var lake_mesh: ArrayMesh
var coast_lines: Array=[]
var river_lines: Array=[]
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

func _ready() -> void:
	clip_contents=true;mouse_filter=Control.MOUSE_FILTER_STOP
	resized.connect(queue_redraw)

func configure(registry: ContentRegistry, library: AssetLibrary, text_scale: float=1.0) -> void:
	content=registry;assets=library;label_scale=text_scale

func points(coordinates: Array) -> PackedVector2Array:
	var result=PackedVector2Array()
	for xy in coordinates:result.append(Vector2(xy[0],xy[1]))
	return result

func select_scenario(id: String, owner: String) -> void:
	recipe=content.scenarios[id];selected_owner=owner
	if source_map.get("id","")!=recipe.map_id:
		source_map=content.maps[recipe.map_id];prepare_geometry();map_revision+=1
	prepare_cities();queue_redraw()

func prepare_geometry() -> void:
	var rings: Array=[];var holes: Array=[];coast_lines.clear();river_lines.clear()
	for shape in source_map.get("render_land",[]):
		rings.append(points(shape.exterior))
		for hole in shape.holes:holes.append(points(hole))
	land_mesh=AtlasSurface.build(rings,768).mesh;lake_mesh=AtlasSurface.build(holes,384).mesh
	var extent=points(source_map.get("render_extent",[]))
	bounds=Rect2(extent[0],Vector2.ONE) if not extent.is_empty() else Rect2(Vector2.ZERO,Vector2.ONE)
	for point in extent:bounds=bounds.expand(point)
	for line in source_map.get("render_coast",[]):coast_lines.append(points(line))
	for line in source_map.get("render_rivers",[]):river_lines.append(points(line))

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
		if edge.get("active_from","0000-00-00")>recipe.anchor_date:continue
		var line=PackedVector2Array()
		for hex in edge.path_hexes:line.append(HexGrid.to_world(HexGrid.coordinate(hex)))
		if line.size()>1:rail_lines.append(line)

func framing_bounds() -> Rect2:
	if not source_map.get("strategic_scale",false) or recipe.mode!="campaign" or not target_exists:return bounds
	var radius=float(recipe.get("camera_radius_hex",18+maxi(0,recipe.get("province_scope",[]).size()-1)*5))
	return Rect2(target-Vector2(72,55)*radius,Vector2(144,110)*radius).intersection(bounds)

func project(world: Vector2) -> Vector2:return world*scale_factor+map_offset

func _draw() -> void:
	if recipe.is_empty() or size.x<1 or size.y<1:return
	var frame=framing_bounds()
	scale_factor=minf((size.x-72)/maxf(1,frame.size.x),(size.y-76)/maxf(1,frame.size.y))
	map_offset=size*.5-frame.get_center()*scale_factor
	draw_rect(Rect2(Vector2.ZERO,size),Color("63858b"))
	draw_set_transform(map_offset,0,Vector2.ONE*scale_factor)
	if land_mesh!=null:draw_mesh(land_mesh,null,Transform2D.IDENTITY,Color("b5bca0"))
	if lake_mesh!=null:draw_mesh(lake_mesh,null,Transform2D.IDENTITY,Color("63858b"))
	for line in coast_lines:
		if line.size()>1:draw_polyline(line,Color("546658"),1.2/scale_factor,true)
	for line in river_lines:
		if line.size()>1:draw_polyline(line,Color("759da1"),1.3/scale_factor,true)
	for line in rail_lines:draw_polyline(line,Color("797b61"),1.3/scale_factor,true)
	draw_set_transform(Vector2.ZERO)
	# Fixed cardinal orientation and quiet edge rules keep the atlas readable
	# at a different scale without fabricating miniature terrain decorations.
	draw_rect(Rect2(Vector2(10,10),size-Vector2(20,20)),Color(.91,.90,.78,.5),false,1)
	var font_size=int(16*label_scale)
	draw_string(assets.font,Vector2(26,20+font_size),"N ↑",HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,Color("e8e8d4"))
	pin_rects.clear();var occupied: Array=[]
	var ordered=cities.duplicate();ordered.sort_custom(func(a,b):return int(a.owner==selected_owner)*10+a.level>int(b.owner==selected_owner)*10+b.level)
	for city in ordered:
		var p=project(city.at)
		if not Rect2(Vector2(22,22),size-Vector2(44,44)).has_point(p):continue
		var own=city.owner==selected_owner;var color=MapView.TERRITORY_COLORS.get(city.owner,Color("909b90"))
		var radius=7.0 if own else 4.0
		if own:draw_circle(p,radius+4,Color(.97,.91,.70,.7),false,1.4,true)
		draw_circle(p+Vector2(1,2),radius+1,Color(0,0,0,.4));draw_circle(p,radius,color)
		draw_circle(p,radius,Color("e7e3ce"),false,1,true)
		if city.playable:pin_rects.append({"rect":Rect2(p-Vector2(22,22),Vector2(44,44)),"owner":city.owner})
		if not own and city.level<2:continue
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

func _gui_input(event: InputEvent) -> void:
	if (event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT and event.pressed) or (event is InputEventScreenTouch and event.pressed):
		var nearest="";var distance=INF
		for pin in pin_rects:
			var delta=pin.rect.get_center().distance_squared_to(event.position)
			if pin.rect.has_point(event.position) and delta<distance:nearest=pin.owner;distance=delta
		if not nearest.is_empty():faction_selected.emit(nearest);accept_event()
