class_name StrategicMinimap
extends Control

signal focused(world: Vector2)
var state: Dictionary={}
var content: ContentRegistry
var map_view: MapView
var extent=Vector2.ONE
var land_surface: ArrayMesh
var water_surface: ArrayMesh
var geometry_cells: Array=[]

func _ready() -> void:custom_minimum_size=Vector2(250,140);mouse_filter=Control.MOUSE_FILTER_STOP

func update_map(s: Dictionary, registry: ContentRegistry, view: MapView) -> void:
	state=s;content=registry;map_view=view
	land_surface=view.land_surface;water_surface=view.water_surface
	if not is_same(geometry_cells,state.map.cells):
		geometry_cells=state.map.cells;extent=Vector2.ONE
		for cell in state.map.cells:
			var p=HexGrid.to_world(HexGrid.coordinate(cell.position));extent.x=maxf(extent.x,p.x+48);extent.y=maxf(extent.y,p.y+48)
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO,size),Color("377d91"))
	if state.is_empty():return
	var scale_factor=minf((size.x-16)/extent.x,(size.y-16)/extent.y);var offset=Vector2(8,8)
	draw_set_transform(offset,0,Vector2.ONE*scale_factor)
	if land_surface!=null:draw_mesh(land_surface,null,Transform2D.IDENTITY,Color("b4bd91"))
	if water_surface!=null:draw_mesh(water_surface,null,Transform2D.IDENTITY,Color("377d91"))
	if is_instance_valid(map_view) and map_view.show_control:
		if state.map.get("strategic_scale",false):
			# The continental minimap follows the same real-city Voronoi control
			# field as the main strategic view. Drawing the old tactical city rings
			# here made the field look opaque and leaked rings across the coast.
			for hex in map_view.territory_field_cells:
				var owner=str(map_view.territory_field_cells[hex]);if owner.is_empty():continue
				var center=HexGrid.to_world(hex);var polygon=HexGrid.corners(center,47.4)
				var color=map_view.faction_color(owner);color.a=MapView.TERRITORY_FIELD_OPACITY
				draw_colored_polygon(polygon,color)
		else:
			for zone in map_view.places.zones:
				var owner=map_view.places.owners.get(zone.city_id,"")
				if owner.is_empty():continue
				var color=map_view.faction_color(owner);color.a=MapView.TERRITORY_OPACITY
				draw_mesh(zone.mesh,null,Transform2D.IDENTITY,color)
	draw_set_transform(Vector2.ZERO)
	for line in state.map.render_rivers:
		var points=PackedVector2Array()
		for xy in line:points.append(Vector2(xy[0],xy[1])*scale_factor+offset)
		if points.size()>1:draw_polyline(points,Color("7da1a7"),1,true)
	for edge in state.map.rail_edges:
		if state.date<edge.active_from:continue
		var points=PackedVector2Array()
		for h in edge.path_hexes:points.append(HexGrid.to_world(HexGrid.coordinate(h))*scale_factor+offset)
		if points.size()>1:draw_polyline(points,Color("3d4030") if MovementRules.rail_available(state,edge) else Color("949080"),1.25,true)
	for city in state.cities:
		var p=HexGrid.to_world(HexGrid.coordinate(city.position))*scale_factor+offset
		draw_circle(p,3,map_view.faction_color(city.owner_id))
	for poi in state.map.get("reference_pois",[]):draw_circle(HexGrid.to_world(HexGrid.coordinate(poi.position))*scale_factor+offset,2,Color("776d58"))
	if is_instance_valid(map_view):
		var visible=Rect2((map_view.camera-map_view.size/(2*map_view.zoom))*scale_factor+offset,map_view.size/map_view.zoom*scale_factor)
		draw_rect(visible,Color("a94938"),false,1.6)
	draw_rect(Rect2(Vector2.ZERO,size),Color("bba36b"),false,3);draw_rect(Rect2(Vector2(4,4),size-Vector2(8,8)),Color("292e29"),false,1)

func _gui_input(event: InputEvent) -> void:
	if (event is InputEventMouseButton and event.pressed and event.button_index==MOUSE_BUTTON_LEFT) or (event is InputEventScreenTouch and event.pressed):
		var scale_factor=minf((size.x-16)/extent.x,(size.y-16)/extent.y);focused.emit((event.position-Vector2(8,8))/scale_factor);accept_event()
