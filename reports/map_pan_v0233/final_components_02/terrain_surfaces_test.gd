extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"content_loads")
	verify(MapTerrainSurfaces.available(),"twenty_types_eighty_originals_installed")
	var observed: Dictionary={};var all_hashes: Dictionary={};var adjacent_pairs=0;var bad_pairs=0
	for family in MapTerrainSurfaces.data().get("types",{}):
		var pool=MapTerrainSurfaces.ids(family);var used: Dictionary={}
		verify(pool.size()==4,"four_independent_originals:"+family)
		for id in pool:
			var row: Dictionary=MapTerrainSurfaces.data().records[id]
			verify(FileAccess.file_exists("res://assets/tile/"+id+".png") and FileAccess.get_sha256("res://assets/tile/"+id+".png")==row.source_sha256,"immutable_engine_original:"+id)
			all_hashes[row.source_sha256]=true
		for q in range(-12,13):
			for r in range(-12,13):
				var h=Vector2i(q,r);var id=MapTerrainSurfaces.variant_for(family,h);used[id]=true
				for direction in HexGrid.DIRECTIONS:
					adjacent_pairs+=1
					if MapTerrainSurfaces.variant_for(family,h+direction)==id:bad_pairs+=1
		verify(used.size()==4,"all_four_sources_used_stably:"+family)
	verify(all_hashes.size()==80,"no_duplicate_original_bytes_counted")
	verify(adjacent_pairs>0 and bad_pairs==0,"no_same_original_on_any_of_six_adjacent_cells_across_negative_and_positive_coordinates")
	var geo=MapTerrainSurfaces.geography()
	verify(not geo.get("historical_landuse_survey",true) and not geo.get("water_polygons_added",true) and not geo.get("forest_boundaries_added",true),"ecoregions_do_not_claim_historical_forests_or_water")
	for map_id in geo.get("maps",{}):
		var map: Dictionary=content.maps[map_id];var original=ContentRegistry.fingerprint(map);var cells: Dictionary={}
		for cell in map.cells:cells[HexGrid.coordinate(cell.position)]=cell.duplicate(true)
		var diagnostics=MapTerrainSurfaces.apply(cells,map_id)
		verify(ContentRegistry.fingerprint(map)==original,"authoritative_map_unchanged:"+map_id)
		verify(diagnostics.active and not diagnostics.rule_maps_modified and not diagnostics.water_or_forest_added,"presentation_scope_only:"+map_id)
		var valid=true
		for hex in cells:
			var cell: Dictionary=cells[hex];var family=MapTerrainSurfaces.family_for(cell)
			if family.is_empty():continue
			observed[family]=true
			var row=geo.maps[map_id].get(cell.id,[])
			valid=valid and row.size()==3 and row[0]==family and geo.ecoregions.has(str(int(row[1])))
			valid=valid and cell.terrain_id not in ["sea","river","road","city","port","ford"]
			var occupied=cell.duplicate(true);occupied["owner_id"]="another_owner"
			valid=valid and MapArtBank.material_family(occupied)==MapTerrainSurfaces.draw_family(family,cell) and MapSurfaceRegions.material_label(cell)!=""
		verify(valid,"every_applied_material_is_sourced_and_independent_of_occupying_faction:"+map_id)
	verify(observed.size()==20,"all_twenty_types_exist_on_actual_maps")
	for family in ["temperate_litter","conifer_litter","boreal_litter","dry_woodland_litter"]:
		verify(MapTerrainSurfaces.draw_family(family,{"terrain_id":"plain"}) not in ["temperate_litter","conifer_litter","boreal_litter","dry_woodland_litter"],"potential_forest_does_not_paint_plain_as_fallen_leaves:"+family)
		verify(MapTerrainSurfaces.draw_family(family,{"terrain_id":"plain","presentation_terrain_id":"forest"})==family,"dated_visual_forest_can_retain_regional_ground:"+family)
	for feature in ["sea","river","road","city","port","ford"]:
		var cell={"terrain_id":feature,"presentation_terrain_surface":"dune_sand"}
		verify(MapTerrainSurfaces.family_for(cell).is_empty(),"feature_precedence:"+feature)
	verify(MapTerrainSurfaces.alpha_for("dune_sand",false)>.9 and MapDetails.SURFACE_BLEND_INNER>=.7,"visible_material_grain_and_continuous_feathered_coverage")
	verify(MapView.TERRITORY_FIELD_OPACITY<.3 and MapView.TERRITORY_OPACITY<.3,"political_wash_stays_separate_and_translucent")
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"actual_types":observed.size(),"adjacent_pairs":adjacent_pairs,"repeated_adjacent_sources":bad_pairs,"formal_art_approval":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_02/terrain_surfaces_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("TERRAIN_SURFACES_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
