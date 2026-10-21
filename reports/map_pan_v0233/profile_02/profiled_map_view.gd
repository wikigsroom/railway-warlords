extends "res://presentation/map_view.gd"

static var timings: Dictionary={}
static var recording=false

func draw_static_atlas(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_static_atlas(view)
	if recording:
		if not timings.has("draw_static_atlas"):timings["draw_static_atlas"]=[]
		timings["draw_static_atlas"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_landscape(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_landscape(view)
	if recording:
		if not timings.has("draw_landscape"):timings["draw_landscape"]=[]
		timings["draw_landscape"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_cell_surface_variants(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_cell_surface_variants(view)
	if recording:
		if not timings.has("draw_cell_surface_variants"):timings["draw_cell_surface_variants"]=[]
		timings["draw_cell_surface_variants"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_cell_terrain_tiles(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_cell_terrain_tiles(view)
	if recording:
		if not timings.has("draw_cell_terrain_tiles"):timings["draw_cell_terrain_tiles"]=[]
		timings["draw_cell_terrain_tiles"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_cell_depth(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_cell_depth(view)
	if recording:
		if not timings.has("draw_cell_depth"):timings["draw_cell_depth"]=[]
		timings["draw_cell_depth"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_cell_river_details(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_cell_river_details(view)
	if recording:
		if not timings.has("draw_cell_river_details"):timings["draw_cell_river_details"]=[]
		timings["draw_cell_river_details"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_control_zones(view: Rect2, scenery_top: bool=false) -> void:
	var began=Time.get_ticks_usec()
	super.draw_control_zones(view,scenery_top)
	if recording:
		if not timings.has("draw_control_zones"):timings["draw_control_zones"]=[]
		timings["draw_control_zones"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_territory_field(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_territory_field(view)
	if recording:
		if not timings.has("draw_territory_field"):timings["draw_territory_field"]=[]
		timings["draw_territory_field"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_crossing_markers(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_crossing_markers(view)
	if recording:
		if not timings.has("draw_crossing_markers"):timings["draw_crossing_markers"]=[]
		timings["draw_crossing_markers"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_places(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_places(view)
	if recording:
		if not timings.has("draw_places"):timings["draw_places"]=[]
		timings["draw_places"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_units(view: Rect2, actors: Variant=null) -> void:
	var began=Time.get_ticks_usec()
	super.draw_units(view,actors)
	if recording:
		if not timings.has("draw_units"):timings["draw_units"]=[]
		timings["draw_units"].append((Time.get_ticks_usec()-began)/1000.0)

func draw_foreground(view: Rect2) -> void:
	var began=Time.get_ticks_usec()
	super.draw_foreground(view)
	if recording:
		if not timings.has("draw_foreground"):timings["draw_foreground"]=[]
		timings["draw_foreground"].append((Time.get_ticks_usec()-began)/1000.0)

