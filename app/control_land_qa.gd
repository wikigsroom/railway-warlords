class_name ControlLandQA
extends RefCounted

# Ordinary native renderer and unmodified Asia scenario. Images are complete
# viewports; independently sourced water witnesses check actual rendered pixels.
var app
var checks: Array=[]
var captures: Array=[]
var cases: Array=[]
var folder=""
var label_leaders: Array=[]

static func run(application) -> void:
	var qa=ControlLandQA.new();qa.app=application;await qa.execute()

func check(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:push_error("CONTROL_LAND_QA: "+name)

func settle() -> void:
	for i in range(10):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw

func obstacles() -> Array:
	var view: MapView=app.map_view;var result: Array=[]
	for control in view.label_obstacle_controls:
		if is_instance_valid(control) and control.is_visible_in_tree():result.append(control.get_global_rect().grow(10))
	for row in view.capture_labels():
		var box=row.screen_rect;result.append(Rect2(view.global_position+Vector2(box[0],box[1]),Vector2(box[2],box[3])).grow(6))
	# Relocated city labels draw real leader strokes outside their label boxes.
	# Record the actual rendered segments; they are annotations over water, not
	# political fill pixels, and must be excluded in both toggle frames.
	for label in view.foreground_view.drawn_labels:
		if not label.shifted:continue
		label_leaders.append([view.world_to_screen(label.position)+view.global_position,
			view.world_to_screen(label.rect.get_center())+view.global_position])
	for box in [view.control_legend_rect(view.control_legend_ids()),view.terrain_legend_rect()]:
		if box.has_area():result.append(Rect2(box.position+view.global_position,box.size).grow(8))
	return result

func occluded(point: Vector2, blocked: Array) -> bool:
	if blocked.any(func(rect):return rect.has_point(point)):return true
	return label_leaders.any(func(segment):return point.distance_to(Geometry2D.get_closest_point_to_segment(point,segment[0],segment[1]))<=4.0)

func capture(name: String) -> Image:
	var path=folder+"/"+name+".png"
	check(await app.capture_ui(path,"source_land_control_"+name),"raw_native_capture:"+name)
	var metadata_path=path.get_basename()+".json"
	var meta=JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
	meta["control_land_clip"]=app.map_view.places.control_clip_diagnostics
	meta["territory_field"]=app.map_view.territory_field_diagnostics
	meta["control_enabled"]=app.map_view.show_control;meta["camera"]=[app.map_view.camera.x,app.map_view.camera.y];meta["zoom"]=app.map_view.zoom
	meta["scenario_id"]=app.match_controller.state.scenario_id
	var file=FileAccess.open(metadata_path,FileAccess.WRITE);file.store_string(JSON.stringify(meta,"\t"));file.close()
	captures.append({"path":path,"metadata":metadata_path,"control_enabled":app.map_view.show_control})
	return app.get_viewport().get_texture().get_image()

func delta(a: Image, b: Image, pixel: Vector2i) -> float:
	var first=a.get_pixelv(pixel);var second=b.get_pixelv(pixel)
	return maxf(absf(first.r-second.r),maxf(absf(first.g-second.g),absf(first.b-second.b)))*255

func compare(natural: Image, controlled: Image, blocked: Array, id: String, source: Dictionary) -> void:
	var view: MapView=app.map_view;var clear=view.get_global_rect().grow(-14)
	var used: Dictionary={};var count=0;var maximum=0.0;var records: Array=[]
	for witness in source.water_witnesses:
		if float(witness.source_land_clearance)*view.zoom<7:continue
		var center=view.world_to_screen(Vector2(witness.point[0],witness.point[1]))+view.global_position
		for dx in [-2,0,2]:
			for dy in [-2,0,2]:
				var pixel=Vector2i(center+Vector2(dx,dy))
				if used.has(pixel) or not clear.has_point(Vector2(pixel)) or occluded(Vector2(pixel),blocked):continue
				used[pixel]=true;var difference=delta(natural,controlled,pixel);maximum=maxf(maximum,difference);count+=1
				if records.size()<100:records.append({"city_id":witness.city_id,"pixel":[pixel.x,pixel.y],"world":witness.point,"max_channel_delta":difference})
	check(count>=9,"source_water_pixels_are_visible_and_sampled:"+id)
	check(maximum<=2.0,"control_toggle_does_not_recolor_source_water_pixels:"+id)
	var land_changed=0
	for zone in view.places.zones:
		var vertices: PackedVector3Array=zone.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		for i in range(0,vertices.size(),3):
			var center=(vertices[i]+vertices[i+1]+vertices[i+2])/3
			var screen=view.world_to_screen(Vector2(center.x,center.y))+view.global_position
			if not clear.has_point(screen) or occluded(screen,blocked):continue
			if delta(natural,controlled,Vector2i(screen))>2:land_changed+=1
			if land_changed>=24:break
		if land_changed>=24:break
	check(land_changed>=3,"land_ownership_wash_still_changes_actual_pixels:"+id)
	check(view.backdrop_view.city_control_fill_draw_count==0 and view.backdrop_view.territory_field_fill_draw_count>0,"shipping_continental_renderer_uses_one_control_coverage_layer:"+id)
	var minimap_count=0;var minimap_maximum=0.0;var mini=view.minimap
	var factor=minf((mini.size.x-16)/mini.extent.x,(mini.size.y-16)/mini.extent.y)
	var mini_clear=mini.get_global_rect().grow(-9);var mini_used: Dictionary={}
	for witness in source.water_witnesses:
		if float(witness.source_land_clearance)*factor<3:continue
		var pixel=Vector2i(mini.global_position+Vector2(8,8)+Vector2(witness.point[0],witness.point[1])*factor)
		if mini_used.has(pixel) or not mini_clear.has_point(Vector2(pixel)):continue
		mini_used[pixel]=true;minimap_count+=1;minimap_maximum=maxf(minimap_maximum,delta(natural,controlled,pixel))
	check(minimap_count>=12,"minimap_source_water_is_sampled:"+id)
	check(minimap_maximum<=2.0,"minimap_control_toggle_does_not_recolor_source_water:"+id)
	cases.append({"id":id,"water_pixels":count,"water_max_channel_delta":maximum,"land_changed_samples":land_changed,
		"minimap_water_pixels":minimap_count,"minimap_water_max_channel_delta":minimap_maximum,"water_samples":records,
		"city_influence_fill_draws":view.backdrop_view.city_control_fill_draw_count,"field_fill_batches":view.backdrop_view.territory_field_fill_draw_count,
		"continuous_ground_shader_active":view.backdrop_view.material!=null,
		"rendered_label_leaders":label_leaders.map(func(segment):return [[segment[0].x,segment[0].y],[segment[1].x,segment[1].y]])})

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--control-land-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/screenshots/control_land_native"
	app.settings.tutorial=false;app.start_game("asia_1840",app.content.scenarios.asia_1840.player_default);app.close_overlay();await settle()
	app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.pending={};app.order_mode="";app.refresh_battle();await settle()
	var view: MapView=app.map_view;var source=MapControlLandClip.for_map(view.state.map)
	check(not source.is_empty() and view.territory_field_diagnostics.get("land_clipped",false),"shipping_map_uses_source_bound_land_clipping")
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	for id in ["tianjin","osaka","baku","singapore","overview"]:
		label_leaders=[]
		if id=="overview":view.fit_map()
		else:
			var city=StateAccess.find(view.state,"cities",id);view.zoom=.66;view.focus_world(HexGrid.to_world(HexGrid.coordinate(city.position)))
		view.show_control=false;view.queue_redraw();view.minimap.queue_redraw();await settle()
		var natural=await capture(id+"_natural");var blocked=obstacles()
		view.show_control=true;view.queue_redraw();view.minimap.queue_redraw();await settle()
		var controlled=await capture(id+"_control");blocked.append_array(obstacles())
		compare(natural,controlled,blocked,id,source)
	check(ContentRegistry.fingerprint(app.match_controller.state)==before,"native_camera_and_control_toggles_preserve_all_rules_and_random_state")
	var failures=checks.filter(func(row):return not row.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"cases":cases,"captures":captures,
		"build_version":ContentRegistry.APP_VERSION,"content_hash":app.content.content_hash,"resolution":app.get_viewport_rect().size,
		"source_map_sha256":source.map_sha256,"clip_data_sha256":FileAccess.get_sha256(MapControlLandClip.PATH),
		"normal_shipping_renderer":not app.territory_qa_mode,"qa_save_isolated":not app.qa_save_path.is_empty(),
		"source_water_witnesses":source.water_witnesses.size(),"physical_android_device_tested":false,"ew6_parity_claimed":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CONTROL_LAND_NATIVE ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"cases":cases.map(func(row):return {"id":row.id,"water_pixels":row.water_pixels,"max_delta":row.water_max_channel_delta,"minimap_pixels":row.minimap_water_pixels,"minimap_max_delta":row.minimap_water_max_channel_delta}),"failures":failures}));app.get_tree().quit(0 if failures.is_empty() else 1)
