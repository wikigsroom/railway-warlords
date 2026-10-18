class_name MapView
extends Control

const TerrainVisuals = preload("res://presentation/terrain_visuals.gd")

signal hex_selected(hex: Vector2i)
signal place_selected(place_id: String)

const COLORS={"plain":Color("a9a58b"),"road":Color("b5ad90"),"hill":Color("8b8e75"),"forest":Color("677f67"),"mountain":Color("818373"),"peak":Color("697163"),"wetland":Color("75918b"),"city":Color("bcb190"),"river":Color("507980"),"sea":Color("466b76"),"port":Color("587a7d"),"ford":Color("879e92")}
# Presentation colors identify the actual current owner, independently of the
# historical command-marker catalog. Shared by territory, flags and minimap.
const TERRITORY_COLORS={"zhili":Color("6199d0"),"fengtian":Color("dc826c"),"anhui":Color("a08ccc"),"shanxi":Color("e1ba5c"),"guominjun":Color("55b5ae"),"jiangsu":Color("d19d56"),"zhejiang":Color("7cb57e"),"yunnan":Color("7f9bb4"),"guangdong":Color("cf9bb7"),"dongjiang":Color("af83b3"),"sichuan":Color("a7b96b"),"guangxi":Color("53a899"),"hunan":Color("ccad8a"),"gansu":Color("bc8165"),"qing":Color("4c6675"),"british_empire":Color("b26b4b"),"british_india":Color("a36b50"),"french_empire":Color("6b6fa3"),"french_indochina":Color("6c6c95"),"russian_empire":Color("6e7e9b"),"russian_provisional":Color("7c8d9c"),"soviet":Color("a64c52"),"japan":Color("b7534b"),"korea":Color("887c62"),"ottoman":Color("80676e"),"qajar_persia":Color("92704f"),"afghanistan":Color("6e7c58"),"siam":Color("7c8e5d"),"thailand":Color("718a5c"),"netherlands":Color("9a6c61"),"spain":Color("a77a54"),"portugal":Color("8c6d77"),"taiping":Color("6b5591"),"boxers":Color("9d5a3c"),"eight_nation":Color("536f8a"),"germany":Color("55636f"),"italy":Color("71866c"),"usa":Color("6d83a4"),"beiyang_gov":Color("536d7f"),"guangzhou_government":Color("8f6b4a"),"bolsheviks":Color("a54d52"),"mongolia":Color("887253"),"tibet":Color("7b8064"),"kmt":Color("4c6fa1"),"ccp":Color("a3544c"),"japanese_occupied":Color("98524a"),"vichy_france":Color("6f7090"),"nguyen_dynasty":Color("786b52"),"burmese_kingdom":Color("7a7654"),"sikh_empire":Color("a17b4f")}
# EW6-style ownership wash: the surveyed land, rivers and terrain remain
# readable beneath the current-owner tint. Borders and the legend carry the
# stronger faction cue; the fill itself is intentionally translucent.
const TERRITORY_OPACITY=.26
# Continental and local control use mutually exclusive coverage layers. The
# broad field keeps the landscape visible without stacking city influences.
const TERRITORY_FIELD_OPACITY=.21
const TERRITORY_FIELD_BORDER_OPACITY=.42
var content: ContentRegistry
var assets: AssetLibrary
var state: Dictionary={}
var camera=Vector2.ZERO
var zoom=1.0
var selected_unit_id=""
var selected_city_id=""
var selected_place_id=""
var selected_terrain_hex: Variant=null
var unit_headings: Dictionary={}
var heading_match_id=""
var heading_memory_authoritative=false
var hud_map_rect=Rect2()
var show_places=true
var show_control=true
var show_terrain=true
var places=HistoricalPlaces.new()
var place_references: Array=[]
var settlement_choices: Dictionary={}
var reachable: Dictionary={}
var pending_hex: Variant=null
var show_rail=true
var show_supply=false
var label_obstacle_controls: Array=[]
var show_grid=false
var visible_ids: Dictionary={}
var dragging=false
var drag_origin=Vector2.ZERO
var last_pointer=Vector2.ZERO
var pointers: Dictionary={}
var pinch_distance=0.0
var touch_dragged=false
var effects: Array=[]
var pulse=0.0
var geography_key=""
var administration_key=""
var land_shapes: Array=[]
var land_surface: ArrayMesh
var water_surface: ArrayMesh
var extent_surface: ArrayMesh
var surface_diagnostics: Dictionary={}
var coast_lines: Array=[]
var river_lines: Array=[]
var river_stream_orders: Array=[]
var river_rows: Array=[]
var river_surface_draw_count=0
var river_texture_draw_count=0
var river_ink_draw_count=0
var water_source_texture: Texture2D
var detail_river_lines: Array=[]
var detail_river_buckets: Dictionary={}
var crossing_markers: Array=[]
var historical_landcover_features: Array=[]
var historical_landcover_patch_cells=0
var terrain_feature_sprite_draw_count=0
var region_lines: Array=[]
var world_bounds=Rect2()
var camera_bounds=Rect2()
var camera_bounds_source="full_map"
var rail_cells: Dictionary={}
var presentation_cells: Dictionary={}
var terrain_visual_buckets: Dictionary={}
var map_extent=PackedVector2Array()
var minimap: StrategicMinimap
var relief=AtlasRelief.new()
var continuous_relief_enabled=true
var map_details=MapDetails.new()
var surface_region_diagnostics: Dictionary={}
var hydrography_diagnostics: Dictionary={}
var label_scale=1.0
var drawn_labels: Array=[]
var label_revision=0
var label_cache_revision=-1
var label_cache_state: Dictionary={}
var label_cache_selection=""
var label_city_nodes: Array=[]
var label_place_nodes: Array=[]
var label_unit_points: Array=[]
var label_text_widths: Dictionary={}
var playback=BattlePlayback.new()
var playback_paused=false
var cinema: BattleCinema
var attack_targets: Dictionary={}
var command_preview: Dictionary={}
var static_only=false
var static_units_only=false
var unit_viewport: SubViewport
var unit_view: MapView
var unit_signature=""
var unit_camera=Vector2.ZERO
var unit_zoom=1.0
var unit_dimensions=Vector2.ZERO
var unit_rebuilds=0
var unit_layers: Array=[]
var unit_segments: Array=[]
var unit_actors: Array=[]
var unit_source_override: Array=[]
var unit_ready_hidden=false
var unit_actor_views: Array=[]
var static_foreground_only=false
var foreground_view: MapView
var drawn_unit_count=0
var drawn_unit_counter_ids: Array=[]
var drawn_unit_detail_ids: Array=[]
var drawn_city_counter_ids: Array=[]
var drawn_city_detail_ids: Array=[]
var drawn_place_counter_ids: Array=[]
var drawn_place_detail_ids: Array=[]
var live_actor_draw_count=0
var unit_cache_enabled=true
var ordered_unit_source: Array=[]
var ordered_unit_positions=PackedFloat32Array()
var ordered_unit_records: Array=[]
var shadow_mesh: ArrayMesh
var backdrop_viewport: SubViewport
var backdrop_view: MapView
var backdrop_signature=""
var backdrop_camera=Vector2.ZERO
var backdrop_zoom=1.0
var backdrop_dimensions=Vector2.ZERO
var annotation_view_size=Vector2.ZERO
var backdrop_rebuilds=0
var profile_draw_enabled="--profile-draw" in OS.get_cmdline_user_args()
var profile_draw_samples: Array=[]
var profile_shadow_usec=0
var profile_sort_usec=0
var terrain_tile_draw_count=0
var terrain_transition_draw_count=0
var terrain_symbol_draw_count=0
var terrain_scenery_draw_count=0
var terrain_surface_variant_draw_count=0
var ground_material_batches: Array=[]
var city_control_fill_draw_count=0
var territory_field_fill_draw_count=0
var terrain_depth_draw_count=0
var terrain_cell_river_draw_count=0
var terrain_micro_symbol_draw_count=0
# A bounded evidence renderer for the full 74k-cell strategic map.  It keeps
# the authored land/coast/river meshes and the real historical control zones,
# while omitting the expensive relief mesh and overview lattice for this one
# native pixel proof.  Normal Windows and Android play never enable it.
var territory_qa_mode=false
var territory_field_meshes: Dictionary={}
var territory_field_cells: Dictionary={}
var territory_field_borders: Array=[]
var territory_field_diagnostics: Dictionary={}
var territory_field_signature=""

func setup(registry: ContentRegistry, library: AssetLibrary) -> void:
	content=registry;assets=library;mouse_filter=Control.MOUSE_FILTER_STOP
	clip_contents=true;set_process(true)
	texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	backdrop_viewport=SubViewport.new();backdrop_viewport.disable_3d=true;backdrop_viewport.gui_disable_input=true
	backdrop_viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;add_child(backdrop_viewport)
	backdrop_view=get_script().new();backdrop_view.static_only=true;backdrop_view.assets=assets;backdrop_view.content=content
	backdrop_view.clip_contents=true;backdrop_view.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	backdrop_viewport.add_child(backdrop_view);backdrop_view.set_process(false)
	unit_viewport=SubViewport.new();unit_viewport.disable_3d=true;unit_viewport.gui_disable_input=true;unit_viewport.transparent_bg=true
	unit_viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;add_child(unit_viewport)
	unit_view=get_script().new();unit_view.static_units_only=true;unit_view.assets=assets;unit_view.content=content
	unit_view.clip_contents=true;unit_viewport.add_child(unit_view);unit_view.set_process(false)
	unit_layers.append(make_unit_layer(unit_viewport,unit_view))
	foreground_view=get_script().new();foreground_view.static_foreground_only=true;foreground_view.content=content;foreground_view.assets=assets
	foreground_view.clip_contents=true;foreground_view.mouse_filter=Control.MOUSE_FILTER_IGNORE;foreground_view.z_index=10
	add_child(foreground_view);foreground_view.set_process(false)
	cinema=BattleCinema.new();cinema.z_index=15;cinema.assets=assets;cinema.content=content;cinema.playback=playback;add_child(cinema)
	cinema.z_index=20
	cinema.anchor_left=.5;cinema.anchor_right=.5;cinema.anchor_top=1;cinema.anchor_bottom=1
	cinema.offset_left=-360;cinema.offset_right=360;cinema.offset_top=-318;cinema.offset_bottom=-18

func set_state(value: Dictionary, events: Array = [], prepared: Dictionary = {}) -> void:
	state=value;unit_signature="";ordered_unit_source=[];label_revision+=1
	update_unit_headings(value,events)
	if geography_key!=geography_signature():prepare_geography()
	elif administration_key!=ContentRegistry.administration_year(state.date):prepare_administration()
	prepare_camera_bounds()
	places.update_owners(state);place_references=places.references(state)
	prepare_territory_field()
	if not prepared.is_empty():
		visible_ids=prepared.visible_ids
	else:
		visible_ids={}
		for sight in state.visibility:
			if sight.faction_id==state.player_faction_id:
				for id in sight.visible_cell_ids:visible_ids[id]=true
	# New commands can alter fog, railway availability or ownership. Redraw once
	# instead of deeply comparing 74762 IDs and complete copied railway routes.
	backdrop_signature=""
	queue_redraw()
	if is_instance_valid(minimap):minimap.update_map(state,content,self)

func restore_headings(memory: FacingMemory) -> void:
	unit_headings=memory.vectors();heading_match_id=memory.match_id
	heading_memory_authoritative=true;unit_signature=""

func update_unit_headings(next_state: Dictionary, events: Array) -> void:
	# Facing is presentation state, so it survives the end of a move/attack while
	# the authoritative unit position, AP and random stream remain untouched.
	# Existing authored fallback views seed the initial formation direction.
	var match_id=str(next_state.get("match_id",next_state.get("scenario_id","")))
	if match_id!=heading_match_id:
		unit_headings.clear();heading_match_id=match_id
	if events.is_empty():
		for unit in next_state.get("units",[]):
			if unit_headings.has(unit.id):continue
			var fallback=str(unit.get("facing","se"))
			# The rules layer stores the historical diagonal formation facing.  The
			# presentation layer resolves that into an authored cardinal source view
			# so an idle formation has a stable, readable front instead of sharing the
			# same diagonal sprite as every other unit.
			unit_headings[unit.id]=heading_for_source(fallback)
		# Recent committed events are serialized with the match. Rebuild visual
		# direction on a fresh map after loading, without changing rule state.
		if not heading_memory_authoritative:apply_heading_events(next_state.get("event_log",[]))
		return
	apply_heading_events(events)
	for unit in next_state.get("units",[]):
		if unit_headings.has(unit.id):continue
		unit_headings[unit.id]=heading_for_source(str(unit.get("facing","se")))

func heading_for_source(direction: String) -> Vector2:
	return {"n":Vector2.UP,"e":Vector2.RIGHT,"s":Vector2.DOWN,"w":Vector2.LEFT,"sw":Vector2(-1,0),"se":Vector2(1,0)}.get(direction,Vector2.RIGHT)

func apply_heading_events(events: Array) -> void:
	for event in events:
		var kind=str(event.get("type",""))
		if kind in ["UnitMoved","RailTransported","MoveUndone","Disembarked","EmergencyDisembark"]:
			var path: Array=event.get("path",[])
			if path.size()<2:
				path=[event.get("from"),event.get("position")]
			if path.size()>=2 and path[-2]!=null and path[-1]!=null:
				var from=HexGrid.to_world(HexGrid.coordinate(path[-2]));var to=HexGrid.to_world(HexGrid.coordinate(path[-1]))
				if to.distance_squared_to(from)>.01:unit_headings[str(event.get("unit_id",""))]=(to-from).normalized()
		elif kind=="CombatDiceRolled":
			var from_hex=event.get("from");var target_hex=event.get("position")
			if from_hex!=null and target_hex!=null:
				var from=HexGrid.to_world(HexGrid.coordinate(from_hex));var target=HexGrid.to_world(HexGrid.coordinate(target_hex));var direction=(target-from).normalized()
				var attacker_id=str(event.get("attacker_id",""));var target_id=str(event.get("target_id",""))
				if not attacker_id.is_empty():unit_headings[attacker_id]=direction
				if not target_id.is_empty():unit_headings[target_id]=-direction
		elif kind=="DamageApplied":
			var from_hex=event.get("from");var target_hex=event.get("position")
			if from_hex!=null and target_hex!=null:
				var from=HexGrid.to_world(HexGrid.coordinate(from_hex));var target=HexGrid.to_world(HexGrid.coordinate(target_hex));var direction=(target-from).normalized()
				var attacker_id=str(event.get("attacker_id",""));var target_id=str(event.get("unit_id",""))
				if not attacker_id.is_empty():unit_headings[attacker_id]=direction
				if not target_id.is_empty():unit_headings[target_id]=-direction

func geography_signature() -> String:
	var key=str(state.map.id)+str(state.content_hash)
	if state.map.get("id","")=="asia_strategic":
		# The dated 1922 grove must appear when its source becomes valid, including
		# a calendar transition in the same match. Other maps reuse their mesh.
		key+=(":after1922" if str(state.date)>="1922-01-01" else ":before1922")
	return key

func presentation_source_map_id() -> String:
	# An explicit QA fixture retains the production geometry byte-for-byte.
	# It must exercise the same material and river layers as that source map.
	return str(state.map.get("fixture_source",{}).get("production_map_id",state.map.id))

func prepare_geography() -> void:
	geography_key=geography_signature();land_shapes.clear();coast_lines.clear();river_lines.clear();detail_river_lines.clear();crossing_markers.clear();rail_cells.clear()
	presentation_cells.clear();terrain_visual_buckets.clear();historical_landcover_features.clear();historical_landcover_patch_cells=0
	load_historical_landcover_features()
	territory_field_meshes.clear();territory_field_cells.clear();territory_field_borders.clear();territory_field_diagnostics={};territory_field_signature=""
	world_bounds=Rect2(HexGrid.to_world(HexGrid.coordinate(state.map.cells[0].position)),Vector2.ONE)
	for cell in state.map.cells:
		var h=HexGrid.coordinate(cell.position)
		# All source maps stay immutable. Regional material references and dated
		# woodland symbols live exclusively in these presentation copies.
		var visual_cell: Dictionary=cell.duplicate(true)
		presentation_cells[h]=visual_cell
		world_bounds=world_bounds.expand(HexGrid.to_world(h))
	apply_named_landcover_classes()
	surface_region_diagnostics=MapSurfaceRegions.apply(presentation_cells,presentation_source_map_id())
	surface_region_diagnostics["terrain_subtypes"]=MapTerrainSurfaces.apply(presentation_cells,presentation_source_map_id())
	for h in presentation_cells:
		var visual_cell: Dictionary=presentation_cells[h]
		var terrain_kind=TerrainVisuals.kind_for_cell(visual_cell)
		var bucket=Vector2i(floori(float(h.x)/16.0),floori(float(h.y)/16.0))
		if not terrain_visual_buckets.has(bucket):terrain_visual_buckets[bucket]=[]
		terrain_visual_buckets[bucket].append({"hex":h,"kind":terrain_kind,"cell":visual_cell})
	world_bounds=world_bounds.grow(48)
	map_extent=points_array(state.map.get("render_extent",[]))
	for shape in state.map.get("render_land",[]):land_shapes.append({"exterior":points_array(shape.exterior),"holes":shape.holes.map(points_array)})
	var holes: Array=[]
	for shape in land_shapes:holes.append_array(shape.holes)
	var land=AtlasSurface.build(land_shapes.map(func(shape):return shape.exterior),768)
	var clipped=MapControlLandClip.for_map(state.map)
	var water: Dictionary
	if clipped.is_empty():water=AtlasSurface.build(holes,MapRiverSurface.TEXTURE_PERIOD)
	else:
		water={"mesh":MapControlLandClip.inland_water_mesh(clipped,MapRiverSurface.TEXTURE_PERIOD),"rings":holes.size(),
			"triangles":MapControlLandClip.vertices(clipped.inland_water).size()/3,"errors":[]}
	var extent=AtlasSurface.build([map_extent] if map_extent.size()>=3 else [],MapRiverSurface.TEXTURE_PERIOD)
	land_surface=land.mesh;water_surface=water.mesh;extent_surface=extent.mesh
	surface_diagnostics={"land_rings":land.rings,"land_triangles":land.triangles,"water_rings":water.rings,"errors":land.errors+water.errors+extent.errors}
	if not surface_diagnostics.errors.is_empty():push_error("Surveyed atlas surface failed: "+state.map.id+" "+str(surface_diagnostics.errors))
	for line in state.map.render_coast:coast_lines.append(points_array(line))
	var hydro=MapHydrography.build(state.map,presentation_source_map_id())
	river_lines=hydro.major;river_stream_orders=hydro.major_orders;river_rows=hydro.major_rows;detail_river_lines=hydro.detail;hydrography_diagnostics=hydro.diagnostics
	detail_river_buckets=MapHydrography.spatial_index(detail_river_lines)
	for crossing in state.map.get("crossings",[]):
		var from=HexGrid.to_world(HexGrid.coordinate(crossing.get("from",{})));var to=HexGrid.to_world(HexGrid.coordinate(crossing.get("to",{})))
		crossing_markers.append({"from":from,"to":to,"kind":str(crossing.get("kind","bridge")),"intact":bool(crossing.get("intact",true)),"rail_allowed":bool(crossing.get("rail_allowed",false))})
	prepare_administration(false)
	for edge in state.map.rail_edges:
		for position in edge.path_hexes:rail_cells[HexGrid.key(HexGrid.coordinate(position))]=true
	if territory_qa_mode:
		# Relief is a presentation cache built from every strategic cell. It is
		# useful in the game viewport, but the QA pass only needs the sourced
		# geography and current-owner fills, so leave the cache empty here.
		relief=AtlasRelief.new()
		map_details=MapDetails.new()
	else:
		relief.build(state.map,land_shapes,river_lines,detail_river_lines.map(func(row):return row.points))
		map_details.build(state.map,presentation_cells,relief,coast_lines,river_lines+detail_river_lines.map(func(row):return row.points))
	places.prepare(state.map,state.date)
	prepare_place_sprites()
	camera_bounds=world_bounds;camera_bounds_source="full_map"

func load_historical_landcover_features() -> void:
	# Only named, sourced sites are allowed into the strategic forest layer.
	# This is deliberately separate from rule cells: it cannot invent a biome,
	# alter movement, or imply continuous historical land-cover coverage.
	var path="res://presentation/data/asia_landcover_features.json"
	if not FileAccess.file_exists(path) or state.map.get("id","")!="asia_strategic":return
	var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:return
	for feature in parsed.get("features",[]):
		var year=int(str(state.date).substr(0,4))
		if year<int(feature.get("valid_from",0)) or year>int(feature.get("valid_to",9999)):continue
		if feature.get("world_position",[]).size()!=2:continue
		historical_landcover_features.append(feature.duplicate(true))

func apply_named_landcover_classes() -> void:
	# Convert only the documented radius around a named, time-valid forest/grove
	# landmark into a visual forest class. This is deliberately presentation
	# data: the state map, terrain costs and movement rules remain unchanged.
	if historical_landcover_features.is_empty() or presentation_cells.is_empty():return
	for feature in historical_landcover_features:
		var kind=str(feature.get("kind",""))
		if kind not in ["forest","grove"]:continue
		var source_id=str(feature.get("id",""))
		var world_position=feature.get("world_position",[])
		if world_position.size()<2:continue
		var anchor_hex=HexGrid.from_world(Vector2(float(world_position[0]),float(world_position[1])))
		var radius=maxi(0,int(feature.get("presentation_radius_hex",1)))
		for dq in range(-radius,radius+1):
			for dr in range(-radius,radius+1):
				if absi(dq)+absi(dr)+absi(dq+dr)>radius*2:continue
				var hex=anchor_hex+Vector2i(dq,dr)
				if not presentation_cells.has(hex):continue
				var cell: Dictionary=presentation_cells[hex]
				var detailed=str(cell.get("terrain_id",""));var natural=str(cell.get("natural_terrain_id",detailed))
				# Never paint a source landmark over a real waterway, road, city,
				# port or ford. Those geographic/strategic facts must remain legible.
				if detailed in TerrainVisuals.FEATURE_KINDS or natural=="sea" or detailed=="sea":continue
				if not cell.get("render_land_covered",true):continue
				if not cell.has("presentation_terrain_id"):
					cell["presentation_terrain_id"]="forest"
					cell["presentation_terrain_source"]=source_id
					cell["presentation_forest_asset"]=str(feature.get("scenery_asset",""))

func prepare_camera_bounds() -> void:
	# A historical campaign can use the continental map as its source while the
	# playable camera stays inside the authored theatre. Free-world/conquest
	# keeps the full Asia strategic layer. Tactical maps already have their own
	# local world extent and therefore need no synthetic crop.
	camera_bounds=world_bounds;camera_bounds_source="full_map"
	if state.is_empty() or not state.map.get("strategic_scale",false) or state.get("mode","")!="campaign":return
	var recipe=content.scenarios.get(state.get("scenario_id",""),{})
	var anchor: Variant=null
	var target_id=str(recipe.get("target_city_id",""))
	for city in state.map.get("cities",[]):
		if city.id==target_id:anchor=city.position;break
	if anchor==null:
		for city in state.get("cities",[]):
			if city.id==target_id:anchor=city.position;break
	if anchor==null:return
	var scope_count=maxi(1,recipe.get("province_scope",[]).size())
	# The theatre is intentionally wide enough for a desktop tactical view while
	# remaining a local campaign map. Additional period provinces add a controlled
	# ring around the target; the continental free-world layer is never exposed by
	# a campaign drag.
	var radius=18.0+float(scope_count-1)*5.0
	if recipe.has("camera_radius_hex"):radius=float(recipe.camera_radius_hex)
	var center=HexGrid.to_world(HexGrid.coordinate(anchor))
	var half=Vector2(72.0*radius,55.0*radius)
	var candidate=Rect2(center-half,half*2.0)
	var clipped=candidate.intersection(world_bounds)
	if clipped.has_area():
		camera_bounds=clipped.grow(48.0)
		camera_bounds_source="campaign_theatre:%s:%dhex"%[target_id,int(radius)]

func prepare_place_sprites() -> void:
	settlement_choices={}
	if MapArtBank.available():
		var candidates: Array=[]
		for node in places.nodes:
			# Source locations and actual roles select the family. Precomputing the
			# station/dock alternatives keeps future construction stable as well.
			for role in ["","station","dock"]:
				var family=MapArtBank.settlement_family(node,state.date,role)
				if not family.is_empty():candidates.append({"key":node.id+":"+role,"family":family,"position":node.at})
		settlement_choices=MapArtBank.assign(candidates,450.0)
	for node in places.nodes:
		var rank=HistoricalPlaces.importance(node,state.date)
		var bounds=Vector2(78,58) if rank==1 else Vector2(104,78) if rank==2 else Vector2(118,94) if rank==3 else Vector2(136,116)
		var footprint=Rect2(node.at+Vector2(0,-12)-bounds*.5,bounds)
		var bank_id=str(settlement_choices.get(node.id+":",""))
		if not bank_id.is_empty():
			node["bank_asset_id"]=bank_id
			var rectangle=MapArtBank.source_rect(bank_id,bounds)
			node["bank_texture_rect"]=rectangle
			footprint=Rect2(node.at+Vector2(0,26)+rectangle.position,rectangle.size)
		node["sprite_bounds"]=bounds
		node["sprite_on_land"]=true if state.map.get("strategic_scale",false) else relief.dry_point(footprint.position) and relief.dry_point(footprint.end) and relief.dry_point(Vector2(footprint.end.x,footprint.position.y)) and relief.dry_point(Vector2(footprint.position.x,footprint.end.y)) and not relief.intersects_index(footprint,relief.boundary_buckets,0)

func prepare_administration(refresh_places: bool=true) -> void:
	administration_key=ContentRegistry.administration_year(state.date);region_lines.clear()
	for region in state.map.get("admin_layers",{}).get(administration_key,[]):
		for line in region.lines:region_lines.append(points_array(line))
	if refresh_places and not places.map_key.is_empty():places.prepare(state.map,state.date);prepare_place_sprites()

func points_array(coordinates: Array) -> PackedVector2Array:
	var points=PackedVector2Array()
	for xy in coordinates:points.append(Vector2(xy[0],xy[1]))
	return points

func map_place_visible(node: Dictionary) -> bool:
	if not HistoricalPlaces.visible_at(node,state.date,zoom,selected_place_id):return false
	if not state.map.get("strategic_scale",false):return true
	# EW6's continental atlas keeps the strategic canvas quiet and promotes
	# cities/ports as the camera approaches. The authored node is still present
	# and becomes selectable at its normal tactical threshold.
	var rank=HistoricalPlaces.importance(node,state.date)
	if zoom<.18:return rank>=5 or node.get("id","")==selected_place_id
	if zoom<.28:return rank>=4 or node.get("id","")==selected_place_id
	if zoom<.42:return rank>=3 or node.get("id","")==selected_place_id
	return true

func focus_player() -> void:
	if state.is_empty():return
	var recipe=content.scenarios[state.scenario_id]
	var own=state.units.filter(func(u):return u.owner_id==state.player_faction_id and u.position!=null)
	if state.mode=="conquest":
		var city=StateAccess.nearest_city(state,HexGrid.coordinate(own[0].position),state.player_faction_id) if not own.is_empty() else {}
		zoom=.65;focus_world(HexGrid.to_world(HexGrid.coordinate(city.position)) if not city.is_empty() else Vector2(1200,1000))
	else:
		var city=StateAccess.find(state,"cities",recipe.target_city_id)
		var at=HexGrid.to_world(HexGrid.coordinate(city.position)) if not city.is_empty() else world_bounds.get_center()
		if not own.is_empty():
			var first=HexGrid.to_world(HexGrid.coordinate(own[0].position));var army=Rect2(first,Vector2.ONE)
			for unit in own:
				var point=HexGrid.to_world(HexGrid.coordinate(unit.position))
				if point.distance_to(first)<1600:army=army.expand(point)
			army=army.grow(100)
			var area=map_hud_area().grow(-48)
			# Include the objective when it is locally reachable in this opening
			# view. A distant campaign objective must not shrink the army to dots.
			if at.distance_to(army.get_center())<minf(area.size.x,area.size.y)/.65:army=army.expand(at).grow(36)
			zoom=clampf(minf(area.size.x/maxf(1,army.size.x),area.size.y/maxf(1,army.size.y)),.48,.90)
			focus_world(army.get_center())
		else:zoom=.76;focus_world(at)

func focus_world(world: Vector2) -> void:
	# The unobscured playfield has a different centre from the full viewport.
	# Keep the selected city/army there, rather than beneath the right inspector.
	camera=world-(map_hud_area().get_center()-size*.5)/zoom
	clamp_camera();queue_redraw()

func screen_to_hex(screen: Vector2) -> Vector2i:return HexGrid.from_world((screen-size*.5)/zoom+camera)
func world_to_screen(world: Vector2) -> Vector2:return (world-camera)*zoom+size*.5

func map_bank_capture_facts() -> Dictionary:
	if not MapArtBank.available():return {"active":false}
	var view=Rect2(camera-size/(2*zoom),size/zoom)
	var scenery=relief.visible_features(view)+map_details.visible_features(view,zoom)
	var uses: Dictionary={};var families: Dictionary={};var positions: Dictionary={}
	for feature in scenery:
		var id=str(feature.asset_id)
		uses[id]=int(uses.get(id,0))+1
		families[feature.family]=int(families.get(feature.family,0))+1
		if not positions.has(id):positions[id]=[]
		positions[id].append(feature.position)
	var nearest=INF;var nearby_pairs=0
	for id in positions:
		var points: Array=positions[id]
		for a in range(points.size()):
			for b in range(a+1,points.size()):
				var distance=points[a].distance_to(points[b]);nearest=minf(nearest,distance)
				if distance<250.0:nearby_pairs+=1
	var buildings: Dictionary={}
	for node in places.references(state):
		if view.has_point(node.at) and node.get("sprite_on_land",true) and HistoricalPlaces.visible_at(node,state.date,zoom,selected_place_id):
			var id=str(node.get("bank_asset_id",""))
			if not id.is_empty():buildings[node.id]=id
	for city in state.cities:
		if city.fort_hp<=0 or city.id in ["jiumenkou","shanhaiguan"] or not view.has_point(HexGrid.to_world(HexGrid.coordinate(city.position))):continue
		var role="station" if EconomyRules.building_level(city,"station")>0 and HistoricalPlaces.kind(city,state.date)=="city" else "dock" if city.get("port",false) and HistoricalPlaces.kind(city,state.date) not in ["national_capital","capital"] else ""
		var id=str(settlement_choices.get(city.id+":"+role,""))
		if not id.is_empty():buildings[city.id]=id
	var materials: Dictionary={};var material_ids: Dictionary={}
	for entry in visible_terrain_entries(view):
		var key=HexGrid.key(entry.hex);var family=str(map_details.surface_families.get(key,""))
		if family.is_empty():continue
		materials[family]=int(materials.get(family,0))+1
		material_ids[map_details.surfaces.get(key,"")]=true
	var hydro_facts=MapHydrography.facts(detail_river_lines,detail_river_buckets,hydrography_diagnostics,view,zoom,state.map.get("strategic_scale",false))
	var water_renderer=backdrop_view if is_instance_valid(backdrop_view) and not static_only else self
	hydro_facts["river_surface"]={"renderer":"source_centerline_gradient_ribbon","water_texture_id":MapRiverSurface.TEXTURE_ID,"world_texture_period":MapRiverSurface.TEXTURE_PERIOD,"drawn_watercourses":water_renderer.river_surface_draw_count,"drawn_gradient_ribbons":water_renderer.river_surface_draw_count-water_renderer.river_ink_draw_count,"drawn_antialiased_headwaters":water_renderer.river_ink_draw_count,"drawn_textured_ribbons":water_renderer.river_texture_draw_count,"primary_width_from_vertex_count":false,"measured_banks_claimed":false}
	hydro_facts.river_surface["headwater_style"]="muted_waterbed_with_translucent_riparian_halo"
	hydro_facts.river_surface["detail_banks_drawn_before_water"]=true
	var subtype_facts=terrain_surface_capture_facts(view)
	var lighting=relief.shade_field.facts()
	lighting["shader_active"]=water_renderer.material!=null and bool(water_renderer.material.get_shader_parameter("relief_enabled"))
	subtype_facts["relief_lighting"]=lighting
	return {"active":true,"catalog_additional_sources":MapArtBank.data().records.size(),"catalog_map_assets":MapArtBank.data().total_map_assets,"terrain_surface_extension":subtype_facts,"map_symbols":map_symbol_capture_facts(),"current_total_map_assets":int(MapArtBank.data().total_map_assets)+int(subtype_facts.independent_originals)+int(subtype_facts.macro_originals),"camera":[camera.x,camera.y],"zoom":zoom,"scenery_instances_intersecting_view":scenery.size(),"distinct_scenery_originals_intersecting_view":uses.size(),"source_use_counts":uses,"families":families,"same_source_pairs_under_250_world_units":nearby_pairs,"nearest_repeated_source_distance_world":nearest if is_finite(nearest) else null,"settlement_sources":buildings,"surface_material_families_in_view":materials,"distinct_surface_originals_in_view":material_ids.size(),"surface_geography":surface_region_diagnostics,"hydrography":hydro_facts,"source_images_modified":false,"measurement_scope":"Actual source-ID selections intersecting the world viewport; HUD occlusion is not subtracted. Count is not an artistic-quality or historical-coverage score."}

func map_symbol_capture_facts() -> Dictionary:
	var counters: Array=[];var details: Array=[]
	if uses_unit_cache():
		for index in range(unit_segments.size()):
			counters.append_array(unit_layers[index].view.drawn_unit_counter_ids);details.append_array(unit_layers[index].view.drawn_unit_detail_ids)
		for actor in unit_actor_views:
			if actor.visible:counters.append_array(actor.drawn_unit_counter_ids);details.append_array(actor.drawn_unit_detail_ids)
	else:
		counters=drawn_unit_counter_ids.duplicate();details=drawn_unit_detail_ids.duplicate()
	var source=playback.units if playback.active else state.units
	var index: Dictionary={}
	for unit in source:index[unit.id]=unit
	var viewport=Rect2(Vector2.ZERO,size)
	var visible=func(id):
		if not index.has(id) or index[id].position==null:return false
		var point=playback.position_of(index[id]) if playback.active else HexGrid.to_world(HexGrid.coordinate(index[id].position))
		return viewport.has_point(world_to_screen(point))
	counters=counters.filter(visible);details=details.filter(visible)
	return {"zoom_band":MapSemanticZoom.band(zoom),"detail_threshold":MapSemanticZoom.DETAIL_ZOOM,"regional_threshold":MapSemanticZoom.REGIONAL_ZOOM,"unit_counter_ids":counters,"unit_detail_ids":details,"city_counter_ids":drawn_city_counter_ids.duplicate(),"city_detail_ids":drawn_city_detail_ids.duplicate(),"place_counter_ids":drawn_place_counter_ids.duplicate(),"place_detail_ids":drawn_place_detail_ids.duplicate(),"unit_counter_screen_size":[MapSemanticZoom.unit_size(zoom).x,MapSemanticZoom.unit_size(zoom).y],"background_legacy_terrain_symbols":backdrop_view.terrain_symbol_draw_count if backdrop_view!=null else terrain_symbol_draw_count,"background_painted_scenery":backdrop_view.terrain_scenery_draw_count if backdrop_view!=null else terrain_scenery_draw_count,"source_units_removed":false,"rule_positions_changed":false,"units_aggregated":false,"scope":"Actual draw IDs in the unit layers, filtered to anchors in this viewport; HUD occlusion is not subtracted."}

func terrain_surface_capture_facts(view: Rect2) -> Dictionary:
	var type_counts: Dictionary={};var source_counts: Dictionary={};var repeated=0;var pairs=0;var macro_sources: Dictionary={}
	for entry in visible_terrain_entries(view):
		var key=HexGrid.key(entry.hex);var id=str(map_details.surfaces.get(key,""))
		if not id.begins_with("tile_surface_"):continue
		var family=str(map_details.surface_families.get(key,""))
		var macro=MapTerrainSurfaces.macro_id(family)
		if not macro.is_empty():macro_sources[macro]=true
		type_counts[family]=int(type_counts.get(family,0))+1;source_counts[id]=int(source_counts.get(id,0))+1
		for direction in [Vector2i(1,0),Vector2i(0,1),Vector2i(-1,1)]:
			var other=str(map_details.surfaces.get(HexGrid.key(entry.hex+direction),""))
			if not other.begins_with("tile_surface_"):continue
			pairs+=1
			if id==other:repeated+=1
	return {"active":MapTerrainSurfaces.available(),"registered_types":MapTerrainSurfaces.data().get("types",{}).size(),"independent_originals":MapTerrainSurfaces.data().get("records",{}).size(),"macro_originals":MapTerrainSurfaces.macro_data().get("records",{}).size(),"macro_identity_revision":MapTerrainSurfaces.macro_data().get("material_identity_revision",""),"stored_superseded_macro_originals":MapTerrainSurfaces.macro_data().get("superseded_originals",0),"visible_macro_sources":macro_sources.keys(),"macro_repeat_world_units":MapTerrainSurfaces.macro_data().get("world_repeat_period",0),"fine_detail_alpha":MapTerrainSurfaces.detail_alpha(bool(state.map.get("strategic_scale",false))),"visible_types":type_counts,"source_use_counts":source_counts,"checked_adjacent_pairs":pairs,"same_original_on_adjacent_cells":repeated,"ground_alpha":MapTerrainSurfaces.alpha_for("temperate_meadow",bool(state.map.get("strategic_scale",false))),"blend_inner_ratio":MapDetails.SURFACE_BLEND_INNER,"continuous_ground":continuous_ground_facts(),"rule_geometry_changed":false}

func continuous_ground_facts() -> Dictionary:
	var renderer=backdrop_view if is_instance_valid(backdrop_view) and not static_only else self
	return {"active":renderer.material!=null,"source_layers":GroundMaterialBlend.source_layers().size(),"whole_original_dimensions":[1254,1254],"macro_coverage":"nonoverlapping_hex_partition_with_three_source_blending","source_ground_coverage":MapGroundCoverage.diagnostics(map_details.source_ground_coverage),"ground_material_policy":map_details.ground_policy,"source_images_modified":false,"city_influence_fill_draws":renderer.city_control_fill_draw_count,"field_fill_batches":renderer.territory_field_fill_draw_count}

func place_at_screen(screen: Vector2) -> String:
	if not show_places or not selected_unit_id.is_empty():return ""
	var best=28.0;var result=""
	for node in place_references:
		if not map_place_visible(node):continue
		var distance=world_to_screen(node.at).distance_to(screen)
		if distance<best:best=distance;result=node.id
	return result

func select_screen(screen: Vector2) -> void:
	# Compact formations have precise geographic anchors. Resolve their visible
	# counters before the wider city snap radius, which can otherwise swallow
	# a neighbouring formation when several cells fit inside 22 screen pixels.
	if zoom<MapSemanticZoom.DETAIL_ZOOM:
		var best=minf(12.0,maxf(3.0,MapSemanticZoom.unit_size(zoom).x*.72))
		var counter_hex: Variant=null
		for unit in state.units:
			if unit.position==null or not VisibilityRules.unit_visible(state,state.player_faction_id,unit):continue
			var hex=HexGrid.coordinate(unit.position);var point=HexGrid.to_world(hex)
			if MapSemanticZoom.detailed(zoom,unit.id==selected_unit_id) and not StateAccess.at(state,"cities",hex).is_empty():point+=Vector2(29,17)
			var distance=world_to_screen(point).distance_to(screen)
			if distance<best:best=distance;counter_hex=hex
		if counter_hex!=null:hex_selected.emit(counter_hex);return
	if selected_unit_id.is_empty():
		var best=22.0;var city_hex: Variant=null
		for city in state.cities+state.map.get("reference_pois",[]):
			var h=HexGrid.coordinate(city.position);var distance=world_to_screen(HexGrid.to_world(h)).distance_to(screen)
			if distance<best:best=distance;city_hex=h
		if city_hex!=null:hex_selected.emit(city_hex);return
	var place_id=place_at_screen(screen)
	if not place_id.is_empty():place_selected.emit(place_id)
	else:hex_selected.emit(screen_to_hex(screen))

func overview_zoom() -> float:
	var bounds=camera_bounds if camera_bounds.has_area() else world_bounds
	if bounds.size.x<1 or bounds.size.y<1 or size.x<1 or size.y<1:return .28
	return clampf(minf(size.x/bounds.size.x,size.y/bounds.size.y)*.90,.008,1.65)

func fit_map() -> void:
	zoom=overview_zoom();camera=(camera_bounds if camera_bounds.has_area() else world_bounds).get_center();clamp_camera();queue_redraw()

func zoom_at(factor: float, at: Vector2) -> void:
	var before=(at-size*.5)/zoom+camera
	zoom=clampf(zoom*factor,minf(.28,overview_zoom()),1.65);camera=before-(at-size*.5)/zoom
	clamp_camera();queue_redraw()

func clamp_camera() -> void:
	if state.is_empty():return
	var bounds=camera_bounds if camera_bounds.has_area() else world_bounds
	var area=map_hud_area();var half_view=area.size/(2*zoom)
	var center_offset=(area.get_center()-size*.5)/zoom
	for axis in range(2):
		var low=bounds.position[axis]+minf(half_view[axis]-20,bounds.size[axis]*.5)-center_offset[axis]
		var high=bounds.end[axis]-minf(half_view[axis]-20,bounds.size[axis]*.5)-center_offset[axis]
		camera[axis]=clampf(camera[axis],low,high)

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index==MOUSE_BUTTON_WHEEL_UP:zoom_at(1.12,event.position)
		elif event.button_index==MOUSE_BUTTON_WHEEL_DOWN:zoom_at(1/1.12,event.position)
		elif event.button_index in [MOUSE_BUTTON_LEFT,MOUSE_BUTTON_RIGHT,MOUSE_BUTTON_MIDDLE]:
			if event.pressed:dragging=false;drag_origin=event.position;last_pointer=event.position
			elif event.button_index==MOUSE_BUTTON_LEFT and not dragging and not playback.active:select_screen(event.position)
			accept_event()
	elif event is InputEventMouseMotion and event.button_mask&(MOUSE_BUTTON_MASK_LEFT|MOUSE_BUTTON_MASK_RIGHT|MOUSE_BUTTON_MASK_MIDDLE):
		if event.position.distance_to(drag_origin)>9:dragging=true
		if dragging:camera-=event.relative/zoom;clamp_camera();queue_redraw()
	elif event is InputEventScreenTouch:
		if event.pressed:
			pointers[event.index]=event.position;drag_origin=event.position;touch_dragged=false
			if pointers.size()==2:pinch_distance=pointers.values()[0].distance_to(pointers.values()[1]);touch_dragged=true
		else:
			if pointers.size()==1 and not touch_dragged and event.position.distance_to(drag_origin)<12 and not playback.active:select_screen(event.position)
			pointers.erase(event.index);pinch_distance=0
		accept_event()
	elif event is InputEventScreenDrag:
		pointers[event.index]=event.position
		if pointers.size()==2:
			var points=pointers.values();var distance=points[0].distance_to(points[1]);var middle=(points[0]+points[1])*.5
			if pinch_distance>0:zoom_at(distance/pinch_distance,middle)
			pinch_distance=distance;touch_dragged=true
		elif pointers.size()==1 and (touch_dragged or event.position.distance_to(drag_origin)>12):
			touch_dragged=true;camera-=event.relative/zoom;clamp_camera();queue_redraw()
		accept_event()

func _process(delta: float) -> void:
	if static_only or static_units_only or static_foreground_only:return
	if territory_qa_mode:return
	if sync_backdrop():queue_redraw()
	if sync_unit_layer():queue_redraw()
	pulse+=delta
	var was_active=playback.active;var before_hit=playback.cue_flags.has("hit")
	if not playback_paused:playback.tick(delta)
	if was_active and playback.active and not before_hit and playback.cue_flags.has("hit"):
		for event in playback.current.get("impacts",[]):
			var position=event.get("position",playback.current.get("position"))
			if position!=null:effects.append({"position":HexGrid.to_world(HexGrid.coordinate(position)),"text":("城防 −" if event.type=="FortDamaged" else "−")+str(event.amount),"time":0.0,"kind":"damage"})
	for e in effects:e.time+=delta
	effects=effects.filter(func(e):return e.time<1.25)
	if was_active or not effects.is_empty() or pending_hex!=null:queue_redraw()

func faction_color(owner: String) -> Color:
	if TERRITORY_COLORS.has(owner):return TERRITORY_COLORS[owner]
	# Unknown or newly introduced groups get a deterministic visible color, rather
	# than all collapsing into the same beige fallback.
	return Color.from_hsv(float(absi(hash(owner))%360)/360.0,.44,.79)

func sprite(texture: Texture2D, center: Vector2, bounds: Vector2, tint: Color = Color.WHITE) -> void:
	var actual=texture.get_size();var factor=minf(bounds.x/actual.x,bounds.y/actual.y);var dimensions=actual*factor
	draw_texture_rect(texture,Rect2(center-dimensions*.5,dimensions),false,tint)

func _draw() -> void:
	if state.is_empty() or assets==null:
		if not static_units_only and not static_foreground_only:draw_rect(Rect2(Vector2.ZERO,size),Color("d8c8a5"))
		return
	var view=Rect2(camera-size/(2*zoom),size/zoom).grow(170)
	if territory_qa_mode:
		# The territory proof is a direct native viewport capture. Keep the same
		# authored map extent, hydrography and ownership meshes, but do not build
		# the ordinary layered backdrop/unit/foreground caches for this pass.
		if not static_units_only and not static_foreground_only:draw_rect(Rect2(Vector2.ZERO,size),Color("bbc6a4"))
		draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
		draw_territory_qa_atlas(view)
		draw_set_transform(Vector2.ZERO)
		return
	if static_only:
		draw_rect(Rect2(Vector2.ZERO,size),Color("d8c8a5"))
		draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
		draw_static_atlas(view);draw_set_transform(Vector2.ZERO);return
	if static_units_only:
		draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
		draw_units(view);draw_set_transform(Vector2.ZERO);return
	if static_foreground_only:
		draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
		draw_foreground(view);return
	sync_backdrop()
	var profile_start=Time.get_ticks_usec() if profile_draw_enabled else 0
	profile_shadow_usec=0
	profile_sort_usec=0
	if backdrop_viewport!=null:
		var source_at=(camera-backdrop_camera)*backdrop_zoom+backdrop_dimensions*.5-size*.5*backdrop_zoom/zoom
		draw_texture_rect_region(backdrop_viewport.get_texture(),Rect2(Vector2.ZERO,size),Rect2(source_at,size*backdrop_zoom/zoom))
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
	for mark in state.map.get("render_labels",[]):
		var p=Vector2(mark.position[0],mark.position[1])
		if view.has_point(p):map_name(mark.name,p,48 if mark.kind=="water" else 36,Color("e5dfcb") if mark.kind=="water" else Color("4c5244"),.72)
	if state.map.id in ["jingjin","jingfeng"]:draw_bohai_label(view)
	draw_regions(view)
	var overlay_keys=reachable.duplicate()
	for key in attack_targets:overlay_keys[key]=true
	for key in overlay_keys:
		var h=HexGrid.from_key(key);var p=HexGrid.to_world(h)
		if not view.has_point(p):continue
		var polygon=HexGrid.corners(p,48);var outline=polygon.duplicate();outline.append(polygon[0])
		if reachable.has(key):
			draw_colored_polygon(polygon,Color(.25,.66,.70,.18));draw_polyline(outline,Color(.36,.76,.80,.76),1.1/zoom,true)
		if attack_targets.has(key):
			draw_colored_polygon(polygon,Color(.65,.22,.19,.18));draw_polyline(outline,Color("bf6b54"),1.25/zoom,true);draw_arc(p,21,0,TAU,32,Color("b35b47"),1.5/zoom,true)
	if command_preview.get("valid",false) and command_preview.has("path"):
		var route=PackedVector2Array()
		for h in command_preview.path:route.append(HexGrid.to_world(h))
		if route.size()>1:draw_polyline(route,Color("ecdfb3"),5/zoom,true);draw_polyline(route,Color("3c8794"),2/zoom,true)
	draw_places(view)
	drawn_city_counter_ids=[];drawn_city_detail_ids=[]
	for city in playback.cities if playback.active else state.cities:
		var p=HexGrid.to_world(HexGrid.coordinate(city.position))
		if not view.has_point(p):continue
		if not MapSemanticZoom.detailed(zoom,city.id==selected_city_id):
			draw_city_counter(p,city);drawn_city_counter_ids.append(city.id);continue
		drawn_city_detail_ids.append(city.id)
		var color=faction_color(city.owner_id)
		var image: Texture2D
		var bank_id=""
		if MapArtBank.available() and city.fort_hp>0 and city.id not in ["jiumenkou","shanhaiguan"]:
			var role="station" if EconomyRules.building_level(city,"station")>0 and HistoricalPlaces.kind(city,state.date)=="city" else "dock" if city.get("port",false) and HistoricalPlaces.kind(city,state.date) not in ["national_capital","capital"] else ""
			bank_id=str(settlement_choices.get(city.id+":"+role,MapArtBank.settlement_id(city,state.date,role)))
		if bank_id.is_empty():
			if city.id=="jiumenkou" and ResourceLoader.exists("res://assets/scenery/scenery_jiumenkou_wall.png"):image=assets.texture("scenery","scenery_jiumenkou_wall")
			elif city.id=="shanhaiguan" and city.fort_hp>0:image=assets.texture("scenery","scenery_walled_city")
			elif city.fort_hp>0 and HistoricalPlaces.kind(city,state.date) in ["capital","national_capital","county","market"]:image=assets.texture("scenery",HistoricalPlaces.asset_id(city,state.date))
			elif EconomyRules.building_level(city,"station")>0 and city.fort_hp>0:image=assets.texture("scenery","scenery_station_town")
			else:image=assets.texture("building","building_%s_%s"%["station" if EconomyRules.building_level(city,"station")>0 else "barracks","damaged" if city.fort_hp==0 else "intact"])
		if not bank_id.is_empty():
			var bank_texture=assets.texture("building",bank_id)
			var rectangle=MapArtBank.source_rect(bank_id,Vector2(136,116));rectangle.position+=p+Vector2(0,28)
			if bank_texture!=null:draw_texture_rect(bank_texture,rectangle,false)
		elif image!=null:sprite(image,p+Vector2(0,-15),Vector2(136,116))
		command_flag(p+Vector2(-47,-42),city.owner_id,20)
		if city.fort_hp>0:
			draw_rect(Rect2(p+Vector2(-27,41),Vector2(54,4)),Color("282e27"));draw_rect(Rect2(p+Vector2(-27,41),Vector2(54.0*city.fort_hp/city.fort_max_hp,4)),Color("d2be81"))
		if city.id==selected_city_id:var corners=HexGrid.corners(p,46);corners.append(corners[0]);draw_polyline(corners,Color("eedda2"),2.4,true)
	for poi in state.map.get("reference_pois",[]):
		var p=HexGrid.to_world(HexGrid.coordinate(poi.position))
		if not view.has_point(p):continue
		draw_circle(p,5,Color("776d58"));draw_arc(p,10,0,TAU,20,Color("eee1c0"),1.5,true)
		if zoom>.4:map_name(poi.name+(" · 日占" if poi.poi_reason=="historical_occupation" else ""),p+Vector2(0,28),21,Color("393e34"),.9)
	var profile_units=Time.get_ticks_usec() if profile_draw_enabled else 0
	draw_unit_layer(view)
	var profile_after_units=Time.get_ticks_usec() if profile_draw_enabled else 0
	sync_foreground()
	draw_set_transform(Vector2.ZERO)
	if profile_draw_enabled and profile_draw_samples.size()<2000:
		profile_draw_samples.append({"total_ms":(Time.get_ticks_usec()-profile_start)/1000.0,"sort_ms":profile_sort_usec/1000.0,"units_ms":(profile_after_units-profile_units)/1000.0,"shadows_ms":profile_shadow_usec/1000.0})

func draw_foreground(view: Rect2) -> void:
	for sight in state.visibility:
		if sight.faction_id!=state.player_faction_id:continue
		for ghost in sight.last_seen:
			var h=HexGrid.coordinate(ghost.position);var cell=StateAccess.cell(state,h)
			if visible_ids.has(cell.get("id","")) or state.round-ghost.round>3:continue
			var p=HexGrid.to_world(h)
			if not view.has_point(p):continue
			draw_arc(p,28,0,TAU,24,Color(.76,.75,.65,.4),1,true)
			draw_string(assets.font,p+Vector2(-7,7),"?",HORIZONTAL_ALIGNMENT_LEFT,-1,26,Color(.83,.82,.70,.65))
	if pending_hex!=null:
		var p=HexGrid.to_world(pending_hex);var corners=HexGrid.corners(p,44);corners.append(corners[0]);draw_polyline(corners,Color(1,.82,.41,.75+.2*sin(pulse*4)),3,true)
	if selected_terrain_hex!=null:
		var p=HexGrid.to_world(selected_terrain_hex);var corners=HexGrid.corners(p,45);corners.append(corners[0]);draw_polyline(corners,Color("e5d19b"),2/zoom,true)
	for e in effects:
		var p=e.position+Vector2(-15,-40-e.time*24);var color=Color("ffe3ae");color.a=1-e.time/1.25
		var effect_texture=assets.texture("fx","fx_bullet_hit" if e.kind=="damage" else "fx_capture")
		if effect_texture!=null and e.time<.5:draw_texture_rect(effect_texture,Rect2(e.position-Vector2(34,34),Vector2(68,68)),false,Color(1,1,1,1-e.time*2))
		draw_string(assets.font,p,e.text,HORIZONTAL_ALIGNMENT_LEFT,-1,26,color)
	draw_playback(view)
	draw_city_labels(view)
	if show_places:draw_place_labels(view)
	draw_set_transform(Vector2.ZERO)
	if show_control:draw_control_legend()
	if show_terrain:draw_terrain_legend()
	draw_rect(Rect2(Vector2.ZERO,size),Color("ad9366"),false,2)
	draw_distance_scale()

func map_hud_area() -> Rect2:
	return hud_map_rect if hud_map_rect.has_area() else Rect2(Vector2(16,16),size-Vector2(32,32))

func legend_scale() -> float:return minf(1.25,label_scale)

func terrain_legend_rect() -> Rect2:
	if not show_terrain or zoom<.24:return Rect2()
	var area=map_hud_area();var s=legend_scale()
	var columns=clampi(int((area.size.x/s-58)/76),1,5)
	return Rect2(area.position,Vector2(columns*76+58,12+ceili(9.0/columns)*22)*s)

func ellipsized_label(text: String, font_size: int, width: float) -> String:
	if assets.font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size).x<=width:return text
	while not text.is_empty() and assets.font.get_string_size(text+"…",HORIZONTAL_ALIGNMENT_LEFT,-1,font_size).x>width:text=text.left(-1)
	return text+"…"

func draw_terrain_legend() -> void:
	# A compact screen-space key keeps the authored terrain vocabulary visible
	# without covering the strategic map or changing the command layout.
	var box=terrain_legend_rect()
	if not box.has_area():return
	var entries=[
		["平原",Color("b0aa7b")],
		["林地",Color("526c52")],
		["丘陵",Color("77775b")],
		["山地",Color("4d5c54")],
		["湿地",Color("657d72")],
		["河流",Color("3f839e")],
		["道路",Color("987d59")],
		["城镇",Color("b79a63")],
		["海面",Color("397083")]
	]
	var s=legend_scale();var columns=maxi(1,int(round((box.size.x/s-58)/76)))
	draw_rect(box,Color(.08,.13,.15,.86));draw_rect(box,Color("9baeb0",.62),false,1)
	draw_string(assets.font,box.position+Vector2(8,20)*s,"地形",HORIZONTAL_ALIGNMENT_LEFT,-1,int(14*s),Color("e8e2c9"))
	for index in range(entries.size()):
		var at=box.position+Vector2(48+(index%columns)*76,8+(index/columns)*22)*s
		draw_rect(Rect2(at,Vector2(11,11)*s),entries[index][1]);draw_rect(Rect2(at,Vector2(11,11)*s),Color("e7dfbd",.60),false,1)
		draw_string(assets.font,at+Vector2(15,11)*s,entries[index][0],HORIZONTAL_ALIGNMENT_LEFT,-1,int(13*s),Color("e8e2c9"))

func draw_distance_scale() -> void:
	var area=map_hud_area();var s=legend_scale();var box=Rect2(area.end-Vector2(minf(217*s,area.size.x),56*s),Vector2(minf(217*s,area.size.x),56*s))
	draw_rect(box,Color(.91,.85,.69,.90));draw_rect(box,Color("827149"),false,.8)
	var maximum_km=(box.size.x-66*s)*state.map.hex_radius_m/(HexGrid.RADIUS*zoom*1000.0)
	var magnitude=pow(10,floor(log(maximum_km)/log(10)))
	var distance=magnitude
	for multiplier in [5,2,1]:
		if magnitude*multiplier<=maximum_km:distance=magnitude*multiplier;break
	var width=distance*1000.0*HexGrid.RADIUS*zoom/state.map.hex_radius_m
	var start=box.position+Vector2(12*s,40*s);var finish=start+Vector2(width,0);var ink=Color("394238")
	draw_line(start,finish,ink,2,true)
	for point in [start,finish]:draw_line(point-Vector2(0,4),point+Vector2(0,4),ink,2,true)
	var text=(str(int(distance)) if distance>=1 else ("%.1f"%distance))+" km"
	draw_string(assets.font,start+Vector2(0,-8*s),text,HORIZONTAL_ALIGNMENT_LEFT,-1,int(16*s),ink)
	draw_string(assets.font,box.position+Vector2(box.size.x-45*s,32*s),"北↑",HORIZONTAL_ALIGNMENT_LEFT,-1,int(14*s),ink)

func draw_city_counter(point: Vector2, city: Dictionary) -> void:
	var rank=HistoricalPlaces.importance(city,state.date)
	var radius=MapSemanticZoom.city_radius(zoom,rank)
	var color=faction_color(str(city.owner_id)) if city.has("owner_id") else Color("93836c")
	draw_set_transform(world_to_screen(point).snapped(Vector2.ONE/64.0))
	draw_circle(Vector2(0,1),radius+1.2,Color(.05,.10,.12,.28))
	if rank>=5 and zoom>=MapSemanticZoom.REGIONAL_ZOOM:
		var diamond=PackedVector2Array([Vector2(0,-radius-1),Vector2(radius+1,0),Vector2(0,radius+1),Vector2(-radius-1,0)])
		draw_colored_polygon(diamond,Color("d5c493"))
		draw_circle(Vector2.ZERO,radius-1.0,Color("25343a"))
	else:
		draw_circle(Vector2.ZERO,radius,Color("d5c493"));draw_circle(Vector2.ZERO,maxf(1.0,radius-.9),Color("25343a"))
	draw_circle(Vector2.ZERO,maxf(.8,radius-2.0),color)
	if (city.get("port",false) or HistoricalPlaces.kind(city,state.date)=="port") and radius>=4:
		draw_line(Vector2(-radius*.65,radius+1.5),Vector2(radius*.65,radius+1.5),Color("d7eceb"),1.1,true)
	elif radius>=4:
		draw_line(Vector2(-2,-1),Vector2(0,-3),Color("eee9d3"),1.0,true);draw_line(Vector2(0,-3),Vector2(2,-1),Color("eee9d3"),1.0,true)
	if city.id==selected_city_id or city.id==selected_place_id:draw_arc(Vector2.ZERO,radius+2,0,TAU,24,Color("eedda2"),1.2,true)
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func draw_unit_counter(point: Vector2, unit: Dictionary, color: Color, opacity: float) -> void:
	var dimensions=MapSemanticZoom.unit_size(zoom)
	var rect=Rect2(-dimensions*.5,dimensions)
	var ink=Color("eee9d8") if color.get_luminance()<.43 else Color("14292e")
	ink.a=opacity
	draw_set_transform(world_to_screen(point).snapped(Vector2.ONE/64.0))
	draw_rect(rect.grow(MapSemanticZoom.unit_border(zoom)),Color(.06,.12,.15,opacity*.94))
	draw_rect(rect,Color(color,opacity))
	if dimensions.x>=9.0:
		var center=Vector2(0,-.5);var family=str(content.definition("units",unit.def_id).get("family","infantry"))
		match family:
			"cavalry":draw_line(center+Vector2(-2,2),center+Vector2(2,-2),ink,1.2,true)
			"artillery","coastal":draw_circle(center,1.6,ink);draw_line(center,center+Vector2(3,-2),ink,1.0,true)
			"rail":draw_line(center+Vector2(-3,-1),center+Vector2(3,-1),ink,1.0,true);draw_line(center+Vector2(-3,1),center+Vector2(3,1),ink,1.0,true)
			"river","naval","water":draw_line(center+Vector2(-3,-1),center+Vector2(3,-1),ink,1.1,true);draw_line(center+Vector2(-2,1),center+Vector2(2,1),ink,1.1,true)
			"motor":draw_rect(Rect2(center-Vector2(2,1.6),Vector2(4,3.2)),ink,false,1.0)
			"air":draw_line(center+Vector2(0,-2.5),center+Vector2(0,2),ink,1.2,true);draw_line(center+Vector2(-3,0),center+Vector2(3,0),ink,1.0,true)
			_:draw_line(center+Vector2(-2,-2),center+Vector2(2,2),ink,1.0,true);draw_line(center+Vector2(-2,2),center+Vector2(2,-2),ink,1.0,true)
		if unit.general_id!=null:draw_circle(rect.position+Vector2(1.2,1.2),1.3,Color(1,.88,.55,opacity))
	if dimensions.x>=5:
		draw_rect(Rect2(Vector2(rect.position.x,rect.end.y-1),Vector2(dimensions.x*float(unit.hp)/unit.max_hp,1)),Color(.94,.94,.83,opacity))
	if unit.id==selected_unit_id:draw_rect(rect.grow(1.5),Color(1,.85,.48,opacity),false,1.1)
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func draw_units(view: Rect2, actors: Variant = null) -> void:
	var display_units=actors if actors!=null else (unit_source_override if static_units_only else ordered_units(playback.units if playback.active else state.units))
	if actors==null:drawn_unit_count=0;drawn_unit_counter_ids=[];drawn_unit_detail_ids=[]
	for u in display_units:
		# The previous unit finishes in its screen-anchor transform for the
		# authored sprite and status bars.  Restore the shared world transform
		# before resolving the next formation's facing marker, motion trail and
		# world-space visibility.  Without this reset only the first idle chevron
		# was reliably drawn at the unit's map position.
		draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)
		if u.position==null:continue
		var p=playback.position_of(u) if playback.active else HexGrid.to_world(HexGrid.coordinate(u.position))
		if u.owner_id!=state.player_faction_id and not VisibilityRules.hex_visible(state,state.player_faction_id,HexGrid.from_world(p)):continue
		if not view.has_point(p):continue
		var color=faction_color(u.owner_id)
		var at_city=not StateAccess.at(state,"cities",HexGrid.coordinate(u.position)).is_empty() and (not playback.active or playback.current.kind not in ["move","rail"] or playback.current.unit_id!=u.id)
		var active_actor=playback.active and playback.animated_unit_ids.has(u.id)
		var detail=MapSemanticZoom.detailed(zoom,u.id==selected_unit_id or active_actor)
		var opacity=playback.opacity_of(u) if playback.active else 1.0
		if opacity<=0:continue
		if at_city and detail:p+=Vector2(29,17)
		if not detail:
			draw_unit_counter(p,u,color,opacity);drawn_unit_counter_ids.append(u.id);drawn_unit_count+=1;continue
		drawn_unit_detail_ids.append(u.id)
		# Facing is visual state only. Movement turns the miniature toward the
		# current segment; neither the saved formation nor its legal action changes.
		var heading=Vector2.ZERO
		if playback.active and playback.current.kind in ["move","rail"] and playback.current.unit_id==u.id:
			var progress=playback.progress()
			var travel=progress if playback.reduced_motion else progress*progress*(3-2*progress)
			var route=playback.current.path;var segment=mini(route.size()-2,int((route.size()-1)*travel))
			heading=HexGrid.to_world(HexGrid.coordinate(route[segment+1]))-HexGrid.to_world(HexGrid.coordinate(route[segment]))
		elif playback.active and playback.current.kind=="attack" and playback.current.attacker.id==u.id:
			heading=HexGrid.to_world(HexGrid.coordinate(playback.current.position))-HexGrid.to_world(HexGrid.coordinate(playback.current.from))
		elif playback.active and playback.current.kind=="attack" and playback.current.target.get("id","")==u.id:
			heading=HexGrid.to_world(HexGrid.coordinate(playback.current.from))-HexGrid.to_world(HexGrid.coordinate(playback.current.position))
		if heading.length_squared()<0.01 and unit_headings.has(str(u.id)):
			heading=unit_headings[str(u.id)]
		var orientation=unit_orientation(heading,str(u.get("facing","se")),u)
		var pose=playback.pose_of(u) if playback.active else "idle"
		var image=assets.unit_action_texture(u,orientation.asset,pose)
		var motion=playback.motion_visual(u,content) if playback.active else {"offset":Vector2.ZERO,"rotation":0.0,"scale":1.0,"profile":"idle","phase":0.0}
		# Build each actor around its screen anchor, avoiding large world-coordinate
		# cancellation in GPU vertices on the fivefold atlas and cached viewports.
		var world_anchor=p
		# Cached targets add integer pixel padding. Quantize the actor anchor to
		# the same subpixel lattice before either target rasterizes its vertices.
		var visual_anchor=world_anchor+motion.offset
		var screen_anchor=world_to_screen(visual_anchor).snapped(Vector2.ONE/64.0)
		if motion.profile!="idle":draw_unit_motion_trail(world_anchor,motion,u,opacity)
		# Keep the final facing legible after the event has finished. Active and
		# selected formations get a full brass chevron; idle formations retain a
		# compact, low-alpha pennant so every authored cardinal unit source has a
		# visible base direction without turning the map into a field of arrows.
		if heading.length_squared()>0.01 and zoom>=.42:
			var prominent=playback.active or u.id==selected_unit_id
			# Keep the facing marker outside the sprite silhouette.  The previous
			# anchor sat at the unit centre, so the authored soldier/cannon art hid
			# most of a short east/west chevron.  A small pennant above the formation
			# remains readable for idle units and shares the same cached heading as
			# movement, attack and damage playback.
			var facing_anchor=p+Vector2(0,-39 if not at_city else -34)
			draw_unit_heading(facing_anchor,heading.normalized(),opacity,not prominent)
		draw_set_transform(screen_anchor,0,Vector2.ONE*zoom)
		p=Vector2.ZERO
		drawn_unit_count+=1
		draw_ellipse_shadow(p+Vector2(0,12),opacity)
		if zoom>=.20 and u.owner_id==state.player_faction_id and (u.ap_left>0 or u.attack_ready) and not playback.active and not unit_ready_hidden:draw_arc(p+Vector2(0,12),29,0,TAU,32,Color(.86,.96,1,.65),1.3/zoom,true)
		var family=str(content.definition("units",u.def_id).get("family","infantry"))
		draw_unit_family_badge(p+Vector2(0,25),family,color,opacity)
		if image!=null:
			draw_set_transform(screen_anchor,orientation.angle+motion.rotation,Vector2.ONE*zoom*float(motion.scale))
			var bound=Vector2(88,80) if not at_city else Vector2(75,68)
			var action_rect=assets.unit_action_rect(u,orientation.asset,pose,bound)
			if action_rect.has_area():draw_texture_rect(image,action_rect,false,Color(1,1,1,opacity))
			else:sprite(image,Vector2.ZERO+Vector2(0,-9),bound,Color(1,1,1,opacity))
			draw_set_transform(screen_anchor,0,Vector2.ONE*zoom)
		command_flag(p+Vector2(25,-35),u.owner_id,14)
		if u.id==selected_unit_id:
			var center=HexGrid.to_world(HexGrid.coordinate(u.position))-world_anchor;var corners=HexGrid.corners(center,47);corners.append(corners[0]);draw_polyline(corners,Color("e3bf60"),3.2,true)
		draw_rect(Rect2(p+Vector2(-24,25),Vector2(48,6)),Color("172731"));draw_rect(Rect2(p+Vector2(-23,26),Vector2(46.0*u.hp/u.max_hp,4)),Color("91c879") if u.owner_id==state.player_faction_id else Color("e36f59"))
		for i in range(1,4):draw_line(p+Vector2(-24+i*12,25),p+Vector2(-24+i*12,31),Color("252b2b"),1,true)
		for i in range(u.stack):draw_rect(Rect2(p+Vector2(29,-13+i*7),Vector2(5,5)),Color("e8d9a9"))
		if u.general_id!=null and zoom>=.40:draw_string(assets.font,p+Vector2(-36,-25),"★",HORIZONTAL_ALIGNMENT_LEFT,-1,20,Color("ffe4a5"))
		var veteran=VeterancyRules.rank_for(int(u.get("experience",0)))
		if veteran>0 and zoom>=.50:draw_string(assets.font,p+Vector2(-30,13),["","Ⅰ","Ⅱ","Ⅲ"][veteran],HORIZONTAL_ALIGNMENT_LEFT,-1,16,Color("e7c58c"))
		if u.supply_state!="FULL" and zoom>=.37:draw_string(assets.font,p+Vector2(24,23),"!",HORIZONTAL_ALIGNMENT_LEFT,-1,22,Color("ffc885"))
		if show_supply and u.owner_id==state.player_faction_id:
			var city=StateAccess.find(state,"cities",str(u.get("supply_city_id")))
			if not city.is_empty():draw_line(p,HexGrid.to_world(HexGrid.coordinate(city.position))-world_anchor,Color(.71,.88,.65,.4),1.2,true)
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func unit_orientation(heading: Vector2, fallback: String="se", unit: Dictionary={}) -> Dictionary:
	# Prefer the independent Sub2 cardinal source views. They keep the figures
	# upright while facing north/east/south/west; the old diagonal sources remain
	# a safe fallback for editor scans or a partially imported older package.
	if heading.length_squared()<0.01:
		return {"asset":"sw" if fallback=="sw" else "se","angle":0.0}
	var angle=heading.angle()
	var cardinal="e"
	if angle>=PI*.25 and angle<PI*.75:cardinal="s"
	elif angle>=PI*.75 or angle< -PI*.75:cardinal="w"
	elif angle>= -PI*.75 and angle< -PI*.25:cardinal="n"
	var unit_id=str(unit.get("elite_id") if unit.get("elite_id")!=null else unit.get("def_id",""))
	var cardinal_available=not unit_id.is_empty() and assets!=null and assets.texture("unit","unit_%s_%s"%[unit_id,cardinal])!=null
	if cardinal_available:return {"asset":cardinal,"angle":0.0}
	var diagonal="sw" if heading.x<-.01 else "se"
	var source_angle=2.64 if diagonal=="sw" else .50
	return {"asset":diagonal,"angle":wrapf(angle-source_angle,-PI,PI)}

func draw_unit_heading(at: Vector2, heading: Vector2, opacity: float, compact: bool=false) -> void:
	# A restrained brass chevron makes the current facing legible even when a
	# small formation is partly hidden by the control ring or a terrain sprite.
	var length=23.0 if compact else 32.0
	var wing=6.0 if compact else 8.0
	var back=7.0 if compact else 9.0
	var alpha=(.56 if compact else .80)*opacity
	var tip=at+heading*length
	var normal=heading.orthogonal()
	var ink=Color(.94,.82,.48,alpha)
	var width=maxf(.75,(.95 if compact else 1.4)/zoom)
	# A dark hairline beneath the brass mark survives pale plains and mountain
	# textures without changing the faction colour or unit artwork.
	draw_line(at+heading*(length*.34)+normal*.7,tip+normal*.7,Color(.08,.12,.13,alpha*.55),width+maxf(.3,.7/zoom),true)
	draw_line(at+heading*(length*.34),tip,ink,width,true)
	draw_line(tip,tip-heading*back+normal*wing,ink,width,true)
	draw_line(tip,tip-heading*back-normal*wing,ink,width,true)

func draw_unit_family_badge(center: Vector2, family: String, owner_color: Color, opacity: float) -> void:
	# Small class silhouettes remain visible when the Sub2 miniature is reduced on
	# a phone. They supplement the authored sprite and never replace it.
	var badge_colors={"infantry":Color("6f8794"),"cavalry":Color("c49a57"),"artillery":Color("a66d59"),"motor":Color("708c92"),"rail":Color("b9a77b"),"river":Color("5c9aa2"),"naval":Color("5c9aa2"),"water":Color("5c9aa2"),"coastal":Color("668a9e"),"air":Color("c6a45e")}
	var ink=Color(badge_colors.get(family,Color("7f8c86")),opacity*.86)
	var edge=Color(owner_color,opacity*.92)
	draw_circle(center,9.0,Color(.06,.12,.15,opacity*.72));draw_circle(center,7.2,ink)
	match family:
		"cavalry":
			draw_line(center+Vector2(-4,3),center+Vector2(0,-4),edge,1.6,true);draw_line(center+Vector2(0,-4),center+Vector2(5,3),edge,1.6,true)
		"artillery","rail":
			draw_rect(Rect2(center-Vector2(4,3),Vector2(8,6)),edge);draw_line(center+Vector2(-1,-1),center+Vector2(6,-6),edge,1.5,true)
		"river","naval","water","coastal":
			draw_line(center+Vector2(-5,1),center+Vector2(5,1),edge,1.6,true);draw_line(center+Vector2(-3,4),center+Vector2(3,4),edge,1.3,true)
		"motor":
			draw_rect(Rect2(center-Vector2(5,3),Vector2(10,6)),edge);draw_circle(center+Vector2(-4,5),1.7,edge);draw_circle(center+Vector2(4,5),1.7,edge)
		_:
			draw_line(center+Vector2(-4,3),center+Vector2(0,-4),edge,1.7,true);draw_line(center+Vector2(0,-4),center+Vector2(4,3),edge,1.7,true)

func draw_unit_motion_trail(world_anchor: Vector2, motion: Dictionary, unit: Dictionary, opacity: float) -> void:
	var action=playback.current;var path=action.get("path",[])
	if path.size()<2:return
	var p=playback.progress();var segment=mini(path.size()-2,int((path.size()-1)*clampf(p*p*(3-2*p),0,1)))
	var from=HexGrid.to_world(HexGrid.coordinate(path[segment]));var to=HexGrid.to_world(HexGrid.coordinate(path[segment+1]));var direction=(to-from).normalized();var screen=world_to_screen(world_anchor);var normal=direction.orthogonal();var alpha=opacity*(.34+.16*sin(motion.phase))
	draw_set_transform(Vector2.ZERO)
	match motion.profile:
		"cavalry":
			for i in range(3):draw_circle(screen-direction*float(18+i*11)+normal*sin(motion.phase+i)*3,2.6-i*.45,Color(.72,.58,.39,alpha*(1.0-i*.22)))
		"motor":
			for i in range(2):draw_circle(screen-direction*float(20+i*12)+Vector2(0,-9-i*4),3.2-i*.6,Color(.55,.60,.56,alpha*(1.0-i*.25)))
		"rail":
			for i in range(4):draw_line(screen-direction*float(15+i*10)+normal*5,screen-direction*float(21+i*10)-normal*5,Color(.88,.69,.39,alpha),1.4,true)
		"river","naval","water","coastal":
			draw_line(screen-direction*52+normal*7,screen-direction*10+normal*3,Color(.72,.91,.91,alpha),1.6,true);draw_line(screen-direction*52-normal*7,screen-direction*10-normal*3,Color(.72,.91,.91,alpha*.8),1.4,true)
		_:
			for i in range(2):draw_circle(screen-direction*float(17+i*13)+normal*sin(motion.phase+i)*2,2.2-i*.5,Color(.77,.66,.47,alpha*(1.0-i*.3)))
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func ordered_units(source: Array) -> Array:
	var start=Time.get_ticks_usec() if profile_draw_enabled else 0
	var positions=PackedFloat32Array()
	for u in source:positions.append(HexGrid.to_world(HexGrid.coordinate(u.position)).y if u.position!=null else -9999)
	if not is_same(ordered_unit_source,source) or positions!=ordered_unit_positions:
		ordered_unit_source=source;ordered_unit_positions=positions
		var indexed=[]
		for i in range(source.size()):indexed.append({"unit":source[i],"y":positions[i]})
		indexed.sort_custom(func(a,b):return a.y<b.y)
		ordered_unit_records=indexed.map(func(record):return record.unit)
	if profile_draw_enabled:profile_sort_usec+=Time.get_ticks_usec()-start
	return ordered_unit_records

func make_unit_layer(viewport: SubViewport, layer: MapView) -> Dictionary:
	var texture=TextureRect.new();texture.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;texture.stretch_mode=TextureRect.STRETCH_SCALE
	texture.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var material=CanvasItemMaterial.new();material.blend_mode=CanvasItemMaterial.BLEND_MODE_PREMULT_ALPHA;texture.material=material
	var atlas=AtlasTexture.new();atlas.atlas=viewport.get_texture();atlas.filter_clip=true;texture.texture=atlas;add_child(texture)
	return {"viewport":viewport,"view":layer,"texture":texture,"atlas":atlas}

func sync_foreground() -> void:
	if foreground_view==null:return
	foreground_view.size=size;foreground_view.state=state;foreground_view.camera=camera;foreground_view.zoom=zoom;foreground_view.label_scale=label_scale
	foreground_view.selected_city_id=selected_city_id;foreground_view.pending_hex=pending_hex;foreground_view.effects=effects;foreground_view.pulse=pulse
	foreground_view.selected_unit_id=selected_unit_id
	foreground_view.selected_terrain_hex=selected_terrain_hex
	foreground_view.playback=playback;foreground_view.visible_ids=visible_ids;foreground_view.queue_redraw()
	foreground_view.cinema=cinema
	foreground_view.places=places;foreground_view.place_references=place_references;foreground_view.selected_place_id=selected_place_id
	foreground_view.show_places=show_places;foreground_view.show_control=show_control;foreground_view.show_terrain=show_terrain
	foreground_view.hud_map_rect=hud_map_rect
	foreground_view.territory_qa_mode=territory_qa_mode
	foreground_view.label_obstacle_controls=label_obstacle_controls
	foreground_view.label_revision=label_revision

func sync_unit_layer() -> bool:
	if static_only or static_units_only or static_foreground_only or state.is_empty() or unit_viewport==null or size.x<1 or size.y<1:return false
	if not uses_unit_cache():return false
	var sorted=ordered_units(playback.units if playback.active else state.units)
	var topology=[];unit_actors=[]
	for i in range(sorted.size()):
		if playback.active and playback.animated_unit_ids.has(sorted[i].id):topology.append([sorted[i].id,i]);unit_actors.append(sorted[i])
	var signature=geography_key+"|"+str(state.state_version)+"|"+str(size)+"|"+selected_unit_id+"|"+str(show_supply)+"|"+str(playback.active)+"|"+str(topology)+"|"+MapSemanticZoom.band(zoom)
	var ratio=zoom/unit_zoom;var padding=(unit_dimensions*ratio-size)*.5;var displacement=(camera-unit_camera)*zoom
	if signature==unit_signature and ratio>=.95 and ratio<=1.05 and absf(displacement.x)<=padding.x-24 and absf(displacement.y)<=padding.y-24:return false
	unit_signature=signature;unit_camera=camera;unit_zoom=zoom;unit_dimensions=Vector2(ceili(size.x)+384,ceili(size.y)+384)
	unit_segments=[[]]
	for u in sorted:
		if playback.active and playback.animated_unit_ids.has(u.id):unit_segments.append([])
		else:unit_segments[-1].append(u)
	while unit_layers.size()<unit_segments.size():
		var viewport=SubViewport.new();viewport.disable_3d=true;viewport.gui_disable_input=true;viewport.transparent_bg=true
		viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;add_child(viewport)
		var layer=get_script().new();layer.static_units_only=true;layer.assets=assets;layer.content=content;layer.clip_contents=true
		viewport.add_child(layer);layer.set_process(false);unit_layers.append(make_unit_layer(viewport,layer))
	for i in range(unit_segments.size()):
		var viewport:SubViewport=unit_layers[i].viewport;var layer:MapView=unit_layers[i].view
		viewport.size=Vector2i(unit_dimensions);layer.size=unit_dimensions
		layer.state=state;layer.camera=camera;layer.zoom=zoom;layer.selected_unit_id=selected_unit_id;layer.show_supply=show_supply
		layer.unit_headings=unit_headings
		layer.unit_source_override=unit_segments[i];layer.unit_ready_hidden=playback.active
		layer.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	unit_rebuilds+=1
	return true

func uses_unit_cache() -> bool:
	return unit_cache_enabled and (not playback.active or playback.animated_unit_ids.size()<=4)

func draw_unit_layer(view: Rect2) -> void:
	if not uses_unit_cache():
		for layer in unit_layers:layer.texture.hide()
		for actor in unit_actor_views:actor.hide()
		draw_units(view);return
	sync_unit_layer()
	if unit_viewport==null:return
	var source_at=(camera-unit_camera)*unit_zoom+unit_dimensions*.5-size*.5*unit_zoom/zoom
	drawn_unit_count=0;live_actor_draw_count=0
	while unit_actor_views.size()<unit_actors.size():
		var actor=get_script().new();actor.static_units_only=true;actor.assets=assets;actor.content=content;actor.clip_contents=true
		actor.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(actor);actor.set_process(false);unit_actor_views.append(actor)
	for i in range(unit_layers.size()):unit_layers[i].texture.visible=i<unit_segments.size()
	for i in range(unit_actor_views.size()):unit_actor_views[i].visible=i<unit_actors.size()
	for i in range(unit_segments.size()):
		# Static slices preserve the original painter order around live actors.
		var layer=unit_layers[i];layer.texture.size=size;layer.atlas.region=Rect2(source_at,size*unit_zoom/zoom);move_child(layer.texture,get_child_count()-1)
		drawn_unit_count+=unit_layers[i].view.drawn_unit_count
		if i<unit_actors.size():
			var actor:MapView=unit_actor_views[i];actor.size=size;actor.state=state;actor.camera=camera;actor.zoom=zoom
			actor.playback=playback;actor.selected_unit_id=selected_unit_id;actor.show_supply=show_supply
			actor.unit_headings=unit_headings
			actor.unit_source_override=[unit_actors[i]];actor.queue_redraw();move_child(actor,get_child_count()-1)

func unit_layer_draw_count() -> int:
	if not uses_unit_cache():return drawn_unit_count
	var count=0
	for i in range(unit_segments.size()):count+=int(unit_layers[i].view.drawn_unit_count)
	for actor in unit_actor_views:
		if actor.visible:count+=int(actor.drawn_unit_count)
	return count

func sync_backdrop() -> bool:
	if static_only or static_units_only or static_foreground_only or state.is_empty() or backdrop_viewport==null or size.x<1 or size.y<1:return false
	var signature=geography_key+"|"+administration_key+"|"+str(size)+"|"+str(label_scale)+"|"+str(show_rail)+"|"+str(show_grid)+"|"+str(show_control)+"|"+str(show_terrain)+"|"+places.owner_signature
	var ratio=zoom/backdrop_zoom
	var padding=(backdrop_dimensions*ratio-size)*.5
	var displacement=(camera-backdrop_camera)*zoom
	if signature==backdrop_signature and ratio>=.85 and ratio<=1.15 and absf(displacement.x)<=padding.x-24 and absf(displacement.y)<=padding.y-24:return false
	backdrop_signature=signature;backdrop_camera=camera;backdrop_zoom=zoom
	backdrop_dimensions=Vector2(ceili(size.x)+384,ceili(size.y)+384)
	backdrop_viewport.size=Vector2i(backdrop_dimensions);backdrop_view.size=backdrop_dimensions
	backdrop_view.camera=camera;backdrop_view.zoom=zoom;backdrop_view.state=state;backdrop_view.visible_ids=visible_ids
	backdrop_view.annotation_view_size=size;backdrop_view.show_grid=show_grid;backdrop_view.show_rail=show_rail;backdrop_view.label_scale=label_scale;backdrop_view.show_terrain=show_terrain
	backdrop_view.land_shapes=land_shapes;backdrop_view.coast_lines=coast_lines;backdrop_view.river_lines=river_lines;backdrop_view.detail_river_lines=detail_river_lines;backdrop_view.region_lines=region_lines
	backdrop_view.river_stream_orders=river_stream_orders;backdrop_view.river_rows=river_rows
	backdrop_view.crossing_markers=crossing_markers
	backdrop_view.land_surface=land_surface;backdrop_view.water_surface=water_surface;backdrop_view.extent_surface=extent_surface
	backdrop_view.map_extent=map_extent;backdrop_view.relief=relief;backdrop_view.world_bounds=world_bounds
	backdrop_view.continuous_relief_enabled=continuous_relief_enabled
	backdrop_view.map_details=map_details
	backdrop_view.settlement_choices=settlement_choices
	backdrop_view.presentation_cells=presentation_cells;backdrop_view.terrain_visual_buckets=terrain_visual_buckets
	backdrop_view.surface_region_diagnostics=surface_region_diagnostics
	backdrop_view.hydrography_diagnostics=hydrography_diagnostics
	backdrop_view.detail_river_buckets=detail_river_buckets
	backdrop_view.historical_landcover_features=historical_landcover_features
	backdrop_view.places=places;backdrop_view.show_control=show_control
	backdrop_view.territory_field_meshes=territory_field_meshes;backdrop_view.territory_field_cells=territory_field_cells;backdrop_view.territory_field_borders=territory_field_borders;backdrop_view.territory_field_diagnostics=territory_field_diagnostics
	backdrop_view.territory_qa_mode=territory_qa_mode
	backdrop_view.queue_redraw();backdrop_viewport.render_target_update_mode=SubViewport.UPDATE_ONCE;backdrop_rebuilds+=1
	return true

func draw_static_atlas(view: Rect2) -> void:
	terrain_scenery_draw_count=0
	if territory_qa_mode:
		draw_territory_qa_atlas(view)
		return
	draw_landscape(view)
	if show_terrain and zoom>=.10:
		var scenery=relief.visible_features(view)
		if MapArtBank.available():
			scenery.append_array(map_details.visible_features(view,zoom))
			scenery.sort_custom(func(a,b):return a.position.y<b.position.y if a.position.y!=b.position.y else a.asset_id<b.asset_id)
		for feature in scenery:
			var image=assets.texture("scenery",feature.asset_id)
			var has_original=image!=null
			if image==null:image=assets.texture("scenery","scenery_atlas_ridge_01" if feature.terrain_id in ["mountain","peak"] else "scenery_atlas_hill_01")
			if image!=null:
				terrain_scenery_draw_count+=1
				# Preserve the painterly 2.5D source while letting the surveyed
				# terrain mesh, cell texture and faction wash remain visible through
				# the lower silhouette.  This is a presentation tint only.
				var feature_alpha=.98 if feature.terrain_id in ["mountain","peak"] else .94
				if state.map.get("strategic_scale",false):feature_alpha+=.04
				if feature.has("texture_rect") and has_original:
					var rectangle: Rect2=feature.texture_rect;rectangle.position+=feature.position
					draw_texture_rect(image,rectangle,false,Color(1.0,1.0,.98,minf(feature_alpha,1.0)))
				else:sprite(image,feature.position,feature.bounds,Color(1.0,1.0,.98,minf(feature_alpha,1.0)))
	if show_control and not state.map.get("strategic_scale",false):draw_control_zones(view,true)
	for points in region_lines:
		if points.size()>1:draw_polyline(points,Color(.95,.96,.84,.38),1.6/zoom,true);draw_polyline(points,Color(.22,.31,.30,.42 if zoom<.52 else .22),.7/zoom,true)
	if show_rail and not territory_qa_mode:
		for edge in state.map.rail_edges:
			if state.date<edge.active_from:continue
			var points=PackedVector2Array()
			for position in edge.path_hexes:points.append(HexGrid.to_world(HexGrid.coordinate(position)))
			if points.size()<2:continue
			points=rounded_track(points)
			var color=Color("a65438") if edge.damage!="intact" else (Color("242823") if MovementRules.rail_available(state,edge) else Color("898574"))
			draw_polyline(points,Color(.93,.86,.67,.83),maxf(7,2.4/zoom),true);draw_polyline(points,color,maxf(4.2,1.1/zoom),true)
			for i in range(points.size()-1):
				if zoom<.32:break
				var delta=points[i+1]-points[i];var perpendicular=delta.normalized().orthogonal()*3.8
				for step in range(int(delta.length()/9)):
					var p=points[i]+delta.normalized()*step*9;draw_line(p-perpendicular,p+perpendicular,color,1.3,true)
				var normal=delta.normalized().orthogonal()*1.3;draw_line(points[i]+normal,points[i+1]+normal,Color("d4cdb3"),.7,true);draw_line(points[i]-normal,points[i+1]-normal,Color("d4cdb3"),.7,true)
			if edge.damage!="intact":
				var center=points[points.size()/2];draw_line(center-Vector2(10,12),center+Vector2(10,12),Color("a74336"),4,true);draw_line(center+Vector2(-10,12),center+Vector2(10,-12),Color("a74336"),4,true)
	# Known terrain and intelligence-grid outlines are cached; commands remain dynamic.
	# At full-map scale a subpixel grid obscures surveyed coastlines. Tactical
	# zoom keeps the same 48px hex; visit only axial coordinates in this viewport.
	if zoom>=.20:
		var bounds=visible_hex_bounds(view);var low=bounds[0];var high=bounds[1]
		for q in range(low.x,high.x+1):
			for r in range(low.y,high.y+1):
				var cell=presentation_cells.get(Vector2i(q,r),{})
				if cell.is_empty() or (not show_grid and not visible_ids.has(cell.id)):continue
				var p=HexGrid.to_world(Vector2i(q,r))
				if not view.has_point(p):continue
				var outline=HexGrid.corners(p,48);outline.append(outline[0])
				# Keep the operational hex visible without letting the lattice overpower
				# surveyed coastlines, terrain objects and semi-transparent control fields.
				draw_polyline(outline,Color(.94,.97,.94,.16 if show_grid else .065),.55/zoom,true)
	if zoom<.52 and not territory_qa_mode:draw_overview_grid(view)

func draw_territory_qa_atlas(view: Rect2) -> void:
	# Keep the evidence image geographic without asking CanvasItem to upload the
	# full relief/terrain command stream.  These are the same authored coastline,
	# land rings, rivers and ownership meshes used by shipping play; only the
	# optional decorative atlas layers are omitted for this bounded QA capture.
	var rectangle=PackedVector2Array([view.position,Vector2(view.end.x,view.position.y),view.end,Vector2(view.position.x,view.end.y)])
	draw_colored_polygon(rectangle,Color("bbc6a4"))
	if map_extent.size()>=4:draw_colored_polygon(map_extent,Color("377d91"))
	# Reuse the validated authored land mesh with a flat parchment tint. Relief,
	# cell fabric and the overview lattice remain outside this bounded capture.
	if land_surface!=null:draw_mesh(land_surface,null,Transform2D.IDENTITY,Color("a9a58b"))
	for points in coast_lines:
		if points.size()>1 and view.intersects(Rect2(points[0],Vector2.ZERO).expand(points[points.size()-1]).grow(160)):
			draw_polyline(points,Color("a5cdc3"),3.0,true)
	for points in river_lines:
		if points.size()>1 and view.intersects(Rect2(points[0],Vector2.ZERO).expand(points[points.size()-1]).grow(160)):
			draw_polyline(points,Color("5b9aaa"),maxf(2.4,3.2/zoom),true)
	if show_control and not state.map.get("strategic_scale",false):draw_control_zones(view)

func draw_overview_grid(view: Rect2) -> void:
	# EW6-style strategic readability: retain the same 48px gameplay hex while
	# thinning the overview lattice so the 74k-cell map remains inexpensive.
	# Long axial guides are aligned to the compiled coordinate system and clipped
	# by the MapView; they do not alter movement cells or invent map content.
	var bounds=visible_hex_bounds(view);var low:Vector2i=bounds[0];var high:Vector2i=bounds[1]
	var stride=3 if zoom<.34 else 2
	var q_step=maxi(stride,ceili(float(high.x-low.x)/96.0))
	var r_step=maxi(stride,ceili(float(high.y-low.y)/96.0))
	# The overview lattice needs to survive the parchment relief and faction fills
	# at both 1080p and the smaller Android viewport.  Keep it restrained, but
	# give each axial guide enough contrast to read as the strategic EW6 grid.
	var strategic=state.map.get("strategic_scale",false)
	var ink=Color(.13,.23,.25,.16 if strategic else .28)
	var width=(.60 if strategic else .82)/zoom
	for q in range(low.x,high.x+1,q_step):
		draw_overview_segment(HexGrid.to_world(Vector2i(q,low.y-2)),HexGrid.to_world(Vector2i(q,high.y+2)),ink,width)
	for r in range(low.y,high.y+1,r_step):
		draw_overview_segment(HexGrid.to_world(Vector2i(low.x-2,r)),HexGrid.to_world(Vector2i(high.x+2,r)),ink,width)
	var diagonal_low=low.x+low.y-2;var diagonal_high=high.x+high.y+2
	var diagonal_step=maxi(stride,ceili(float(diagonal_high-diagonal_low)/96.0))
	for diagonal in range(diagonal_low,diagonal_high+1,diagonal_step):
		draw_overview_segment(HexGrid.to_world(Vector2i(low.x-2,diagonal-low.x+2)),HexGrid.to_world(Vector2i(high.x+2,diagonal-high.x-2)),ink,width)

func draw_overview_segment(a: Vector2, b: Vector2, color: Color, width: float) -> void:
	# Overview guides are clipped to the sourced map polygon so the strategic
	# lattice does not leak into the HUD margins or the surrounding sea backdrop.
	if map_extent.size()<3:
		draw_line(a,b,color,width,true);return
	# Let the engine clip the two-point polyline in one geometry operation. This
	# avoids allocating/sorting intersection points on every redraw of the
	# 74k-cell overview and keeps the same sourced polygon boundary.
	var clipped=Geometry2D.intersect_polyline_with_polygon(PackedVector2Array([a,b]),map_extent)
	for fragment in clipped:
		if fragment is PackedVector2Array and fragment.size()>1:
			draw_polyline(fragment,color,width,true)

func visible_hex_bounds(view: Rect2) -> Array:
	var low=Vector2i(2147483647,2147483647);var high=Vector2i(-2147483647,-2147483647)
	for point in [view.position,Vector2(view.end.x,view.position.y),view.end,Vector2(view.position.x,view.end.y)]:
		var h=HexGrid.from_world(point)
		low=Vector2i(mini(low.x,h.x),mini(low.y,h.y));high=Vector2i(maxi(high.x,h.x),maxi(high.y,h.y))
	return [low-Vector2i.ONE,high+Vector2i.ONE]

func draw_ellipse_shadow(center: Vector2, opacity: float) -> void:
	var start=Time.get_ticks_usec() if profile_draw_enabled else 0
	if shadow_mesh==null:
		var vertices=PackedVector3Array();var indices=PackedInt32Array()
		for i in range(24):vertices.append(Vector3(cos(i*TAU/24)*22,sin(i*TAU/24)*7,0))
		for i in range(1,23):indices.append_array(PackedInt32Array([0,i,i+1]))
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_INDEX]=indices
		shadow_mesh=ArrayMesh.new();shadow_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	draw_mesh(shadow_mesh,null,Transform2D(0,center),Color(.17,.18,.13,.16*opacity))
	if profile_draw_enabled:profile_shadow_usec+=Time.get_ticks_usec()-start

func draw_playback(view: Rect2) -> void:
	if not playback.active:return
	var action=playback.current;var p=playback.progress()
	if action.kind in ["move","rail"]:
		var unit=StateAccess.find({"units":playback.units},"units",action.unit_id)
		if unit.is_empty():return
		var position=playback.position_of(unit)
		if not view.has_point(position):return
		if unit.owner_id!=state.player_faction_id and not VisibilityRules.hex_visible(state,state.player_faction_id,HexGrid.from_world(position)):return
		var definition=content.definition("units",unit.def_id)
		var effect=assets.texture("fx","fx_ship_wake" if MovementRules.domain_of(unit,content)!="land" else ("fx_smoke" if action.kind=="rail" else "fx_dust"))
		if effect!=null:sprite(effect,position+Vector2(-25,15),Vector2(65,40),Color(1,1,1,.22+.12*sin(p*PI)))
	elif action.kind=="attack":
		var origin=HexGrid.to_world(HexGrid.coordinate(action.from));var target=HexGrid.to_world(HexGrid.coordinate(action.position));var direction=(target-origin).normalized()
		if p>=.35 and p<.67:
			var travel=clampf((p-.35)/.32,0,1);var projectile=origin.lerp(target,travel)
			if action.family=="artillery":projectile.y-=sin(travel*PI)*45
			draw_line(projectile-direction*18,projectile,Color("efd49a"),2/zoom,true);draw_circle(projectile,3/zoom,Color("f4ce75"))
			var burst=fmod((p-.35)*28,1) if action.attacker.def_id=="machine_gun" else (p-.35)/.11
			if burst<1:
				var flash=assets.texture("fx","fx_muzzle")
				if flash!=null:sprite(flash,origin+direction*25,Vector2(48,40),Color(1,1,1,.8*(1-burst)))
		if p>=.65 and p<.9:
			var explosion=assets.texture("fx","fx_cannon_blast" if action.family=="artillery" else "fx_bullet_hit")
			if explosion!=null:sprite(explosion,target,Vector2(86,76),Color(1,1,1,(.9-p)/.25))
	elif action.kind=="capture":
		var position=HexGrid.to_world(HexGrid.coordinate(action.position))
		draw_arc(position,24+p*40,0,TAU,48,Color(.93,.82,.53,1-p),3/zoom,true)
		map_name("占领 "+action.name,position+Vector2(0,-72-p*12),24,Color("ddbb72"),1-p*.6)
	elif action.kind=="air":
		var origin=HexGrid.to_world(HexGrid.coordinate(action.from));var target=HexGrid.to_world(HexGrid.coordinate(action.position))
		var position=origin.lerp(target,p/.65) if p<.65 else target+(target-origin).normalized()*(p-.65)*450
		var plane=assets.texture("scenery","scenery_recon_biplane")
		if plane!=null:sprite(plane,position+Vector2(0,-42),Vector2(86,74),Color(1,1,1,minf(p*8,(1-p)*7)))
		if action.bomb and p>=.65:
			var explosion=assets.texture("fx","fx_cannon_blast")
			if explosion!=null:sprite(explosion,target,Vector2(100,90),Color(1,1,1,(1-p)/.35))
		elif not action.bomb:draw_arc(target,24+p*100,-p*TAU,(1-p)*TAU,48,Color(.76,.88,.84,(1-p)*.7),2/zoom,true)
	elif action.kind=="support":
		var position=HexGrid.to_world(HexGrid.coordinate(action.position));var effect=assets.texture("fx",action.effect)
		if effect!=null:sprite(effect,position+Vector2(0,-p*20),Vector2(72,64),Color(1,1,1,sin(p*PI)*.7))
		if action.event.type=="UnitPromoted":map_name("晋为"+action.event.name,position+Vector2(0,-55-p*18),22,Color("cfad6e"),sin(p*PI))

func draw_landscape(view: Rect2) -> void:
	city_control_fill_draw_count=0;territory_field_fill_draw_count=0
	river_surface_draw_count=0;river_texture_draw_count=0;river_ink_draw_count=0
	water_source_texture=assets.texture("tile",MapRiverSurface.TEXTURE_ID)
	var sea=water_source_texture;var plain=assets.texture("tile","tile_plain_01")
	var rectangle=PackedVector2Array([view.position,Vector2(view.end.x,view.position.y),view.end,Vector2(view.position.x,view.end.y)])
	# The authored textures carry the geographic detail; these restrained
	# parchment/sea modulations move the presentation toward the paper atlas
	# treatment used by EW6 without editing or recompositing any source PNG.
	draw_colored_polygon(rectangle,Color("c8c1a4"))
	if map_extent.size()>=4:
		draw_colored_polygon(map_extent,Color("567f84"))
		if extent_surface!=null:draw_mesh(extent_surface,sea,Transform2D.IDENTITY,Color(.82,.88,.83,1.0))
	for fraction in [.07,.93]:
		var at=view.position+Vector2(view.size.x*fraction,view.size.y*.55)
		if map_extent.size()>=4 and not Geometry2D.is_point_in_polygon(at,map_extent):map_name("图幅外",at,int(20/zoom),Color("756e5b"),.62)
	if land_surface!=null:draw_mesh(land_surface,plain,Transform2D.IDENTITY,Color(.94,1.0,.96,1.0))
	if water_surface!=null:draw_mesh(water_surface,sea,Transform2D.IDENTITY,Color(.82,.88,.83,1.0))
	if show_terrain:draw_cell_surface_variants(view)
	if show_control:draw_territory_field(view)
	if show_terrain:draw_cell_terrain_tiles(view)
	if show_control:draw_control_zones(view)
	if show_terrain and relief.mesh!=null:draw_mesh(relief.mesh,null)
	if show_terrain and zoom>.12:
		for contour in relief.contours:
			if view.has_point(contour[0]) or view.has_point(contour[1]):draw_polyline(contour,Color(.36,.33,.25,.20),.65/zoom,true)
	if show_terrain:
		draw_terrain_fabric(view)
		draw_terrain_transitions(view)
		draw_cell_depth(view)
		draw_cell_detail_symbols(view)
		draw_cell_river_details(view)
		draw_cell_micro_symbols(view)
		draw_cell_feature_sprites(view)
		draw_historical_landcover_features(view)
	for points in coast_lines:
		if points.size()>1:
			# A dark surveyed edge with a warm inner keyline reads as a printed
			# historical atlas and keeps the coastline visible below faction wash.
			draw_polyline(points,Color(.12,.22,.24,.52),8.0,true)
			draw_polyline(points,Color("78877a",.76),3.2,true)
			draw_polyline(points,Color("d9d0aa",.70),1.2,true)
	var visible_mains: Array=[]
	for row in river_rows:
		if view.intersects(row.bounds.grow(40)):visible_mains.append(row)
	# Paint all banks before any water, so source confluences do not acquire
	# a decorative bank across the receiving channel. Nothing is snapped.
	for layer in [1,2,3]:
		for row in visible_mains:
			var width=MapHydrography.primary_width(row,state.map.get("strategic_scale",false))
			if MapRiverSurface.paint(self,row,width,.96,water_source_texture,layer) and layer==2:
				river_surface_draw_count+=1
				if width>=4:river_texture_draw_count+=1
	draw_crossing_markers(view)

func draw_crossing_markers(view: Rect2) -> void:
	# Bridges and ferries are sourced map crossings, so their small symbols are
	# drawn from the exact cell endpoints rather than guessed river decorations.
	for crossing in crossing_markers:
		var a: Vector2=crossing.from;var b: Vector2=crossing.to;var midpoint=(a+b)*.5
		if not view.grow(80).has_point(midpoint):continue
		var direction=(b-a).normalized();var normal=direction.orthogonal();var intact=bool(crossing.intact)
		var ink=Color("d6bd79",.88 if intact else .48)
		if crossing.kind=="ferry":
			for index in range(3):
				var at=a.lerp(b,float(index+1)/4.0)
				draw_line(at-normal*5,at+normal*5,Color("ecdfb4",.72 if intact else .38),1.25/zoom,true)
			draw_line(a+normal*4,b+normal*4,Color("6b9ca3",.70 if intact else .34),1.1/zoom,true)
			draw_line(a-normal*4,b-normal*4,Color("6b9ca3",.70 if intact else .34),1.1/zoom,true)
		else:
			draw_line(a+normal*5,b+normal*5,Color("ead8a6",.82 if intact else .40),4.0/zoom,true)
			draw_line(a-normal*5,b-normal*5,Color("6e5c45",.86 if intact else .40),2.0/zoom,true)
			for index in range(3):
				var at=a.lerp(b,float(index+1)/4.0)
				draw_line(at-normal*8,at+normal*8,ink,1.4/zoom,true)
		if zoom>=.34:
			var caption="渡口" if crossing.kind=="ferry" else ("桥" if crossing.rail_allowed else "桥")
			map_name(caption,midpoint+normal*18,15,Color("80643e"),.82 if intact else .45)

func prepare_territory_field() -> void:
	# The published administrative polygons are available for the local theatre
	# maps.  The continental layer deliberately has no unsupported county
	# borders, so its broad control wash is derived from the real playable city
	# nodes and their current owners.  This is a presentation Voronoi field: it
	# never mutates cell ownership, movement or combat rules.
	var signature=state.map.get("id","")+"|"+places.owner_signature
	if signature==territory_field_signature:return
	territory_field_signature=signature
	territory_field_meshes.clear();territory_field_cells.clear();territory_field_borders.clear();territory_field_diagnostics={}
	if state.is_empty() or not state.map.get("strategic_scale",false):return
	var clipped=MapControlLandClip.for_map(state.map)
	if clipped.is_empty():
		territory_field_diagnostics={"enabled":false,"land_clipped":false,"reason":"missing_or_stale_source_land_clip"}
		return
	var sources: Array=[]
	for city in state.cities:
		var owner=str(city.get("owner_id",""))
		if owner.is_empty():continue
		var position=HexGrid.coordinate(city.position)
		var radius=maxf(3.0,float(city.get("control_radius_hex",4)))
		sources.append({"hex":position,"world":HexGrid.to_world(position),"owner":owner,"radius":radius,"id":str(city.get("id",""))})
	if sources.is_empty():return
	var meshes: Dictionary={};var assigned=0;var skipped=0
	for cell in state.map.cells:
		if not cell.get("render_land_covered",false):continue
		var terrain=str(cell.get("natural_terrain_id",cell.get("terrain_id","")))
		if terrain=="sea":continue
		var hex=HexGrid.coordinate(cell.position);var nearest={};var nearest_score=INF
		for source in sources:
			var distance=float(HexGrid.distance(hex,source.hex))
			# Capital and provincial centres project farther than a village, while
			# still leaving remote unsurveyed land uncoloured instead of inventing
			# a political frontier across it.
			var reach=source.radius+9.0
			if distance>reach:continue
			var score=distance/(source.radius+5.0)
			if score<nearest_score or (is_equal_approx(score,nearest_score) and source.id<str(nearest.get("id",""))):
				nearest_score=score;nearest=source
		if nearest.is_empty():skipped+=1;continue
		var piece: Dictionary=clipped.field_clips.get(HexGrid.key(hex),{})
		if not piece.is_empty() and MapControlLandClip.vertices(piece).is_empty():continue
		var owner=str(nearest.owner);territory_field_cells[hex]=owner;assigned+=1
		if not meshes.has(owner):meshes[owner]={"vertices":PackedVector3Array(),"cells":0}
		var vertices: PackedVector3Array=meshes[owner].vertices
		if piece.is_empty():
			var center=HexGrid.to_world(hex);var polygon=HexGrid.corners(center,float(clipped.field_radius))
			for index in range(6):
				var next=(index+1)%6
				vertices.append(Vector3(center.x,center.y,0))
				vertices.append(Vector3(polygon[index].x,polygon[index].y,0))
				vertices.append(Vector3(polygon[next].x,polygon[next].y,0))
		else:vertices.append_array(MapControlLandClip.vertices(piece))
		meshes[owner].vertices=vertices;meshes[owner].cells=int(meshes[owner].cells)+1
	for owner in meshes:
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=meshes[owner].vertices
		var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		territory_field_meshes[owner]=mesh
	# Only visit three axial directions.  That yields one clean political edge
	# per shared cell boundary and keeps the static command stream bounded.
	for hex in territory_field_cells:
		var owner=str(territory_field_cells[hex]);var center=HexGrid.to_world(hex);var corners=HexGrid.corners(center,47.4)
		for direction_index in range(3):
			var other_hex=hex+HexGrid.DIRECTIONS[direction_index];var other_owner=str(territory_field_cells.get(other_hex,""))
			if other_owner.is_empty() or other_owner==owner:continue
			var pair=[[0,1],[5,0],[4,5]][direction_index]
			var piece: Dictionary=clipped.field_clips.get(HexGrid.key(hex),{})
			if piece.is_empty():
				territory_field_borders.append({"a":corners[pair[0]],"b":corners[pair[1]],"owner":owner,"other":other_owner})
			else:
				for segment in piece.edges[direction_index]:
					territory_field_borders.append({"a":Vector2(segment[0][0],segment[0][1]),"b":Vector2(segment[1][0],segment[1][1]),"owner":owner,"other":other_owner})
	territory_field_diagnostics={"enabled":true,"cells_assigned":assigned,"cells_skipped":skipped,"owners":territory_field_meshes.size(),"border_segments":territory_field_borders.size(),"presentation_only":true,"source":"current_owned_real_city_nodes_voronoi","land_clipped":true,"clip":MapControlLandClip.diagnostics(clipped),"minimap_reuses_same_meshes":true}

func draw_territory_field(view: Rect2) -> void:
	if territory_field_meshes.is_empty():return
	var alpha=TERRITORY_FIELD_OPACITY
	if state.map.get("strategic_scale",false):alpha=.23 if zoom<.24 else .20
	for owner in territory_field_meshes:
		var color=faction_color(str(owner));color.a=alpha
		draw_mesh(territory_field_meshes[owner],null,Transform2D.IDENTITY,color)
		territory_field_fill_draw_count+=1
	if zoom<.12:return
	for border in territory_field_borders:
		var owner_color=faction_color(str(border.owner));var other_color=faction_color(str(border.other))
		var ink=owner_color.lerp(other_color,.5);ink.a=TERRITORY_FIELD_BORDER_OPACITY
		draw_line(border.a,border.b,Color("e7d7a4",.34),maxf(.95,1.35/zoom),true)
		draw_line(border.a,border.b,ink,maxf(.50,.72/zoom),true)

func draw_cell_terrain_tiles(view: Rect2) -> void:
	terrain_tile_draw_count=0
	var strategic=state.map.get("strategic_scale",false)
	if zoom<(.18 if strategic else .30):return
	# Terrain materials blend into continuous ground. Buildings, water and
	# transport have their own sourced geometry, never opaque hex pictures.
	for entry in visible_terrain_entries(view):
		var kind: String=entry.kind
		if kind not in ["forest","wetland","hill","mountain","peak"]:continue
		if not TerrainVisuals.keep_at_overview(entry.cell,kind,strategic,zoom):continue
		var color: Color={"forest":Color("64855b"),"wetland":Color("74928a"),"hill":Color("a5ad83"),"mountain":Color("758777"),"peak":Color("80918c")}[kind]
		color.a=.12 if kind=="forest" else .09
		draw_ground_blend(HexGrid.to_world(entry.hex),color,46.8)
		terrain_tile_draw_count+=1

func draw_ground_blend(center: Vector2, color: Color, radius: float) -> void:
	# Vertex alpha feathers the source-class wash. No raster is edited and no
	# dark hard-edged hex slab is introduced below the miniature scenery.
	var corners=HexGrid.corners(center,radius)
	for index in range(6):
		var polygon=PackedVector2Array([center,corners[index],corners[(index+1)%6]])
		draw_polygon(polygon,PackedColorArray([color,Color(color,0.0),Color(color,0.0)]))

func draw_cell_surface_variants(view: Rect2) -> void:
	# Regional source geometry chooses a visible seamless ground material.
	# Feathered edges retain the continuous surveyed land underneath, while
	# ownership remains its own translucent layer above the ground.
	terrain_surface_variant_draw_count=0
	var strategic=state.map.get("strategic_scale",false)
	var threshold=.10
	if zoom<threshold:
		# Far overview still draws the relief mesh. Bind its numerical sampler
		# even when the detailed ground-material batches are omitted.
		var ground=map_details.ground_material(strategic) if MapArtBank.available() else null
		relief.shade_field.bind_to(ground,continuous_relief_enabled);material=ground
		return
	if MapArtBank.available():
		var ground=map_details.ground_material(strategic)
		relief.shade_field.bind_to(ground,continuous_relief_enabled)
		material=ground
		var fine_details=zoom>=(.20 if strategic else .28)
		if ground==null and not fine_details:return
		var entries=visible_terrain_entries(view) if fine_details else []
		var batches=map_details.surface_meshes(entries,strategic,12000,ground!=null,true,ground==null)
		# Canvas drawing keeps mesh RIDs. Keep the owning resources alive for
		# the entire cached draw, including textures evicted from the asset LRU.
		ground_material_batches=[]
		var macro_count=0
		if ground!=null:
			var chunks=map_details.continuous_macro_meshes(view);macro_count=chunks.count
			ground_material_batches.append_array(chunks.batches)
		ground_material_batches.append_array(batches.batches)
		for batch in ground_material_batches:
			if batch.get("continuous",false):draw_mesh(batch.mesh,null)
			else:
				var source_texture=assets.texture("tile",batch.asset_id)
				if source_texture!=null:
					batch["texture"]=source_texture
					draw_mesh(batch.mesh,source_texture)
		terrain_surface_variant_draw_count=maxi(batches.count,macro_count)
		return
	var texture=assets.texture("tile","tile_plain_02")
	if texture==null:return
	var max_variants=1500 if strategic else 1900
	for entry in visible_terrain_entries(view):
		if terrain_surface_variant_draw_count>=max_variants:break
		var cell: Dictionary=entry.cell;var kind: String=entry.kind
		if kind!="plain" or not cell.get("render_land_covered",false):continue
		# Deterministic half-density keeps the atlas legible while ensuring the
		# normal play camera never shows a perfectly flat uninterrupted field.
		if absi(hash(str(cell.get("id",HexGrid.key(entry.hex)))))%2!=0:continue
		var center=HexGrid.to_world(entry.hex);var polygon=HexGrid.corners(center,46.0)
		var uvs=PackedVector2Array()
		for index in range(polygon.size()):
			var angle=float(index)*PI/3.0;uvs.append(Vector2(.5+.5*cos(angle),.5+.5*sin(angle)))
		var alpha=.025 if strategic else .04
		var colors=PackedColorArray()
		for index in range(polygon.size()):colors.append(Color(1,1,1,alpha))
		draw_polygon(polygon,colors,uvs,texture);terrain_surface_variant_draw_count+=1

func draw_cell_depth(view: Rect2) -> void:
	terrain_depth_draw_count=0
	if zoom<.38:return
	# Volume belongs to the tree/rock silhouettes and their ground contacts.
	# A soft directional shadow supports source relief, without raising every
	# operation hex into a separate six-sided box.
	for entry in visible_terrain_entries(view):
		if entry.kind not in ["hill","mountain","peak"]:continue
		var alpha=.045 if entry.kind=="hill" else .065
		draw_ground_blend(HexGrid.to_world(entry.hex)+Vector2(5,7),Color(.20,.29,.25,alpha),39)
		terrain_depth_draw_count+=1

func draw_cell_detail_symbols(view: Rect2) -> void:
	# At the intermediate strategic zoom the full relief sprites are still too
	# sparse to tell a player what an individual source cell contains. These
	# compact vector glyphs are derived only from the authored terrain class;
	# they add no forests, roads or settlements and disappear at tactical scale
	# where the richer immutable scenery sprites take over.
	terrain_symbol_draw_count=0
	# The production bank now supplies the actual painted ground and scenery.
	# Retain the old vector legend only as a missing-bank fallback; repeating it
	# underneath the painted relief made the regional map look like debug data.
	if MapArtBank.available():return
	if not state.map.get("strategic_scale",false) or zoom<.18 or zoom>.54:return
	var alpha=clampf((zoom-.18)/.22,0.0,1.0)*.48
	if alpha<=0.01:return
	var processed=0
	for entry in visible_terrain_entries(view):
		if processed>=900:break
		var kind: String=entry.kind
		if kind not in ["forest","hill","mountain","peak","wetland"]:continue
		if not TerrainVisuals.keep_at_overview(entry.cell,kind,true,zoom):continue
		var p=HexGrid.to_world(entry.hex)
		if not view.has_point(p):continue
		var seed=absi(hash(str(entry.cell.get("id",HexGrid.key(entry.hex)))))
		var tone=Color("4e6450",alpha) if kind=="forest" else Color("59615a",alpha)
		var scale=clampf(zoom/.32,.62,1.25)
		if kind=="forest":
			for index in range(3):
				var x=float(index-1)*9.0*scale
				var base=p+Vector2(x,6.0*scale)
				var top=base+Vector2(((-1 if (seed+index)%2 else 1)*2.0),-12.0*scale)
				draw_line(base,top,tone,1.7/zoom,true)
				draw_line(top+Vector2(-4,5)*scale,top+Vector2(4,5)*scale,tone,1.1/zoom,true)
		elif kind=="wetland":
			for index in range(3):
				var y=float(index-1)*5.0*scale
				draw_line(p+Vector2(-12,y),p+Vector2(12,y+2.0*scale),Color("547675",alpha),1.15/zoom,true)
		else:
			var ridge=PackedVector2Array([p+Vector2(-15,7)*scale,p+Vector2(-4,-8)*scale,p+Vector2(5,5)*scale,p+Vector2(13,-4)*scale,p+Vector2(18,8)*scale])
			draw_polyline(ridge,tone,1.45/zoom,true)
			if kind in ["mountain","peak"]:
				draw_line(p+Vector2(-8,8)*scale,p+Vector2(1,-5)*scale,Color("d8d1ae",alpha*.74),.8/zoom,true)
		terrain_symbol_draw_count+=1;processed+=1

func draw_cell_river_details(view: Rect2) -> void:
	terrain_cell_river_draw_count=0
	var strategic=state.map.get("strategic_scale",false)
	if zoom<(.42 if strategic else .38):return
	# Only archived vector tributaries are drawn. Adjacency between river-class
	# hexes cannot establish a real watercourse or justify invented streams.
	var rows=MapHydrography.visible_rows(detail_river_lines,detail_river_buckets,view,zoom,strategic)
	for layer in [1,2,3]:
		for row in rows:
			var order=int(row.get("stream_order",0));var fine=order>0
			var display_points: PackedVector2Array=row.get("display_points",row.points)
			var width=MapHydrography.symbolic_width(order,strategic,1.25 if strategic else 1.7)
			var opacity=clampf((zoom-float(row.get("min_zoom",.38))+.10)/.24,0.0,1.0)*(.88 if fine else .86)
			if MapRiverSurface.paint(self,row,width,opacity,water_source_texture,layer) and layer==2:
				river_surface_draw_count+=1
				if width<MapRiverSurface.SMALL_STREAM_LIMIT:river_ink_draw_count+=1
				if width>=4:river_texture_draw_count+=1
				terrain_cell_river_draw_count+=display_points.size()-1

func draw_cell_micro_symbols(view: Rect2) -> void:
	terrain_micro_symbol_draw_count=0
	if MapArtBank.available():return
	if zoom<.42:return
	# Actual rail links and river geometry already carry transportation/water.
	# Reeds are a land-cover symbol, gated by the source wetland classification.
	for entry in visible_terrain_entries(view):
		if entry.kind!="wetland":continue
		var p=HexGrid.to_world(entry.hex)
		for index in range(3):
			var x=float(index-1)*7.0
			draw_line(p+Vector2(x,7),p+Vector2(x+2,-8),Color("4d7770",.66),maxf(.55,.95/zoom),true)
		terrain_micro_symbol_draw_count+=1

func draw_cell_feature_sprites(view: Rect2) -> void:
	terrain_feature_sprite_draw_count=0
	if MapArtBank.available():
		terrain_feature_sprite_draw_count=map_details.visible_features(view,zoom).filter(func(feature):return feature.source_kind=="forest").size()
		return
	var strategic=state.map.get("strategic_scale",false)
	if zoom<(.28 if strategic else .42):return
	var entries=visible_terrain_entries(view)
	entries.sort_custom(func(a,b):return HexGrid.to_world(a.hex).y<HexGrid.to_world(b.hex).y)
	for entry in entries:
		if entry.kind!="forest":continue
		var seed=absi(hash(str(entry.cell.get("id",HexGrid.key(entry.hex)))))
		if strategic and zoom<.42 and seed%2!=0:continue
		var profile=TerrainVisuals.edge_profile(presentation_cells,entry.hex,"forest")
		var sparse=int(profile.boundary_edges)>=3
		var pine=seed%3!=0
		var tree_id="scenery_forest_pine" if pine else "scenery_forest_mixed"
		if sparse:tree_id+="_sparse"
		var tree=assets.texture("scenery",tree_id)
		if tree==null:tree=assets.texture("scenery","scenery_forest_pine")
		if tree==null:continue
		var p=HexGrid.to_world(entry.hex)+Vector2(float(seed%13-6),float(seed%9-4)-15)
		var dimensions=Vector2(94,89) if not sparse else Vector2(78,80)
		# Source crown/trunk silhouettes supply the depth. The complete original
		# PNG and native aspect ratio are retained by sprite().
		sprite(tree,p,dimensions*(.94+float(seed%9)*.012),Color.WHITE)
		terrain_feature_sprite_draw_count+=1

func draw_historical_landcover_features(view: Rect2) -> void:
	historical_landcover_patch_cells=terrain_feature_sprite_draw_count
	if zoom<.56:return
	# Named sites are evidence anchors, not hex-shaped forest boundary claims.
	# Their bounded source classes are rendered by the same foliage pass above.
	for feature in historical_landcover_features:
		var p=Vector2(feature.world_position[0],feature.world_position[1])
		if not view.has_point(p):continue
		var offset=feature.get("visual_offset",[])
		if offset.size()>=2:p+=Vector2(float(offset[0]),float(offset[1]))
		map_name(str(feature.get("name","林地")),p+Vector2(0,45),int(clampf(14.0*label_scale/zoom,14,26)),Color("30473f"),.92)

func draw_terrain_transitions(_view: Rect2) -> void:
	# Class transitions are carried by feathered ground and irregular object
	# silhouettes. The optional operation grid is drawn separately.
	terrain_transition_draw_count=0

func visible_terrain_entries(view: Rect2) -> Array:
	var bounds=visible_hex_bounds(view);var low:Vector2i=bounds[0];var high:Vector2i=bounds[1]
	var bucket_low=Vector2i(floori(float(low.x)/16.0)-1,floori(float(low.y)/16.0)-1)
	var bucket_high=Vector2i(floori(float(high.x)/16.0)+1,floori(float(high.y)/16.0)+1)
	var result: Array=[];var area=view.grow(52)
	for bx in range(bucket_low.x,bucket_high.x+1):
		for by in range(bucket_low.y,bucket_high.y+1):
			for entry in terrain_visual_buckets.get(Vector2i(bx,by),[]):
				if area.has_point(HexGrid.to_world(entry.hex)):result.append(entry)
	return result

func draw_terrain_fabric(_view: Rect2) -> void:
	# Hand-painted source relief replaces repeated synthetic ridge hatching.
	pass

func rounded_track(points: PackedVector2Array) -> PackedVector2Array:
	var rounded=PackedVector2Array([points[0]])
	for i in range(1,points.size()-1):
		var before=points[i-1];var at=points[i];var after=points[i+1]
		var distance=minf(12,minf(before.distance_to(at),after.distance_to(at))*.2)
		var entry=at+(before-at).normalized()*distance;var exit=at+(after-at).normalized()*distance
		for step in range(7):
			var t=step/6.0;rounded.append(entry*(1-t)*(1-t)+at*2*(1-t)*t+exit*t*t)
	rounded.append(points[points.size()-1]);return rounded

func map_name(text: String, position: Vector2, font_size: int, color: Color, opacity: float) -> void:
	var font=assets.map_font;var pixels=maxi(1,roundi(font_size*zoom))
	var width=font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,pixels).x
	var baseline=world_to_screen(position)+Vector2(-width*.5,font_size*zoom*.35)
	draw_set_transform(Vector2.ZERO)
	draw_string_outline(font,baseline,text,HORIZONTAL_ALIGNMENT_LEFT,-1,pixels,1,Color("f0e2ba") if color.get_luminance()<.5 else Color("405356"))
	draw_string(font,baseline,text,HORIZONTAL_ALIGNMENT_LEFT,-1,pixels,Color(color,opacity))
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func draw_screen_label(text: String, baseline: Vector2, pixels: int, color: Color) -> void:
	# Screen-size glyphs stay small and stable while the geographic anchor moves.
	# Avoid allocating hundreds of huge font atlases when zooming out fivefold.
	draw_set_transform(Vector2.ZERO)
	draw_string(assets.map_font,world_to_screen(baseline),text,HORIZONTAL_ALIGNMENT_LEFT,-1,pixels,color)
	draw_set_transform(size*.5-camera*zoom,0,Vector2.ONE*zoom)

func draw_control_zones(view: Rect2, foreground: bool=false) -> void:
	# Continental control already has one disjoint, source-clipped field. City
	# influence polygons overlap it and each other; another translucent pass
	# compounds the wash and creates dark patches unrelated to terrain/ownership.
	if state.map.get("strategic_scale",false):return
	for zone in places.zones:
		var owner=places.owners.get(zone.city_id,"")
		if owner.is_empty() or not view.intersects(zone.bounds):continue
		var color=faction_color(owner);color.a=.10 if foreground else TERRITORY_OPACITY
		# The backdrop owns the single translucent fill pass. The foreground pass
		# only inks the surveyed influence edge; drawing the mesh twice made the
		# nominal alpha look opaque on dense city clusters.
		if not foreground:
			draw_mesh(zone.mesh,null,Transform2D.IDENTITY,color);city_control_fill_draw_count+=1
		# Borders remain readable at tactical zoom as well as the country overview.
		# These are city influence areas clipped to surveyed period provinces; they
		# do not claim to be surveyed historical county or military frontiers.
		if not foreground:continue
		for border in zone.borders:
			if border.size()>1:
				draw_polyline(border,Color(.15,.24,.29,.38),2.8/zoom,true)
				var edge_color=color.lightened(.20);edge_color.a=.78
				draw_polyline(border,edge_color,1.5/zoom,true)

func control_legend_ids() -> Array:
	var represented={}
	for owner in places.owners.values():represented[owner]=true
	var ids: Array=[]
	for id in state.turn_order:
		if represented.has(id):ids.append(id)
	return ids

func control_legend_rect(ids: Array) -> Rect2:
	if ids.is_empty() or not show_control:return Rect2()
	var columns=control_legend_columns(ids);var rows=ceili(float(ids.size())/columns)
	var s=legend_scale();var area=map_hud_area();var terrain=terrain_legend_rect()
	var origin=area.position
	if terrain.has_area():
		if area.size.x-terrain.size.x-12*s>=154*s:origin.x=terrain.end.x+12*s
		else:origin.y=terrain.end.y+8*s
	return Rect2(origin,Vector2(columns*134+20,32+rows*25)*s)

func control_legend_columns(ids: Array) -> int:
	var s=legend_scale();var area=map_hud_area();var terrain=terrain_legend_rect();var width=area.size.x
	if terrain.has_area() and area.size.x-terrain.size.x-12*s>=154*s:width-=terrain.size.x+12*s
	return clampi(int((width/s-20)/134),1,mini(4,maxi(1,ids.size())))

func label_overlay_obstacles() -> Array:
	var result: Array=[]
	for box in [control_legend_rect(control_legend_ids()),terrain_legend_rect()]:
		if box.has_area():result.append(Rect2(camera+(box.position-size*.5)/zoom,box.size/zoom))
	for control in label_obstacle_controls:
		if not is_instance_valid(control) or not control.is_visible_in_tree():continue
		var rect:Rect2=control.get_global_rect();rect.position-=global_position;rect=rect.grow(4*label_scale)
		if rect.has_area():result.append(Rect2(camera+(rect.position-size*.5)/zoom,rect.size/zoom))
	return result

func draw_control_legend() -> void:
	var ids=control_legend_ids();var box=control_legend_rect(ids)
	if not box.has_area():return
	var columns=control_legend_columns(ids)
	var s=legend_scale()
	draw_rect(box,Color(.10,.15,.19,.93));draw_rect(box,Color("91a3a8"),false,1)
	draw_string(assets.font,box.position+Vector2(10,21)*s,"势力归属",HORIZONTAL_ALIGNMENT_LEFT,-1,int(16*s),Color("e8e7d5"))
	for index in range(ids.size()):
		var at=box.position+Vector2(10+(index%columns)*134,32+(index/columns)*25)*s
		draw_rect(Rect2(at,Vector2(11,11)*s),faction_color(ids[index]))
		var name=StateAccess.faction_name(state,ids[index],content).replace("军政集团","").replace("地方军事集团","")
		name=ellipsized_label(name,int(14*s),108*s)
		draw_string(assets.font,at+Vector2(17,11)*s,name,HORIZONTAL_ALIGNMENT_LEFT,-1,int(14*s),Color("e8e7d5"))

func draw_places(view: Rect2) -> void:
	drawn_place_counter_ids=[];drawn_place_detail_ids=[]
	if not show_places:return
	for node in place_references:
		if not view.has_point(node.at) or not map_place_visible(node):continue
		var rank=HistoricalPlaces.importance(node,state.date)
		if not MapSemanticZoom.detailed(zoom,node.id==selected_place_id):
			draw_city_counter(node.at,node);drawn_place_counter_ids.append(node.id)
		else:
			drawn_place_detail_ids.append(node.id)
			var bounds:Vector2=node.sprite_bounds
			if node.sprite_on_land and node.has("bank_asset_id"):
				var rectangle: Rect2=node.bank_texture_rect;rectangle.position+=node.at+Vector2(0,26)
				draw_texture_rect(assets.texture("building",node.bank_asset_id),rectangle,false,Color(1,1,1,.96))
			elif node.sprite_on_land:sprite(assets.texture("scenery",HistoricalPlaces.asset_id(node,state.date)),node.at+Vector2(0,-12),bounds,Color(1,1,1,.94))
			else:draw_circle(node.at,4.0/zoom,Color("796c51"));draw_arc(node.at,7.0/zoom,0,TAU,24,Color("eee0ba"),1.0/zoom,true)
		if node.id==selected_place_id:draw_arc(node.at,30.0/zoom,0,TAU,40,Color("a77936"),2.0/zoom,true)

func prepare_label_records() -> void:
	var selection=selected_city_id+"|"+selected_place_id+"|"+selected_unit_id
	if label_cache_revision==label_revision and is_same(label_cache_state,state) and label_cache_selection==selection:return
	label_cache_revision=label_revision;label_cache_state=state;label_cache_selection=selection
	label_unit_points=[]
	for unit in state.units:
		if unit.position==null or not VisibilityRules.unit_visible(state,state.player_faction_id,unit):continue
		var hex=HexGrid.coordinate(unit.position)
		label_unit_points.append({"id":unit.id,"position":HexGrid.to_world(hex),"in_city":not StateAccess.at(state,"cities",hex).is_empty()})
	var cities: Array=[]
	for city in state.cities:cities.append({"node":city,"priority":city_label_priority(city)})
	cities.sort_custom(func(a,b):return a.priority>b.priority if a.priority!=b.priority else a.node.id<b.node.id)
	label_city_nodes=cities.map(func(record):return record.node)
	var references: Array=[]
	for node in place_references:references.append({"node":node,"priority":1000 if node.id==selected_place_id else HistoricalPlaces.importance(node,state.date)})
	references.sort_custom(func(a,b):return a.priority>b.priority if a.priority!=b.priority else a.node.id<b.node.id)
	label_place_nodes=references.map(func(record):return record.node)

func label_text_width(text: String, pixels: int) -> float:
	var key=str(assets.map_font.get_instance_id())+"|"+str(pixels)+"|"+text
	if not label_text_widths.has(key):label_text_widths[key]=assets.map_font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,pixels).x
	return label_text_widths[key]

func place_label_layout(view: Rect2) -> Array:
	prepare_label_records()
	var result: Array=[];var occupied: Array=label_overlay_obstacles()
	for label in drawn_labels:occupied.append(label.rect)
	for record in label_unit_points:
		var at:Vector2=record.position
		if view.has_point(at):occupied.append(unit_label_obstacle(record))
	var screen_view=Rect2(camera-size/(2*zoom),size/zoom)
	for node in label_place_nodes:
		if not view.has_point(node.at) or not map_place_visible(node):continue
		var kind=HistoricalPlaces.kind(node,state.date)
		var text=node.name+(" · 省城" if kind=="capital" else " · 首都" if kind=="national_capital" else " · 县" if kind=="county" else " · 村" if kind=="village" else "")
		var font_pixels=ceili((16 if kind=="village" else 17)*label_scale);var font_size=ceili(float(font_pixels)/zoom)
		var dimensions=Vector2((label_text_width(text,font_pixels)+10)/zoom,23*label_scale/zoom)
		for shift in [Vector2(0,42),Vector2(0,-64/zoom),Vector2((dimensions.x+16/zoom)*.5,18/zoom),Vector2(-(dimensions.x+16/zoom)*.5,18/zoom),Vector2(0,72/zoom),Vector2(0,108/zoom)]:
			var rect=Rect2(node.at+shift-dimensions*.5,dimensions)
			if not screen_view.encloses(rect):continue
			var collision=false
			for other in occupied:
				if rect.grow(4/zoom).intersects(other):collision=true;break
			if collision:continue
			result.append({"city_id":node.id,"text":text,"position":node.at,"rect":rect,"font_size":font_size,"font_pixels":font_pixels,"shifted":shift!=Vector2(0,42)});occupied.append(rect);break
	return result

func draw_place_labels(view: Rect2) -> void:
	var labels=place_label_layout(view)
	for label in labels:
		var rect:Rect2=label.rect
		if label.shifted:draw_line(label.position,rect.get_center(),Color(.31,.27,.18,.58),.8/zoom,true)
		draw_rect(rect,Color(.90,.94,.89,.90));draw_rect(rect,Color(.27,.38,.41,.7),false,.6/zoom)
		draw_screen_label(label.text,rect.position+Vector2(5/zoom,17.5*label_scale/zoom),label.font_pixels,Color("233640"))
	drawn_labels.append_array(labels)

func unit_label_obstacle(record: Dictionary) -> Rect2:
	var point: Vector2=record.position
	if not MapSemanticZoom.detailed(zoom,str(record.id)==selected_unit_id):
		var dimensions=(MapSemanticZoom.unit_size(zoom)+Vector2.ONE*5)/zoom
		return Rect2(point-dimensions*.5,dimensions)
	if record.in_city:point+=Vector2(29,17)
	return Rect2(point+Vector2(-39,-48),Vector2(82,83))

func city_label_layout(view: Rect2) -> Array:
	prepare_label_records()
	var labels: Array=[];var occupied: Array=label_overlay_obstacles()
	for record in label_unit_points:
		var point:Vector2=record.position
		if not view.has_point(point):continue
		occupied.append(unit_label_obstacle(record))
	var visible_rect=Rect2(camera-size/(2*zoom),size/zoom)
	var font_pixels=ceili(18.0*label_scale);var font_size=ceili(float(font_pixels)/zoom)
	for city in label_city_nodes:
		var point=HexGrid.to_world(HexGrid.coordinate(city.position))
		if not view.has_point(point) or (zoom<.52 and not city.key_city and city.id!=selected_city_id):continue
		var role=HistoricalPlaces.kind(city,state.date)
		var text=city.name+(" · 首都" if role=="national_capital" else " · 省城" if role=="capital" else " ★" if city.key_city else "")
		var width=label_text_width(text,font_pixels)/zoom
		var dimensions=Vector2(width+14/zoom,24.0*label_scale/zoom)
		var anchor=point+Vector2(0,54)
		for shift in [Vector2.ZERO,Vector2(0,34/zoom),Vector2(0,-98/zoom),Vector2((width+26/zoom)*.5,0),Vector2(-(width+26/zoom)*.5,0),Vector2(0,72/zoom),Vector2(0,108/zoom)]:
			var center=anchor+shift;var rect=Rect2(center-dimensions*.5,dimensions)
			if not visible_rect.encloses(rect):continue
			var collides=false
			for other in occupied:
				if rect.grow(3/zoom).intersects(other):collides=true;break
			if collides:continue
			labels.append({"city_id":city.id,"text":text,"position":point,"rect":rect,"font_size":font_size,"font_pixels":font_pixels,"shifted":shift!=Vector2.ZERO});occupied.append(rect);break
	return labels

func city_label_priority(city: Dictionary) -> int:
	return (100 if city.id==selected_city_id else 0)+HistoricalPlaces.importance(city,state.date)*10+(20 if city.key_city else 0)+int(city.level)

func capture_labels() -> Array:
	var result: Array=[]
	for label in foreground_view.drawn_labels if foreground_view!=null else drawn_labels:
		var rect:Rect2=label.rect;var at=world_to_screen(rect.position)
		result.append({"city_id":label.city_id,"text":label.text,"screen_rect":[at.x,at.y,rect.size.x*zoom,rect.size.y*zoom],"font_pixels":label.font_pixels,"shifted":label.shifted})
	return result

func draw_city_labels(view: Rect2) -> void:
	drawn_labels=city_label_layout(view)
	for label in drawn_labels:
		var rect:Rect2=label.rect
		if label.shifted:draw_line(label.position,rect.get_center(),Color(.31,.27,.18,.74),.8/zoom,true)
		var city=StateAccess.find(state,"cities",label.city_id)
		var owner=faction_color(city.get("owner_id",""))
		draw_rect(rect,Color(.10,.16,.20,.93));draw_rect(rect,Color("9baeb2"),false,.8/zoom)
		draw_rect(Rect2(rect.position,Vector2(3/zoom,rect.size.y)),owner)
		draw_screen_label(label.text,rect.position+Vector2(7/zoom,18.5*label_scale/zoom),label.font_pixels,Color("f1efe0"))

func draw_bohai_label(view: Rect2) -> void:
	var visible_size=size if annotation_view_size==Vector2.ZERO else annotation_view_size
	var visible_area=Rect2(camera-visible_size/(2*zoom),visible_size/zoom).grow(-30/zoom)
	var surveyed_at=Vector2.ZERO;var has_surveyed_label=false
	for mark in state.map.get("render_labels",[]):
		if mark.name!="渤海":continue
		surveyed_at=Vector2(mark.position[0],mark.position[1]);has_surveyed_label=true
		if visible_area.has_point(surveyed_at):return
	if not has_surveyed_label:return
	var target=camera+Vector2(visible_size.x*.30,visible_size.y*.23)/zoom
	var best=INF;var label_at=Vector2.ZERO
	var inside=Rect2(camera-visible_size/(2*zoom),visible_size/zoom).grow(-90/zoom)
	var bounds=visible_hex_bounds(inside)
	var label_radius=180000.0*HexGrid.RADIUS/state.map.hex_radius_m
	for q in range(bounds[0].x,bounds[1].x+1):
		for r in range(bounds[0].y,bounds[1].y+1):
			var cell=presentation_cells.get(Vector2i(q,r),{})
			if cell.is_empty() or cell.terrain_id!="sea":continue
			var p=HexGrid.to_world(Vector2i(q,r))
			if not inside.has_point(p) or p.distance_to(surveyed_at)>label_radius:continue
			var score=p.distance_squared_to(target)
			if score<best:best=score;label_at=p
	if best<INF:map_name("渤海",label_at,52,Color("eee5ca"),.83)

func draw_regions(view: Rect2) -> void:
	if zoom>.95 or state.mode=="legion":return
	var year=ContentRegistry.administration_year(state.date)
	for region in state.map.get("admin_layers",{}).get(year,[]):
		var p=Vector2(region.label_position[0],region.label_position[1])
		if view.has_point(p):map_name(ContentRegistry.administration_label(region.name,state.date),p,int(clampf(20.0*label_scale/zoom,32,110)),Color("474331"),.94)

func command_flag(position: Vector2, owner: String, height: float) -> void:
	var color=faction_color(owner);var short={"zhili":"直","anhui":"皖","fengtian":"奉","shanxi":"晋","jiangsu":"苏","zhejiang":"浙","yunnan":"滇","sichuan":"川","guangdong":"粤","guominjun":"国","qing":"清","british_empire":"英","british_india":"印","french_empire":"法","russian_empire":"俄","russian_provisional":"临","soviet":"苏","japan":"日","korea":"韩","ottoman":"奥","qajar_persia":"波","afghanistan":"阿","siam":"暹","taiping":"太","boxers":"义","eight_nation":"联","beiyang_gov":"北","guangzhou_government":"护","bolsheviks":"布","mongolia":"蒙","tibet":"藏","kmt":"国","ccp":"共","japanese_occupied":"占","vichy_france":"维"}.get(owner,"军")
	if owner=="guominjun" and StateAccess.faction(state,owner).has("name_override"):short="冯"
	draw_line(position+Vector2(0,-4),position+Vector2(0,height+17),Color("292c28"),1.4,true)
	var plate=Rect2(position,Vector2(height*1.2,height));draw_rect(plate,color);draw_rect(plate,Color("e7d8ac"),false,.7)
	if (height-1)*zoom>=8:draw_string(assets.font,position+Vector2(2,height-2),short,HORIZONTAL_ALIGNMENT_LEFT,-1,int(height-1),Color("f1e6c9"))
