extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func contains(vertices: PackedVector3Array, point: Vector2) -> bool:
	for i in range(0,vertices.size(),3):
		var a=Vector2(vertices[i].x,vertices[i].y);var b=Vector2(vertices[i+1].x,vertices[i+1].y);var c=Vector2(vertices[i+2].x,vertices[i+2].y)
		if absf((b-a).cross(c-a))<.00001:continue
		var ab=(b-a).cross(point-a);var bc=(c-b).cross(point-b);var ca=(a-c).cross(point-c)
		if (ab>=0 and bc>=0 and ca>=0) or (ab<=0 and bc<=0 and ca<=0):return true
	return false

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"content_loads_with_land_clipped_ownership")
	var map: Dictionary=content.maps.asia_strategic;var map_before=ContentRegistry.fingerprint(map)
	var row=MapControlLandClip.for_map(map)
	verify(not row.is_empty() and row.map_sha256==FileAccess.get_sha256("res://content/maps/asia_strategic.json"),"clip_vectors_are_bound_to_the_actual_source_map_bytes")
	verify(row.source_land_polygons==map.render_land.size() and row.source_land_holes==1,"all_source_islands_and_the_existing_lake_hole_are_retained")
	verify(row.city_zones.size()==map.cities.size() and row.clipped_city_zones==61,"all_81_city_influences_are_clipped_including_61_previous_water_overlaps")
	verify(row.full_field_cells+row.partial_field_cells+row.empty_field_cells==row.eligible_field_cells,"every_eligible_field_hex_has_full_partial_or_empty_source_geometry")
	verify(row.partial_field_cells>0 and row.empty_field_cells>0,"both_partial_shores_and_fully_off_land_candidate_hexes_are_handled")
	verify(MapControlLandClip.for_map({"id":"unsupported_map"}).is_empty(),"unsupported_geography_does_not_receive_an_unclipped_fallback")
	var zones=MapControlLandClip.city_zones(row);var again=MapControlLandClip.city_zones(row)
	verify(zones.size()==81 and zones.map(func(z):return z.mesh.get_instance_id())==again.map(func(z):return z.mesh.get_instance_id()),"actual_city_mesh_resources_are_reused_across_ownership_and_timeline_changes")
	var water_clear=true;var witnesses=0
	for witness in row.water_witnesses:
		var at=Vector2(witness.point[0],witness.point[1]);witnesses+=1
		for zone in zones:
			if zone.bounds.has_point(at) and contains(zone.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX],at):water_clear=false
	verify(witnesses>=150 and water_clear,"all_source_water_witnesses_are_outside_actual_city_mesh_triangles")
	var hole_clear=true;var retained_island_triangles=0;var classifier=AtlasRelief.new()
	var water_mesh=MapControlLandClip.inland_water_mesh(row,MapRiverSurface.TEXTURE_PERIOD)
	var water_vertices: PackedVector3Array=water_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var lake_does_not_hide_islands=true
	for source_shape in map.render_land:
		var exterior=PackedVector2Array();var holes: Array=[]
		for xy in source_shape.exterior:exterior.append(Vector2(xy[0],xy[1]))
		for raw in source_shape.holes:
			var points=PackedVector2Array()
			for xy in raw:points.append(Vector2(xy[0],xy[1]))
			holes.append(points)
		classifier.land.append({"exterior":exterior,"holes":holes})
		var bounds=Rect2(exterior[0],Vector2.ZERO)
		for at in exterior:bounds=bounds.expand(at)
		classifier.land_bounds.append(bounds)
	for shape in map.render_land:
		for raw in shape.holes:
			var hole=PackedVector2Array()
			for xy in raw:hole.append(Vector2(xy[0],xy[1]))
			for zone in zones:
				var vertices: PackedVector3Array=zone.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
				for i in range(0,vertices.size(),3):
					var center=(vertices[i]+vertices[i+1]+vertices[i+2])/3
					var at=Vector2(center.x,center.y)
					if Geometry2D.is_point_in_polygon(at,hole):
						if classifier.dry_point(at):
							retained_island_triangles+=1
							if contains(water_vertices,at):lake_does_not_hide_islands=false
						else:hole_clear=false
	verify(hole_clear and retained_island_triangles>0,"source_lake_water_remains_unpainted_and_actual_lake_islands_remain_land")
	verify(lake_does_not_hide_islands,"actual_lake_water_mesh_excludes_separately_sourced_lake_islands")
	verify(water_mesh==MapControlLandClip.inland_water_mesh(row,MapRiverSurface.TEXTURE_PERIOD),"actual_lake_mesh_is_cached_with_the_shared_water_uv_period")
	var uv: PackedVector2Array=water_mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV];var uv_correct=uv.size()==water_vertices.size()
	for i in range(uv.size()):uv_correct=uv_correct and uv[i].distance_to(Vector2(water_vertices[i].x,water_vertices[i].y)/MapRiverSurface.TEXTURE_PERIOD)<.00001
	verify(uv_correct,"actual_lake_water_mesh_uses_the_same_world_uv_phase_as_rivers_and_seas")
	var view=MapView.new();var field_water_clear=true
	for id in ["asia_1840","asia_1860","asia_1890","asia_1900","asia_1917","asia_1927","asia_1940"]:
		var state=StateBuilder.create(content,id,content.scenarios[id].player_default,{})
		var before=ContentRegistry.fingerprint(state)
		view.state=state;view.places.prepare(state.map,state.date);view.places.update_owners(state);view.territory_field_signature="";view.prepare_territory_field()
		verify(view.territory_field_diagnostics.get("land_clipped",false) and not view.territory_field_meshes.is_empty(),"source_clipped_field_is_used_for_timeline:"+id)
		verify(view.places.zones.all(func(z):return z.get("land_clipped",false)),"source_clipped_city_influences_are_used_for_timeline:"+id)
		verify(view.places.owners.size()==state.cities.size() and state.cities.all(func(city):return view.places.owners.get(city.id,"")==city.owner_id),"current_timeline_owners_are_preserved:"+id)
		verify(ContentRegistry.fingerprint(state)==before,"display_preparation_preserves_rules_geography_economy_random_and_owner_state:"+id)
		if id=="asia_1840":
			for witness in row.water_witnesses:
				var at=Vector2(witness.point[0],witness.point[1])
				for owner in view.territory_field_meshes:
					if contains(view.territory_field_meshes[owner].surface_get_arrays(0)[Mesh.ARRAY_VERTEX],at):field_water_clear=false
	verify(field_water_clear,"source_water_witnesses_are_outside_the_actual_combined_field_meshes")
	var changed=view.state.duplicate(true);var source_mesh_ids=view.places.zones.map(func(z):return z.mesh.get_instance_id())
	var old_signature=view.territory_field_signature;var other=str(changed.turn_order[1])
	changed.cities[0].owner_id=other if other!=changed.cities[0].owner_id else str(changed.turn_order[0])
	view.state=changed;view.places.update_owners(changed);view.prepare_territory_field()
	verify(view.territory_field_signature!=old_signature and view.places.owners[changed.cities[0].id]==changed.cities[0].owner_id,"changed_city_owner_rebuilds_field_colors_from_the_new_state")
	verify(view.places.zones.map(func(z):return z.mesh.get_instance_id())==source_mesh_ids,"changed_city_owner_preserves_the_actual_clipped_city_meshes")
	verify(ContentRegistry.fingerprint(map)==map_before,"all_timeline_and_owner_checks_leave_the_published_source_map_immutable")
	verify(HexGrid.RADIUS==48 and MapView.TERRITORY_OPACITY==.26 and MapView.TERRITORY_FIELD_OPACITY==.21,"base_hex_size_and_translucent_ownership_opacities_are_preserved")
	view.free()
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,
		"content_hash":content.content_hash,"source_map_sha256":row.map_sha256,"presentation_data_sha256":FileAccess.get_sha256(MapControlLandClip.PATH),
		"timelines_checked":7,"water_witnesses_checked":witnesses,"source_maps_modified":false,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/control_land_clip_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CONTROL_LAND_CLIP_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
