extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	verify(MapTerrainSurfaces.available(),"existing_twenty_types_eighty_details_retained")
	var macros=MapTerrainSurfaces.macro_data();var hashes: Dictionary={}
	verify(macros.get("records",{}).size()==20,"one_continuous_ground_for_each_type")
	for family in MapTerrainSurfaces.data().types:
		var id=MapTerrainSurfaces.macro_id(family)
		var path="res://assets/tile/"+id+".png"
		verify(FileAccess.file_exists(path) and FileAccess.get_sha256(path)==macros.records[family].source_sha256,"immutable_continuous_original:"+family)
		hashes[macros.records[family].source_sha256]=true
	verify(hashes.size()==20,"twenty_distinct_new_original_hashes")
	var details=MapDetails.new();var entries: Array=[]
	for h in [Vector2i(-2,-1),Vector2i(-1,-1),Vector2i(0,-1),Vector2i(1,-1),Vector2i(1,0)]:
		var cell={"terrain_id":"plain","presentation_terrain_surface":"temperate_meadow"}
		details.surfaces[HexGrid.key(h)]=MapTerrainSurfaces.variant_for("temperate_meadow",h)
		details.surface_families[HexGrid.key(h)]="temperate_meadow"
		entries.append({"hex":h,"cell":cell,"kind":"plain"})
	var batches=details.surface_meshes(entries,false)
	verify(batches.count==entries.size() and batches.macro_materials==1,"adjacent_hexes_share_one_continuous_material_batch")
	var phase_ok=true;var details_ok=true;var vertices_checked=0;var detail_vertices=0;var fine_started=false;var ordering=true
	for batch in batches.batches:
		var arrays=batch.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var uvs: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV]
		if batch.layer=="macro":
			ordering=ordering and not fine_started
			for index in range(vertices.size()):
				var world=Vector2(vertices[index].x,vertices[index].y)
				phase_ok=phase_ok and uvs[index].is_equal_approx(world/384.0);vertices_checked+=1
		else:
			fine_started=true
			for color in arrays[Mesh.ARRAY_COLOR]:details_ok=details_ok and color.a<=.22001;detail_vertices+=1
	verify(phase_ok and vertices_checked>200,"drawn_mesh_uvs_share_world_phase_across_positive_and_negative_hexes")
	verify(details_ok and detail_vertices>200,"fine_sources_remain_visible_without_overpowering_macro_ground")
	verify(ordering and fine_started,"all_continuous_ground_draws_before_fine_originals")
	var previous=0.0;var widths_increase=true
	for order in range(1,11):
		var width=MapHydrography.symbolic_width(order,false)
		widths_increase=widths_increase and width>previous;previous=width
	verify(widths_increase,"river_order_has_strict_width_hierarchy")
	var source=PackedVector2Array([Vector2.ZERO,Vector2(18,0),Vector2(18,12),Vector2(43,12)])
	var fingerprint=source.duplicate();var rounded=MapHydrography.rounded_source_corners(source,2.4)
	verify(source==fingerprint and rounded[0]==source[0] and rounded[-1]==source[-1],"water_presentation_preserves_source_endpoints_and_original_geometry")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"macro_vertices_checked":vertices_checked,"formal_art_approval":false}
	var file=FileAccess.open("res://reports/map_material_continuity_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_MATERIAL_CONTINUITY_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
