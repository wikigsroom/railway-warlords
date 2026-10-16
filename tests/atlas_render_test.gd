extends SceneTree

var checks: Array=[]
var failures: Array=[]
var evidence: Array=[]

func _init() -> void:run.call_deferred()

func verify(condition: bool, name: String) -> void:
	checks.append({"name":name,"passed":condition})
	if not condition:failures.append(name);push_error(name)

func footprint_inside_source(rect: Rect2, shapes: Array) -> bool:
	var polygon=PackedVector2Array([rect.position,Vector2(rect.end.x,rect.position.y),rect.end,Vector2(rect.position.x,rect.end.y)])
	for shape in shapes:
		# Independent polygon difference, rather than repeating the placement point tests.
		if not Geometry2D.clip_polygons(polygon,shape.exterior).is_empty():continue
		var intersects_hole=false
		for hole in shape.holes:
			if not Geometry2D.intersect_polygons(polygon,hole).is_empty():intersects_hole=true;break
		if not intersects_hole:return true
	return false

func independent_path_index(lines: Array) -> Dictionary:
	# Independent whole-line bounds at a different bucket size from the
	# production per-segment index. Exact polygon intersection remains the
	# actual assertion; this only avoids millions of irrelevant native calls.
	var buckets: Dictionary={}
	for index in range(lines.size()):
		var line: PackedVector2Array=lines[index]
		if line.is_empty():continue
		var bounds=Rect2(line[0],Vector2.ZERO)
		for point in line:bounds=bounds.expand(point)
		for x in range(floori(bounds.position.x/320),floori(bounds.end.x/320)+1):
			for y in range(floori(bounds.position.y/320),floori(bounds.end.y/320)+1):
				var bucket=Vector2i(x,y)
				if not buckets.has(bucket):buckets[bucket]=[]
				buckets[bucket].append(index)
	return {"lines":lines,"buckets":buckets}

func source_paths_clear(area: Rect2, paths: Dictionary) -> bool:
	var selected: Dictionary={}
	for x in range(floori(area.position.x/320),floori(area.end.x/320)+1):
		for y in range(floori(area.position.y/320),floori(area.end.y/320)+1):
			for index in paths.buckets.get(Vector2i(x,y),[]):selected[index]=true
	var polygon=PackedVector2Array([area.position,Vector2(area.end.x,area.position.y),area.end,Vector2(area.position.x,area.end.y)])
	for index in selected:
		if not Geometry2D.intersect_polyline_with_polygon(paths.lines[index],polygon).is_empty():return false
	return true

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"content_loaded")
	if not content.errors.is_empty():quit(1);return
	var library=AssetLibrary.new()
	for map_id in ["jingjin","jingfeng","conquest_china","hankou","ningpu"]:
		var args=OS.get_cmdline_user_args()
		if "--map-id" in args and args[args.find("--map-id")+1]!=map_id:continue
		var recipe={}
		print("ATLAS_MAP_START ",map_id)
		for item in content.scenarios.values():
			if item.map_id==map_id:recipe=item;break
		var state=StateBuilder.create(content,recipe.id,recipe.player_default,{})
		var before=ContentRegistry.fingerprint(state)
		var view=MapView.new();view.size=Vector2(1200,760);view.setup(content,library);view.set_state(state)
		verify(before==ContentRegistry.fingerprint(state),map_id+"_render_preparation_keeps_authoritative_state_unchanged")
		verify(view.surface_diagnostics.errors.is_empty(),map_id+"_all_surveyed_land_and_island_rings_fill_without_triangulation_failure")
		var surface_arrays=view.land_surface.surface_get_arrays(0)
		var surface_vertices=surface_arrays[Mesh.ARRAY_VERTEX];var surface_indices=surface_arrays[Mesh.ARRAY_INDEX]
		var source_area=0.0;var rendered_area=0.0
		for shape in view.land_shapes:
			var points=shape.exterior;var origin=points[0]
			for i in range(1,points.size()-1):source_area+=(points[i]-origin).cross(points[i+1]-origin)*.5
		for i in range(0,surface_indices.size(),3):
			var a=surface_vertices[surface_indices[i]];var b=surface_vertices[surface_indices[i+1]];var c=surface_vertices[surface_indices[i+2]]
			rendered_area+=absf((b-a).cross(c-a).z)*.5
		verify(absf(rendered_area-absf(source_area))<=maxf(.01,absf(source_area)*.000001),map_id+"_filled_mesh_covers_the_entire_surveyed_polygon_area")
		var source_points: Dictionary={}
		for shape in view.land_shapes:
			for point in shape.exterior:source_points[point]=true
		var original_vertices=surface_vertices.size()>0
		for vertex in surface_vertices:original_vertices=original_vertices and source_points.has(Vector2(vertex.x,vertex.y))
		verify(original_vertices,map_id+"_surface_keeps_original_surveyed_vertices")
		var eligible=true;var dry=true;var finite_colors=true;var rivers_clear=true;var rail_clear=true
		var source_cells={}
		for cell in state.map.cells:source_cells[cell.id]=cell
		var river_paths=independent_path_index(view.river_lines+view.detail_river_lines.map(func(row):return row.points))
		var rail_paths=independent_path_index(view.relief.tracks)
		for feature in view.relief.features:
			var cell=source_cells[feature.cell_id]
			eligible=eligible and cell.natural_terrain_id in ["hill","mountain","peak"] and cell.elevation_m!=null and cell.relief_sample_m!=null and cell.region_id!="restricted"
			var feature_dry=footprint_inside_source(feature.footprint,view.land_shapes)
			if not feature_dry and dry:print("FOOTPRINT_DIAGNOSTIC ",JSON.stringify({"cell":cell.id,"at":feature.position,"footprint":feature.footprint,"center_dry":view.relief.dry_point(feature.position),"boundary_intersection":view.relief.intersects_index(feature.footprint,view.relief.boundary_buckets,0)}))
			dry=dry and feature_dry
			for kind in ["river","rail"]:
				var area:Rect2=feature.footprint.grow(9 if kind=="river" else 8)
				if not source_paths_clear(area,river_paths if kind=="river" else rail_paths):
					if kind=="river":rivers_clear=false
					else:rail_clear=false
		verify(eligible,map_id+"_scenery_only_on_sampled_hilly_ground")
		verify(dry,map_id+"_complete_sprite_rectangles_inside_source_land_and_outside_holes")
		verify(rivers_clear,map_id+"_relief_does_not_cover_source_river_strokes")
		verify(rail_clear,map_id+"_relief_does_not_cover_source_tracks")
		var features=ContentRegistry.fingerprint(view.relief.features)
		view.fit_map()
		var whole=Rect2(view.world_to_screen(view.world_bounds.position),view.world_bounds.size*view.zoom)
		verify(Rect2(Vector2.ZERO,view.size).encloses(whole),map_id+"_overview_contains_complete_map_extent")
		view.relief.build(state.map,view.land_shapes,view.river_lines,view.detail_river_lines.map(func(row):return row.points))
		verify(features==ContentRegistry.fingerprint(view.relief.features),map_id+"_placement_deterministic")
		if view.relief.mesh!=null:
			var arrays=view.relief.mesh.surface_get_arrays(0)
			for color in arrays[Mesh.ARRAY_COLOR]:finite_colors=finite_colors and is_finite(color.a) and color.a>=0 and color.a<=1
		verify(finite_colors,map_id+"_mesh_alpha_finite_and_bounded")
		evidence.append({"map_id":map_id,"cells":state.map.cells.size(),"surface":view.surface_diagnostics,"relief":view.relief.diagnostics,"features_fingerprint":ContentRegistry.fingerprint(view.relief.features)})
		if map_id=="conquest_china":
			view.camera=view.world_bounds.get_center()
			for scale in [1.0,1.2,1.5]:
				view.label_scale=scale;view.zoom=view.overview_zoom()
				var labels=view.city_label_layout(Rect2(view.camera-view.size/(2*view.zoom),view.size/view.zoom).grow(170))
				var no_overlap=true;var readable=true
				for i in range(labels.size()):
					readable=readable and labels[i].font_size*view.zoom>=18*scale
					for j in range(i+1,labels.size()):no_overlap=no_overlap and not labels[i].rect.intersects(labels[j].rect)
				verify(readable and labels.size()>=4,"atlas_font_floor_scale_"+str(scale))
				verify(no_overlap,"atlas_city_labels_do_not_overlap_scale_"+str(scale))
			view.label_scale=1.0;view.selected_city_id="beijing"
			view.camera=HexGrid.to_world(HexGrid.coordinate(StateAccess.find(state,"cities","beijing").position));view.clamp_camera()
			var selected_labels=view.city_label_layout(Rect2(view.camera-view.size/(2*view.zoom),view.size/view.zoom).grow(170))
			verify(selected_labels.any(func(label):return label.city_id=="beijing"),"selected_city_label_retained_in_dense_northern_cluster")
			var previous_mesh=view.relief.mesh;var previous_features=ContentRegistry.fingerprint(view.relief.features);var changed=state.duplicate()
			changed.date="1922-04-01" if view.administration_key=="1920" else "1920-08-01";view.set_state(changed)
			verify(view.relief.mesh==previous_mesh and ContentRegistry.fingerprint(view.relief.features)==previous_features,"administrative_year_change_reuses_surveyed_relief")
			verify(view.administration_key==ContentRegistry.administration_year(changed.date),"administrative_year_change_updates_boundaries_separately")
		view.free()
	var app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/atlas_%d"%Time.get_ticks_usec();root.add_child(app)
	await process_frame;app.settings.tutorial=false;app.start_game("campaign_1924_02","zhili");app.close_overlay();await process_frame
	verify(app.saves.root_path==app.qa_save_path and app.saves.root_path!="user://saves","native_qa_does_not_open_live_save_directory")
	var report={"passed":checks.size()-failures.size(),"failed":failures.size(),"checks":checks,"failures":failures,"maps":evidence,"content_hash":content.content_hash,"ruleset_version":ContentRegistry.RUNTIME_RULESET_VERSION,"physical_android_device_tested":false,"scope":"Source geography footprint, immutable state, atlas typography and QA save isolation; not all-assets visual or military-history approval."}
	var file=FileAccess.open("res://reports/atlas_render_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("ATLAS_RENDER_TESTS ",JSON.stringify({"passed":report.passed,"failed":report.failed,"maps":evidence}));quit(0 if failures.is_empty() else 1)
