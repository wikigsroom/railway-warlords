extends SceneTree

var checks: Array=[]
var failures: Array=[]
var summaries: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var index=MapGroundCoverage.data()
	verify(index.get("maps",{}).size()==6,"six_source_maps_have_independent_numerical_catalogues")
	verify(index.get("numerical_vectors_only",false) and not index.get("source_rasters_modified",true),"coverage_has_no_generated_or_edited_raster")
	verify(FileAccess.get_sha256("res://presentation/data/terrain_surface_regions.json")==index.get("source_geography_sha256",""),"registered_ecological_geography_retains_original_bytes")
	for id in index.get("maps",{}):
		var source_path="res://content/maps/"+str(id)+".json"
		var source=JSON.parse_string(FileAccess.get_file_as_string(source_path))
		var original_hash=FileAccess.get_sha256(source_path)
		var row=MapGroundCoverage.for_map(source)
		verify(not row.is_empty() and row.get("map_sha256")==original_hash,"ground_is_bound_to_current_immutable_map:"+id)
		var details=MapDetails.new();details.source_ground_coverage=row
		details.ground_families=row.get("families",{});details.ground_clips=row.get("clips",{})
		var functional=0;var inherited=0;var clipped=0;var samples_ok=true;var alpha_ok=true;var land_area=0.0
		for key in row.get("supplements",{}):
			var evidence: Dictionary=row.supplements[key]
			if evidence.get("rule_terrain","") in ["city","road","port","ford","river"]:functional+=1
			if evidence.get("source_gate","")=="one_neighbour_pigment_interpolation":
				inherited+=1;samples_ok=samples_ok and float(evidence.distance_world)<=sqrt(3)*48+.0001 and evidence.ecoregion_id==null
		verify(samples_ok,"unsupported_ecology_is_only_bounded_neighbour_pigment_interpolation:"+id)
		verify(functional>0,"functional_cells_receive_independent_ground_without_reclassification:"+id)
		# Every clipped vertex traverses the shipping mesh builder. In particular,
		# city/shore cells have no fine-detail surface assignment to depend on.
		for key in row.get("clips",{}):
			var group={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
			details.append_continuous_ground(group,HexGrid.from_key(key),row.families[key])
			clipped+=1
			samples_ok=samples_ok and group.vertices.size()==row.clips[key].size() and group.vertices.size()%3==0
			for color in group.colors:alpha_ok=alpha_ok and absf(color.a-1.0)<.00001
			for i in range(0,group.vertices.size(),3):
				var a=group.vertices[i];var b=group.vertices[i+1];var c=group.vertices[i+2]
				land_area+=absf(Vector2(b.x-a.x,b.y-a.y).cross(Vector2(c.x-a.x,c.y-a.y)))*.5
		verify(samples_ok and clipped==int(row.partial_cells),"all_source_clipped_vertices_reach_runtime_mesh:"+id)
		verify(alpha_ok,"source_shore_partition_has_constant_opacity:"+id)
		var full_area=(int(row.covered_cells)-clipped)*3.0*sqrt(3)*pow(48,2)*.5
		verify(absf(land_area+full_area-float(row.ground_area))<maxf(2.0,float(row.ground_area)*.000001),"runtime_ground_area_matches_compiled_source_partition:"+id)
		verify(FileAccess.get_sha256(source_path)==original_hash,"rules_coasts_rivers_cities_and_dem_are_unchanged:"+id)
		summaries.append({"map":id,"covered_cells":row.covered_cells,"partial_cells":clipped,"functional_underlays":functional,"pigment_interpolations":inherited,"unclassified_cells":row.unclassified_cells})
		await process_frame
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"maps":summaries,"source_map_modified":false,"art_approval":false,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_01/ground_coverage_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_COVERAGE_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if report.passed else 1)
