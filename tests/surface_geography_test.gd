extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"content_loads_with_source_material_layer")
	var source=MapSurfaceRegions.data()
	verify(source.get("source_id","")=="resolve_ecoregions_2017" and int(source.get("source_year",0))==2017 and source.get("license","")=="CC-BY 4.0","ecoregion_source_identity_date_and_license_are_explicit")
	verify(not source.get("authored_rule_maps_modified",true) and not source.get("historical_wetland_extent_claimed",true) and not source.get("water_polygons_added",true) and not source.get("forest_boundaries_added",true),"potential_regions_are_not_misrepresented_as_historical_landuse_water_or_forest")
	var scope=str(source.get("scope",""))
	verify(scope.contains("not dated land use") and scope.contains("historical wetland"),"regional_material_precision_limit_is_preserved_in_runtime_metadata")
	verify(source.ecoregions.get("843",{}).get("name","")=="Taklimakan desert" and source.ecoregions.get("742",{}).get("name","")=="Bohai Sea saline meadow" and source.ecoregions.get("684",{}).get("name","").begins_with("Tarim Basin"),"desert_coastal_meadow_and_tarim_valley_have_separate_named_source_regions")
	var assignments_valid=true;var routed_features_unchanged=true;var real_examples: Dictionary={}
	for map_id in source.get("maps",{}):
		var original: Dictionary=content.maps[map_id]
		var before=ContentRegistry.fingerprint(original);var copies: Dictionary={}
		for cell in original.cells:copies[HexGrid.coordinate(cell.position)]=cell.duplicate(true)
		var terrain_before: Dictionary={}
		for hex in copies:terrain_before[hex]=copies[hex].get("terrain_id","")
		var diagnostics=MapSurfaceRegions.apply(copies,map_id)
		verify(ContentRegistry.fingerprint(original)==before,"rule_map_remains_immutable:"+map_id)
		verify(not diagnostics.historical_landuse_survey and not diagnostics.water_or_forest_added,"source_application_scope_remains_presentation_only:"+map_id)
		for hex in copies:
			var cell: Dictionary=copies[hex]
			routed_features_unchanged=routed_features_unchanged and cell.get("terrain_id","")==terrain_before[hex]
			if not cell.has("presentation_surface_family"):continue
			var record=source.maps[map_id].get(cell.id,[])
			assignments_valid=assignments_valid and record.size()==2 and str(record[0])==cell.presentation_surface_family and source.ecoregions.has(str(int(record[1])))
			var region=int(record[1]);var family=str(record[0])
			if map_id=="asia_strategic":real_examples[str(region)]=family
	verify(assignments_valid,"every_applied_material_has_an_archived_source_region_id")
	verify(routed_features_unchanged,"all_terrain_classes_roads_and_river_rules_are_unchanged")
	verify(real_examples.get("843","")=="sandy_ground" and real_examples.get("824","")=="arid_gravel" and real_examples.get("684","")=="alluvial_soil","actual_asia_cells_distinguish_sandy_desert_gobi_gravel_and_tarim_valley")
	var test_cells={Vector2i.ZERO:{"id":"arbitrary","terrain_id":"river","natural_terrain_id":"plain"}}
	var protected=ContentRegistry.fingerprint(test_cells);MapSurfaceRegions.apply(test_cells,"asia_strategic")
	verify(ContentRegistry.fingerprint(test_cells)==protected,"unmatched_or_river_cells_cannot_gain_an_invented_surface_region")
	var hydro=MapHydrography.source("hydrography_fine")
	verify(hydro.get("source_id","")=="hydrorivers_v10_as" and hydro.get("source_sha256","").length()==64,"fine_river_layer_identifies_its_archived_original")
	verify(hydro.get("no_invented_connections",false) and hydro.get("no_invented_historical_names",false) and hydro.get("width_is_symbolic",false) and hydro.get("flat_lowland_branches_excluded",false),"fine_river_precision_and_historical_limits_are_preserved")
	var fine_rows_valid=true;var fine_total=0
	for map_id in hydro.get("maps",{}):
		var map: Dictionary=content.maps[map_id];var before=ContentRegistry.fingerprint(map)
		var layers=MapHydrography.build(map,map_id)
		verify(before==ContentRegistry.fingerprint(map) and not layers.diagnostics.rule_geometry_modified,"fine_water_display_leaves_authoritative_map_and_crossings_unchanged:"+map_id)
		verify(layers.major.size()==layers.major_orders.size(),"source_main_reach_order_stays_aligned_with_its_geometry:"+map_id)
		for row in layers.detail:
			if int(row.get("source_reach_id",0))<=0:continue
			fine_total+=1
			fine_rows_valid=fine_rows_valid and row.source_name.is_empty() and row.stream_order>=1 and row.stream_order<=4 and row.width_symbolic
	verify(fine_rows_valid and fine_total>0,"source_tributaries_retain_real_reach_ids_and_order_without_fabricated_names")
	var headwater={"bounds":Rect2(10,20,60,60),"points":PackedVector2Array([Vector2(10,20),Vector2(70,80)]),"min_zoom":.8,"rank":10}
	var viewport=Rect2(0,0,200,200)
	verify(not MapHydrography.visible(headwater,viewport,.6,false) and MapHydrography.visible(headwater,viewport,1.05,false) and not MapHydrography.visible(headwater,Rect2(800,800,100,100),1.05,false),"small_source_reaches_appear_only_at_detail_zoom_and_in_the_actual_view")
	var long_reach=headwater.duplicate();long_reach.bounds=Rect2(400,400,800,800)
	var indexed=MapHydrography.spatial_index([headwater,long_reach])
	verify(MapHydrography.visible_rows([headwater,long_reach],indexed,Rect2(0,0,1400,1400),1.05,false).size()==2 and MapHydrography.visible_rows([headwater,long_reach],indexed,Rect2(4000,4000,200,200),1.05,false).is_empty(),"water_spatial_index_draws_each_source_once_and_culls_distant_chunks")
	var source_join=PackedVector2Array([Vector2(0,0),Vector2(0,60),Vector2(60,60),Vector2(60,120)])
	var original_join=source_join.duplicate();var rounded=MapHydrography.rounded_source_corners(source_join,5.76)
	var bounded=true
	for point in rounded:
		var distance=INF
		for index in range(source_join.size()-1):distance=minf(distance,point.distance_to(Geometry2D.get_closest_point_to_segment(point,source_join[index],source_join[index+1])))
		bounded=bounded and distance<=2.88+.00001
	verify(bounded and source_join==original_join and rounded[0]==source_join[0] and rounded[rounded.size()-1]==source_join[source_join.size()-1],"cartographic_corner_rounding_preserves_raw_geometry_and_endpoints_within_60_metres_at_1km_grid")
	var continental=MapHydrography.build(content.maps.asia_strategic,"asia_strategic")
	verify(continental.diagnostics.source_fine_reaches==0 and continental.major.size()==content.maps.asia_strategic.render_rivers.size(),"continental_overview_keeps_existing_primary_geometry_without_claiming_tactical_creeks")
	var hankou=MapHydrography.build(content.maps.hankou,"hankou")
	verify(hankou.diagnostics.major_presentation_replacements>0 and hankou.major_orders.all(func(order):return order>=6),"small_yangtze_map_uses_source_main_order_instead_of_line_length_as_width")
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"scope":"Source identity, preserved precision limits, actual map region application and authoritative state isolation; full raw-vector geometry audited separately."}
	var file=FileAccess.open("res://reports/surface_geography_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("SURFACE_GEOGRAPHY_TEST ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
