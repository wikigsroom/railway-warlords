class_name TerrainSurfaceQA
extends RefCounted

# Uses real scenario geometry and normal MapView rendering. No illustration,
# stitched image or synthetic tile board stands in for an in-game map.
var app
var checks: Array=[]
var captures: Array=[]
var folder=""
var withheld_forest_families: Array=[]
const PREFERRED={
	"temperate_meadow":Vector2(115,46),"dry_steppe":Vector2(111,44),"desert_steppe":Vector2(108,43),
	"dune_sand":Vector2(83,39),"gravel_gobi":Vector2(65,43),"saline_meadow":Vector2(117,39),
	"alpine_meadow":Vector2(92,31),"alpine_steppe":Vector2(85,34),"tundra_moss":Vector2(125,69),
	"boreal_litter":Vector2(115,59),"temperate_litter":Vector2(119,40),"conifer_litter":Vector2(126,52),
	"subtropical_humus":Vector2(106,30),"tropical_moist_humus":Vector2(102,19),
	"dry_woodland_litter":Vector2(76,25),"savanna_red_soil":Vector2(77,17),"flood_meadow":Vector2(124,48),
	"alluvial_loam":Vector2(117,39),"weathered_rock":Vector2(117,41),"alpine_scree":Vector2(86,31)}

static func run(application) -> void:
	var qa=TerrainSurfaceQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String, details: Variant=null) -> void:
	checks.append({"name":name,"passed":value,"details":details})
	if not value:push_error("TERRAIN_SURFACE_QA: "+name)

func settle() -> void:
	for i in range(8):await app.get_tree().process_frame

func capture(name: String) -> void:
	await settle();var path=folder+"/"+name+".png"
	check(await app.capture_ui(path,name),"raw_native_capture:"+name)
	var row={"name":name,"path":path,"raw_godot_capture":true}
	if is_instance_valid(app.map_view):row["map_selection"]=app.map_view.map_bank_capture_facts()
	captures.append(row)

func target(family: String) -> Dictionary:
	var preferred: Vector2=PREFERRED.get(family,Vector2(105,36));var best=INF;var result: Dictionary={}
	for hex in app.map_view.presentation_cells:
		var key=HexGrid.key(hex);var id=str(app.map_view.map_details.surfaces.get(key,""))
		if not id.begins_with("tile_surface_"+family+"_"):continue
		var cell: Dictionary=app.map_view.presentation_cells[hex]
		if not StateAccess.at(app.match_controller.state,"units",hex).is_empty():continue
		var geo=Vector2(float(cell.lon_e6)/1000000.0,float(cell.lat_e6)/1000000.0)
		var distance=geo.distance_squared_to(preferred)
		if distance<best:best=distance;result={"hex":hex,"cell":cell,"id":id}
	return result

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--terrain-surface-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/terrain_surfaces_native"
	check(MapTerrainSurfaces.available(),"twenty_types_eighty_originals_available")
	var before_profile=ContentRegistry.fingerprint(app.profiles.profile)
	for section in range(3):
		app.war_room.show_terrain_atlas(section);await settle()
		var all_variants=true
		for node in app.ui_nodes(app.overlay):
			if not node.has_meta("terrain_surface"):continue
			var picture=node.find_child("TerrainMaterialPreview",true,false)
			var button=node.find_child("TerrainVariant",true,false)
			var first=picture.texture
			for variant in range(int(picture.get_meta("variant_count",4))):
				all_variants=all_variants and picture.texture!=null and int(picture.get_meta("variant",-1))==variant
				button.pressed.emit()
			all_variants=all_variants and picture.texture==first
		check(all_variants,"atlas_macro_and_four_detail_originals_are_reachable:"+str(section))
		var fits=true
		for node in app.ui_nodes(app.overlay):
			if node is ScrollContainer:
				for child in node.get_children():
					if child is Container and child.size.x>node.size.x+2:fits=false
		check(fits,"atlas_scroll_content_fits_viewport:"+str(section))
		await capture("atlas_"+str(section));app.close_overlay();await settle()
	app.settings.tutorial=false;app.start_game("asia_1927",app.content.scenarios.asia_1927.player_default);app.close_overlay();await settle()
	var original=ContentRegistry.fingerprint(app.match_controller.state.map)
	var state_before=ContentRegistry.fingerprint(app.match_controller.state)
	for family in MapTerrainSurfaces.data().types:
		var chosen=target(family)
		if chosen.is_empty() and family in ["boreal_litter","temperate_litter","conifer_litter","dry_woodland_litter"]:
			var eligible=0;var regional=0
			for cell in app.map_view.presentation_cells.values():
				if MapTerrainSurfaces.family_for(cell)!=family:continue
				regional+=1
				if TerrainVisuals.kind_for_cell(cell)=="forest":eligible+=1
			check(regional>0 and eligible==0,"forest_floor_withheld_without_dated_forest_source:"+family)
			withheld_forest_families.append(family);continue
		check(not chosen.is_empty(),"actual_source_material_is_deployed:"+family)
		if chosen.is_empty():continue
		app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode=""
		app.on_hex_selected(chosen.hex)
		app.map_view.zoom=1.25;app.map_view.focus_world(HexGrid.to_world(chosen.hex));await settle()
		var view=Rect2(app.map_view.camera-app.map_view.size/(2*app.map_view.zoom),app.map_view.size/app.map_view.zoom)
		var facts=app.map_view.terrain_surface_capture_facts(view)
		check(int(facts.visible_types.get(family,0))>0,"material_visible_in_real_map:"+family)
		check(facts.visible_macro_sources.has(MapTerrainSurfaces.macro_id(family)),"continuous_macro_visible_on_real_map:"+family)
		check(facts.same_original_on_adjacent_cells==0,"adjacent_originals_differ:"+family)
		await capture("map_"+family)
	check(ContentRegistry.fingerprint(app.match_controller.state.map)==original and ContentRegistry.fingerprint(app.match_controller.state)==state_before,"viewing_all_twenty_materials_does_not_change_game_or_map_state")
	check(ContentRegistry.fingerprint(app.profiles.profile)==before_profile,"atlas_does_not_mutate_growth_profile")
	var failures=checks.filter(func(c):return not c.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"captures":captures,"registered_library_types":20,"rendered_map_types":20-withheld_forest_families.size(),"withheld_without_dated_forest_source":withheld_forest_families,"build_version":ContentRegistry.APP_VERSION,"resolution":app.get_viewport_rect().size,"ui_scale":app.settings.ui_scale,"physical_android_device_tested":false,"formal_art_approval":false,"ew6_parity_claimed":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("TERRAIN_SURFACE_NATIVE ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"captures":captures.size(),"failures":failures}));app.get_tree().quit(0 if failures.is_empty() else 1)
