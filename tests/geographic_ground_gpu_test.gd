extends SceneTree

# Native GPU numerical fixture. These captures are not gameplay/concept art.
class Fixture extends Node2D:
	var source: ArrayMesh
	var quad=false
	var center=Vector2((106.5-20)*48,(80-43.5)*64)
	func _draw() -> void:
		draw_set_transform(Vector2(192,128)-center)
		if not quad:draw_mesh(source,null);return
		var rect=Rect2(center-Vector2(220,160),Vector2(440,320))
		var points=PackedVector2Array([rect.position,rect.position+Vector2(rect.size.x,0),rect.end,rect.position+Vector2(0,rect.size.y)])
		var color=PackedColorArray([Color.WHITE,Color.WHITE,Color.WHITE,Color.WHITE])
		var uv=Vector2(0,GeographicGroundField.UV_MARKER)
		draw_polygon(points,color,PackedVector2Array([uv,uv,uv,uv]))

var viewport: SubViewport
var fixture: Fixture
var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool,name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func frame() -> Image:
	fixture.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	for i in range(5):await process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()

func difference(a: Image,b: Image,shift: Vector2i=Vector2i.ZERO) -> Dictionary:
	var maximum=0.0;var count=0;var total=0.0
	for y in range(32,224,3):
		for x in range(32,352,3):
			var first=a.get_pixel(x,y);var second=b.get_pixel(x-shift.x,y-shift.y)
			var delta=maxf(absf(first.r-second.r),maxf(absf(first.g-second.g),absf(first.b-second.b)))*255.0
			maximum=maxf(maximum,delta);total+=delta;count+=1
	return {"maximum_channel_delta":maximum,"mean_channel_delta":total/count,"pixels":count}

func run() -> void:
	var args=OS.get_cmdline_user_args();var output=args[args.find("--output")+1]
	var content=ContentRegistry.new();verify(content.load_all(),"actual_content_loads")
	var map: Dictionary=content.maps.asia_strategic
	var source=MapCoastGeometry.land(MapCoastGeometry.for_map(map),768).mesh
	var ground=GeographicGroundField.new();ground.build(map,source)
	var relief=GeographicReliefField.new();relief.build(map,source)
	viewport=SubViewport.new();viewport.size=Vector2i(384,256);viewport.disable_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;root.add_child(viewport)
	fixture=Fixture.new();fixture.source=ground.mesh;fixture.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED
	fixture.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	fixture.material=GroundMaterialBlend.material(true);relief.bind_to(fixture.material,true);ground.bind_to(fixture.material)
	viewport.add_child(fixture)
	verify(ground.texture!=null and ground.weight_texture!=null and fixture.material!=null,"compatibility_gpu_has_original_materials_and_numeric_weight_array")
	var actual=await frame();actual.save_png(output+"/source_mesh_fixture.png")
	fixture.quad=true;var unpartitioned=await frame();unpartitioned.save_png(output+"/continuous_quad_fixture.png")
	var partitions=difference(actual,unpartitioned)
	verify(partitions.maximum_channel_delta<=2 and partitions.pixels>6000,"geographic_material_pixels_do_not_depend_on_land_mesh_triangles_or_rule_hex_partition")
	fixture.center+=Vector2(19,13);var moved=await frame();moved.save_png(output+"/panned_quad_fixture.png")
	var anchored=difference(unpartitioned,moved,Vector2i(19,13))
	verify(anchored.maximum_channel_delta<=2,"camera_pan_preserves_world_material_coordinates_and_boundary_phase")
	fixture.center-=Vector2(19,13);fixture.quad=false
	fixture.material.set_shader_parameter("geographic_ground_enabled",false)
	var disabled=await frame();var enabled_difference=difference(actual,disabled)
	verify(enabled_difference.mean_channel_delta>10,"passing_fixture_actually_uses_the_new_material_shader_branch")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"partition_difference":partitions,
		"pan_difference":anchored,"enabled_disabled_difference":enabled_difference,"field":ground.facts(),
		"driver":RenderingServer.get_video_adapter_name(),"fixture_is_gameplay_screenshot":false,
		"physical_android_device_tested":false,"formal_art_approval":false}
	var file=FileAccess.open(output+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GEOGRAPHIC_GROUND_GPU ",JSON.stringify({"passed":failures.is_empty(),"checks":checks.size(),"failures":failures}));quit(0 if failures.is_empty() else 1)
