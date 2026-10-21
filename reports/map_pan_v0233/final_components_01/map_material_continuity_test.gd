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
				var weight=Vector3(uvs[index].x,-uvs[index].y-GroundMaterialBlend.WEIGHT_MARKER,1.0-uvs[index].x+uvs[index].y+GroundMaterialBlend.WEIGHT_MARKER)
				phase_ok=phase_ok and weight.x>=-.0001 and weight.y>=-.0001 and weight.z>=-.0001 and absf(weight.x+weight.y+weight.z-1)<.0001;vertices_checked+=1
		else:
			fine_started=true
			for color in arrays[Mesh.ARRAY_COLOR]:details_ok=details_ok and color.a<=.22001;detail_vertices+=1
	verify(phase_ok and vertices_checked>100,"source_blend_weights_form_a_partition_for_positive_and_negative_hexes")
	verify(details_ok and detail_vertices>200,"fine_sources_remain_visible_without_overpowering_macro_ground")
	verify(ordering and fine_started,"all_continuous_ground_draws_before_fine_originals")
	var area=0.0;var bounded=true
	for batch in batches.batches:
		if batch.layer!="macro":continue
		var v: PackedVector3Array=batch.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for i in range(0,v.size(),3):
			var a=Vector2(v[i].x,v[i].y);var b=Vector2(v[i+1].x,v[i+1].y);var c=Vector2(v[i+2].x,v[i+2].y)
			area+=absf((b-a).cross(c-a))*.5
			var owner=HexGrid.from_world((a+b+c)/3.0)
			bounded=bounded and [a,b,c].all(func(p):return p.distance_to(HexGrid.to_world(owner))<=HexGrid.RADIUS+.001)
	verify(absf(area-entries.size()*3.0*sqrt(3.0)*pow(HexGrid.RADIUS,2)*.5)<.02,"continuous_mesh_area_equals_exact_hex_partition_without_overlapping_apertures")
	verify(bounded,"continuous_ground_stays_inside_the_reserved_source_land_footprint")
	var full=MapDetails.new();var patch: Array=[]
	for q in range(-2,3):
		for r in range(-2,3):
			var h=Vector2i(q,r);var family="temperate_meadow" if q<=0 else "dry_steppe"
			full.surfaces[HexGrid.key(h)]=MapTerrainSurfaces.variant_for(family,h);full.surface_families[HexGrid.key(h)]=family
			patch.append({"hex":h,"cell":{},"kind":"plain"})
	var whole=full.surface_meshes(patch,false,1900,true,false)
	verify(whole.batches.all(func(batch):return batch.layer=="macro" and batch.continuous),"overview_retains_continuous_geographic_materials_without_fine_cell_overlays")
	var coverage=true;var center_mix=true;var layer_ids=GroundMaterialBlend.source_layers()
	for batch in whole.batches:
		var arrays=batch.mesh.surface_get_arrays(0);var v: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var colors: PackedColorArray=arrays[Mesh.ARRAY_COLOR]
		for i in range(v.size()):
			var point=Vector2(v[i].x,v[i].y)
			if absf(point.x)<60 and absf(point.y)<45:coverage=coverage and absf(colors[i].a-1)<.0001
			if point.distance_to(HexGrid.to_world(Vector2i(0,0)))<.001:center_mix=center_mix and roundi(colors[i].r*255)==layer_ids.temperate_meadow
	verify(coverage,"interior_regions_have_constant_opacity_including_material_boundaries")
	verify(center_mix,"source_cell_centres_keep_their_registered_material_identity")
	var rerender=full.surface_meshes(patch.duplicate(),false,1900,true,false)
	verify(whole.batches.size()==rerender.batches.size() and whole.batches.all(func(batch):
		var i=whole.batches.find(batch);return batch.mesh.surface_get_arrays(0)==rerender.batches[i].mesh.surface_get_arrays(0)),"repeated_view_preparation_preserves_world_anchored_vertices_weights_and_source_ids")
	var all_chunks=full.continuous_macro_meshes(Rect2(-1000,-1000,2000,2000))
	var reused=full.continuous_macro_meshes(Rect2(-1000,-1000,2000,2000))
	verify(all_chunks.count==patch.size() and all_chunks.macro_materials==2,"continental_cache_covers_every_registered_cell_and_retains_both_source_types")
	verify(reused.chunks_created==0 and all_chunks.batches.map(func(batch):return batch.mesh.get_instance_id())==reused.batches.map(func(batch):return batch.mesh.get_instance_id()),"panning_and_selection_reuse_identical_ground_mesh_resources")
	var distant=full.continuous_macro_meshes(Rect2(10000,10000,50,50))
	verify(distant.batches.is_empty() and distant.chunks_created==0,"offscreen_chunk_bounds_cull_ground_without_rebuilding_it")
	var many=MapDetails.new()
	for q in range(-20,21):
		for r in range(-20,21):
			var h=Vector2i(q,r);many.surfaces[HexGrid.key(h)]=MapTerrainSurfaces.variant_for("temperate_meadow",h);many.surface_families[HexGrid.key(h)]="temperate_meadow"
	var nearby=Rect2(-160,-140,320,280);var selected=many.continuous_macro_meshes(nearby);var submitted: Dictionary={}
	for batch in selected.batches:
		var v: PackedVector3Array=batch.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for i in range(0,v.size(),3):
			var center=(v[i]+v[i+1]+v[i+2])/3.0;submitted[HexGrid.key(HexGrid.from_world(Vector2(center.x,center.y)))]=true
	var visible_preserved=true
	for key in many.surfaces:
		if nearby.has_point(HexGrid.to_world(HexGrid.from_key(key))):visible_preserved=visible_preserved and submitted.has(key)
	verify(visible_preserved and submitted.size()==selected.count and selected.count<1681 and selected.chunks_created<16,"wide_map_submission_preserves_visible_source_cells_without_drawing_the_entire_map")
	var previous=0.0;var widths_increase=true
	for order in range(1,11):
		var width=MapHydrography.symbolic_width(order,false)
		widths_increase=widths_increase and width>previous;previous=width
	verify(widths_increase,"river_order_has_strict_width_hierarchy")
	var source=PackedVector2Array([Vector2.ZERO,Vector2(18,0),Vector2(18,12),Vector2(43,12)])
	var fingerprint=source.duplicate();var rounded=MapHydrography.rounded_source_corners(source,2.4)
	verify(source==fingerprint and rounded[0]==source[0] and rounded[-1]==source[-1],"water_presentation_preserves_source_endpoints_and_original_geometry")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"macro_vertices_checked":vertices_checked,"formal_art_approval":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/final_components_01/map_material_continuity_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_MATERIAL_CONTINUITY_TEST ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
