class_name WaterContinuityQA
extends RefCounted

# An opt-in native GPU fixture, explicitly separate from gameplay screenshots.
# It exercises the shipping shader/mesh helpers and the three imported sources.
class Fixture extends Node2D:
	var dimensions=Vector2(384,256)
	var pan=Vector2.ZERO
	var magnification=1.0
	var source: Texture2D
	var partitioned=false
	var meshes: Array=[]
	func _draw() -> void:
		draw_set_transform(dimensions*.5-pan*magnification,0,Vector2.ONE*magnification)
		var rect=Rect2(pan-dimensions*.5/magnification,dimensions/magnification).grow(8)
		meshes=[]
		if partitioned:
			var middle=rect.get_center().x
			for part in [Rect2(rect.position,Vector2(middle-rect.position.x,rect.size.y)),Rect2(Vector2(middle,rect.position.y),Vector2(rect.end.x-middle,rect.size.y))]:
				var ring=PackedVector2Array([part.position,Vector2(part.end.x,part.position.y),part.end,Vector2(part.position.x,part.end.y)])
				var mesh=MapWaterMaterials.mesh(AtlasSurface.build([ring],256).mesh)
				meshes.append(mesh);draw_mesh(mesh,source)
		else:
			# Independent single-quad reference: no production mesh encoder.
			var points=PackedVector2Array([rect.position,Vector2(rect.end.x,rect.position.y),rect.end,Vector2(rect.position.x,rect.end.y)])
			var uv=PackedVector2Array()
			for point in points:uv.append(point/256+Vector2(4096,0))
			draw_polygon(points,PackedColorArray([Color.WHITE]),uv,source)

var app
var viewport: SubViewport
var fixture: Fixture
var checks: Array=[]
var samples: Array=[]

static func run(application) -> void:
	var qa=WaterContinuityQA.new();qa.app=application;await qa.execute()

func check(passed: bool, name: String) -> void:
	checks.append({"name":name,"passed":passed})
	if not passed:push_error("WATER_CONTINUITY_QA: "+name)

func frame() -> Image:
	fixture.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	for index in range(4):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()

func difference(first: Image, second: Image, shift: Vector2i=Vector2i.ZERO) -> Dictionary:
	var maximum=0.0;var total=0.0;var count=0
	for x in range(48,first.get_width()-48,5):
		for y in range(48,first.get_height()-48,5):
			var a=first.get_pixel(x,y);var b=second.get_pixel(x-shift.x,y-shift.y)
			var delta=maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))*255.0
			maximum=maxf(maximum,delta);total+=delta;count+=1
	return {"maximum_channel_delta":maximum,"mean_channel_delta":total/maxi(1,count),"pixels":count}

func seam(image: Image, axis: int) -> Dictionary:
	var maximum=0.0;var count=0
	for step in range(24,232,4):
		var left=Vector2i(191,step) if axis==0 else Vector2i(step,127)
		var right=left+Vector2i(1,0) if axis==0 else left+Vector2i(0,1)
		var a=image.get_pixelv(left);var b=image.get_pixelv(right)
		var delta=maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))*255.0
		maximum=maxf(maximum,delta);count+=1
	return {"axis":axis,"maximum_channel_delta":maximum,"pixels":count}

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--water-continuity-output")
	var folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/water_continuity_native"
	DirAccess.make_dir_recursive_absolute(folder)
	viewport=SubViewport.new();viewport.size=Vector2i(384,256);viewport.disable_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;app.add_child(viewport)
	fixture=Fixture.new();fixture.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	fixture.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	fixture.material=GroundMaterialBlend.material(false);viewport.add_child(fixture)
	check(fixture.material!=null,"shipping_compatibility_material_available")
	if fixture.material!=null:
		for id in MapWaterMaterials.IDS:
			fixture.source=app.assets.texture("tile",id)
			check(fixture.source!=null and fixture.source.get_width()==512,"actual_independent_imported_source_available:"+id)
			if fixture.source==null:continue
			fixture.partitioned=false;fixture.pan=Vector2(-128,-64);fixture.magnification=1
			var reference=await frame();fixture.partitioned=true;var partition=await frame()
			var split=difference(reference,partition);samples.append({"id":id,"mesh_partition":split})
			check(split.maximum_channel_delta<=2 and split.pixels>1000,"production_partition_matches_independent_continuous_quad:"+id)
			fixture.partitioned=false;fixture.pan+=Vector2(16,8);var shifted=await frame()
			var phase=difference(reference,shifted,Vector2i(16,8));samples.append({"id":id,"world_phase":phase})
			check(phase.maximum_channel_delta<=2,"panning_retains_world_space_water_phase:"+id)
			fixture.pan=Vector2(-128,-64)+Vector2(256,0);var repeated=await frame()
			var repeat_delta=difference(reference,repeated);samples.append({"id":id,"nominal_period":repeat_delta})
			check(repeat_delta.mean_channel_delta>.1,"source_period_does_not_create_identical_repeated_water_tiles:"+id)
			fixture.pan=Vector2.ZERO;fixture.magnification=16;var border=await frame()
			for axis in [0,1]:
				var measured=seam(border,axis);samples.append({"id":id,"mirrored_source_edge":measured})
				check(measured.maximum_channel_delta<=8,"mirrored_source_edge_is_continuous_at_positive_negative_world_boundary:"+id+":"+str(axis))
			fixture.magnification=.0446823365;fixture.pan=Vector2(-128,-64);var overview=await frame()
			overview.save_png(folder.path_join(id+"_overview.png"))
			var center=overview.get_pixel(192,128)
			var minimum=Vector3.ONE;var maximum=Vector3.ZERO
			for x in range(24,360,4):
				for y in range(24,232,4):
					var color=overview.get_pixel(x,y);var rgb=Vector3(color.r,color.g,color.b)
					minimum=minimum.min(rgb);maximum=maximum.max(rgb)
			var spread=(maximum-minimum)*255.0
			samples.append({"id":id,"overview_zoom":fixture.magnification,"overview_channel_spread":maxf(spread.x,maxf(spread.y,spread.z))})
			check(center.g>center.r and center.b>center.r and center.a>.99 and maxf(spread.x,maxf(spread.y,spread.z))<=2,
				"continental_minification_uses_source_average_without_repeated_bright_dots:"+id)
	var passed=checks.all(func(row):return row.passed)
	var report={"passed":passed,"build_version":ContentRegistry.APP_VERSION,"checks":checks,"samples":samples,
		"scope":"Synthetic native GPU fixture: shipping water shader/imports, actual mesh partition, positive/negative source-edge continuity, world phase, mipmapped overview and repetition. Not a gameplay image or formal art approval.",
		"source_images_modified":false,"physical_android_device_tested":false,"formal_art_approval":false}
	var file=FileAccess.open(folder.path_join("validation.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"));file.close()
	viewport.queue_free();print("WATER_CONTINUITY_QA ",JSON.stringify({"passed":passed,"checks":checks.size()}))
	app.get_tree().quit(0 if passed else 1)
