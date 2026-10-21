extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func run() -> void:
	var details=MapDetails.new();var buckets: Dictionary={};var entries: Array=[];var keys: Array=[]
	for x in [-2,-1,0,1]:
		var key=Vector2i(x,0);keys.append(key);buckets[key]=[]
		for i in 6:
			var h=Vector2i(x*16+i,-i);var family=["temperate_meadow","dry_steppe","weathered_rock"][i%3]
			var row={"hex":h,"cell":{"terrain_id":"plain"},"kind":"plain"}
			buckets[key].append(row);entries.append(row)
			details.surfaces[HexGrid.key(h)]=MapTerrainSurfaces.variant_for(family,h)
			details.surface_families[HexGrid.key(h)]=family
	var before=ContentRegistry.fingerprint(entries)
	for strategic in [false,true]:
		var direct=details.surface_meshes(entries,strategic,entries.size(),true,true,false)
		var cached=details.cached_fine_surface_meshes(keys,buckets,strategic)
		var actual: Dictionary={};var exact=true;var order: Array=[]
		for batch in cached.batches:
			if not actual.has(batch.asset_id):actual[batch.asset_id]=[PackedVector3Array(),PackedColorArray(),PackedVector2Array()]
			var arrays=batch.mesh.surface_get_arrays(0)
			actual[batch.asset_id][0].append_array(arrays[Mesh.ARRAY_VERTEX]);actual[batch.asset_id][1].append_array(arrays[Mesh.ARRAY_COLOR]);actual[batch.asset_id][2].append_array(arrays[Mesh.ARRAY_TEX_UV])
			order.append(batch.asset_id)
		for batch in direct.batches:
			var arrays=batch.mesh.surface_get_arrays(0);var row: Array=actual.get(batch.asset_id,[])
			exact=exact and row.size()==3 and row[0]==arrays[Mesh.ARRAY_VERTEX] and row[1]==arrays[Mesh.ARRAY_COLOR] and row[2]==arrays[Mesh.ARRAY_TEX_UV]
		verify(exact and cached.count==direct.count and direct.count==24,"bucket_geometry_colors_and_uvs_equal_previous_full_mesh_"+str(strategic))
		var sorted=order.duplicate();sorted.sort()
		verify(order==sorted,"cross_bucket_source_texture_blend_order_is_unchanged_"+str(strategic))
		var second=details.cached_fine_surface_meshes(keys,buckets,strategic)
		verify(second.created_chunks==0 and second.batches.map(func(row):return row.mesh)==cached.batches.map(func(row):return row.mesh),"camera_rebuild_reuses_the_same_gpu_resources_"+str(strategic))
	verify(ContentRegistry.fingerprint(entries)==before,"cache_never_changes_geographic_cells_or_material_assignments")
	var many_keys: Array=[]
	for i in 132:
		var key=Vector2i(i+20,5);many_keys.append(key);buckets[key]=[]
	details.cached_fine_surface_meshes(many_keys,buckets,false)
	verify(details.fine_chunk_meshes.size()==MapDetails.FINE_CHUNK_CACHE_LIMIT,"cache_memory_bound_is_enforced_for_a_large_view")
	var kept=details.fine_chunk_meshes.keys();var second=details.cached_fine_surface_meshes(many_keys,buckets,false)
	verify(second.created_chunks==132-MapDetails.FINE_CHUNK_CACHE_LIMIT and details.fine_chunk_meshes.keys()==kept,"oversized_view_preserves_its_cached_working_set_instead_of_thrashing_all_chunks")
	details.build({},{},AtlasRelief.new(),[],[])
	verify(details.fine_chunk_meshes.is_empty() and details.fine_chunk_order.is_empty(),"loading_another_map_clears_all_old_detail_chunks")
	var result={"passed":failures.is_empty(),"checks":checks,"failures":failures,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/fine_cache_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"\t"));file.close()
	print("FINE_CACHE_CHECKS ",checks.size()," passed=",failures.is_empty());quit(0 if failures.is_empty() else 1)
