class_name GroundContinuityQA
extends RefCounted

# Offscreen native material fixture, not a historical map or gameplay screenshot.
# First calibrate direct sampling against an independently drawn whole-source
# texture, then compare production sampling on unpartitioned and hex geometry.
class Fixture extends Node2D:
	var dimensions=Vector2(384,256)
	var pan=Vector2(-29,-13)
	var batches: Array=[]
	var reference: Texture2D
	var reference_period=224.0
	var reference_layer=-1
	var reversed=false
	func _draw() -> void:
		draw_set_transform(dimensions*.5-pan)
		draw_rect(Rect2(pan-dimensions*.5,dimensions),Color("b4bd91"))
		if reference!=null:
			# Independent direct-sampling calibration, with production stochastic
			# sampling disabled explicitly. This is not an art acceptance claim.
			var scale=reference.get_width()/reference_period
			draw_texture_rect_region(reference,Rect2(pan-dimensions*.5,dimensions),Rect2((pan-dimensions*.5)*scale,dimensions*scale),Color(1,1,1,.94))
		elif reference_layer>=0:
			# A single continuous quad is independent of hex partitions and
			# their barycentric weights; the shader is the actual shipping shader.
			var rect=Rect2(pan-dimensions*.5-Vector2(16,16),dimensions+Vector2(32,32))
			var points=PackedVector2Array([rect.position,rect.position+Vector2(rect.size.x,0),rect.end,rect.position+Vector2(0,rect.size.y)])
			var layer=reference_layer/255.0
			var color=Color(layer,layer,layer,1)
			var uv=GroundMaterialBlend.weights(1,0)
			draw_polygon(points,PackedColorArray([color,color,color,color]),PackedVector2Array([uv,uv,uv,uv]))
		else:
			var ordered=batches.duplicate()
			if reversed:ordered.reverse()
			for batch in ordered:draw_mesh(batch.mesh,null)

var app
var viewport: SubViewport
var fixture: Fixture
var checks: Array=[]
var samples: Array=[]

static func run(application) -> void:
	var qa=GroundContinuityQA.new();qa.app=application;await qa.execute()

func check(passed: bool, name: String) -> void:
	checks.append({"name":name,"passed":passed})
	if not passed:push_error("GROUND_CONTINUITY_QA: "+name)

func frame() -> Image:
	fixture.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	for i in range(4):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()

func difference(first: Image, second: Image, shift: Vector2i=Vector2i.ZERO) -> Dictionary:
	var maximum=0.0;var total=0.0;var count=0
	for x in range(48,first.get_width()-48,7):
		for y in range(48,first.get_height()-48,7):
			var a=first.get_pixel(x,y);var b=second.get_pixel(x-shift.x,y-shift.y)
			var delta=maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))*255.0
			maximum=maxf(maximum,delta);total+=delta;count+=1
	return {"maximum_channel_delta":maximum,"mean_channel_delta":total/maxi(1,count),"pixels":count}

func patch(families: Array) -> Dictionary:
	var details=MapDetails.new();var entries: Array=[]
	for q in range(-5,6):
		for r in range(-5,6):
			var hex=Vector2i(q,r);var family=str(families[posmod(q-r,families.size())])
			details.surfaces[HexGrid.key(hex)]=MapTerrainSurfaces.variant_for(family,hex)
			details.surface_families[HexGrid.key(hex)]=family
			entries.append({"hex":hex,"cell":{},"kind":"plain"})
	return details.continuous_macro_meshes(Rect2(-600,-800,1200,1600))

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--ground-continuity-output")
	var folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/ground_continuity_native"
	DirAccess.make_dir_recursive_absolute(folder)
	viewport=SubViewport.new();viewport.size=Vector2i(384,256);viewport.disable_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;app.add_child(viewport)
	fixture=Fixture.new();fixture.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	fixture.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	fixture.material=GroundMaterialBlend.material(false);viewport.add_child(fixture)
	check(fixture.material!=null,"shipping_compatibility_shader_and_complete_source_array_are_available")
	if fixture.material!=null:
		fixture.material.set_shader_parameter("ground_stochastic",false)
		fixture.material.set_shader_parameter("ground_seam_feather",false)
		check(GroundMaterialBlend.source_array.get_layers()==20,"all_twenty_complete_originals_are_available_as_independent_runtime_layers")
		for family in GroundMaterialBlend.source_layers():
			var id=MapTerrainSurfaces.macro_id(family)
			var source=load("res://assets/tile/"+id+".png") as Texture2D
			var image=source.get_image()
			if image.is_compressed():image.decompress()
			image.convert(Image.FORMAT_RGBA8)
			if not image.has_mipmaps():image.generate_mipmaps()
			var copied=GroundMaterialBlend.source_array.get_layer_data(GroundMaterialBlend.source_layers()[family])
			check(copied.get_size()==image.get_size() and copied.get_data()==image.get_data(),"runtime_layer_preserves_whole_original_pixels_and_mips:"+family)
			fixture.reference_period=MapTerrainSurfaces.macro_period(family)
			fixture.reference=ImageTexture.create_from_image(image);var reference=await frame()
			fixture.reference=null;fixture.batches=patch([family]).batches;var actual=await frame()
			var measured=difference(reference,actual);measured["family"]=family;samples.append(measured)
			measured["sampling_mode"]="direct_calibration"
			check(measured.maximum_channel_delta<=2 and measured.pixels>=500,"hex_seams_match_independent_continuous_source_render:"+family)
		fixture.material.set_shader_parameter("ground_stochastic",true)
		fixture.material.set_shader_parameter("ground_seam_feather",true)
		for family in ["temperate_meadow","weathered_rock","alluvial_loam"]:
			fixture.reference_layer=GroundMaterialBlend.source_layers()[family];var reference=await frame()
			fixture.reference_layer=-1;fixture.batches=patch([family]).batches;var actual=await frame()
			var production=difference(reference,actual);production["production_family"]=family;samples.append(production)
			check(production.maximum_channel_delta<=2 and production.pixels>=500,"production_whole_source_sampling_has_no_hex_partition_seams:"+family)
		fixture.batches=patch(["temperate_meadow","dry_steppe","gravel_gobi"]).batches
		fixture.reversed=false;var first=await frame();fixture.reversed=true;var reordered=await frame()
		var ordering=difference(first,reordered);samples.append({"draw_order":ordering})
		check(ordering.maximum_channel_delta<=1,"three_material_boundary_pixels_are_independent_of_draw_order")
		fixture.pan+=Vector2(23,19);var moved=await frame();var anchored=difference(reordered,moved,Vector2i(23,19));samples.append({"world_phase":anchored})
		check(anchored.maximum_channel_delta<=2,"camera_pan_keeps_material_boundaries_and_source_phase_fixed_in_world_space")
		fixture.batches=patch(["weathered_rock"]).batches;fixture.pan=Vector2(-29,-13);var original_phase=await frame()
		fixture.pan+=Vector2(float(MapTerrainSurfaces.macro_data().world_repeat_period),0);var next_phase=await frame()
		var periodicity=difference(original_phase,next_phase);samples.append({"fixed_period_removed":periodicity})
		check(periodicity.mean_channel_delta>0.5,"production_source_does_not_repeat_at_one_texture_period")
	var failures=checks.filter(func(row):return not row.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"samples":samples,"build_version":ContentRegistry.APP_VERSION,
		"renderer":RenderingServer.get_current_rendering_method(),"rendering_device":RenderingServer.get_video_adapter_name(),"fixture_size":[384,256],
		"scope":"Native direct-sampling calibration against the whole source; production sampling on one quad versus hex partitions; draw-order independence, world-phase invariance and fixed-period suppression. Synthetic material fixtures, not historical-map screenshots or artistic acceptance.",
		"source_images_modified":false,"physical_android_device_tested":OS.has_feature("android"),"ew6_parity_claimed":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_CONTINUITY_NATIVE ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"samples":samples}));app.get_tree().quit(0 if failures.is_empty() else 1)
