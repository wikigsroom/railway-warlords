class_name ReliefShadeQA
extends RefCounted

# Synthetic numerical fixtures, never historical screenshots or generated art.
# CPU reference evaluates all sixteen weights directly, independently of the
# shipping shader's four bilinear lookups and the mesh's triangle diagonals.
class Fixture extends Node2D:
	var dimensions=Vector2(384,256)
	var pan=Vector2(-29,-13)
	var field: ReliefShadeField
	var opposite=false
	var mesh: ArrayMesh
	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO,dimensions),Color("b4bd91"))
		if field==null:return
		draw_set_transform(dimensions*.5-pan)
		var hexes=[Vector2i(-7,-7),Vector2i(7,-7),Vector2i(7,7),Vector2i(-7,7)]
		var order=[0,1,3,1,2,3] if opposite else [0,1,2,0,2,3]
		var vertices=PackedVector3Array();var uvs=PackedVector2Array()
		for index in order:
			var p=HexGrid.to_world(hexes[index]);vertices.append(Vector3(p.x,p.y,0));uvs.append(field.uv(hexes[index]))
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_TEX_UV]=uvs
		mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		draw_mesh(mesh,null)

var app
var viewport: SubViewport
var fixture: Fixture
var checks: Array=[]
var samples: Array=[]
var captures: Array=[]
var folder=""

static func run(application) -> void:
	var qa=ReliefShadeQA.new();qa.app=application;await qa.execute()

func check(passed: bool, name: String) -> void:
	checks.append({"name":name,"passed":passed})
	if not passed:push_error("RELIEF_SHADE_QA: "+name)

func frame(name: String) -> Image:
	fixture.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	for i in range(4):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image=viewport.get_texture().get_image();var path=folder+"/"+name+".png"
	check(image!=null and image.get_size()==Vector2i(384,256) and image.save_png(path)==OK,"complete_native_fixture_capture:"+name)
	captures.append({"path":path,"whole_native_viewport":true,"synthetic_fixture_not_gameplay":true})
	return image

func field(constant: bool=false, supported: bool=true) -> ReliefShadeField:
	var cells: Dictionary={};var shades: Dictionary={}
	for q in range(-8,9):
		for r in range(-8,9):
			var id=HexGrid.key(Vector2i(q,r));cells[id]={"id":id,"position":HexGrid.position(Vector2i(q,r))}
			if not supported:continue
			var t=.5+.5*sin(q*1.17+r*.63)
			shades[id]=Color(.24+t*.45,.32+t*.32,.25+t*.19,.08+t*.28) if not constant else Color(.28,.42,.33,.27)
	var result=ReliefShadeField.new();result.build(cells,shades);return result

func expected_colour(world: Vector2) -> Color:
	# Fractional axial inverse, not a rounded picking coordinate.
	var axial=Vector2(world.x/(1.5*HexGrid.RADIUS),world.y/(sqrt(3.0)*HexGrid.RADIUS)-world.x/(3.0*HexGrid.RADIUS))
	var p=axial-Vector2(fixture.field.origin_hex);var base=Vector2i(floori(p.x),floori(p.y));var f=p-Vector2(base)
	var weights: Array=[]
	for t in [f.x,f.y]:weights.append([pow(1.0-t,3)/6.0,(3.0*t*t*t-6.0*t*t+4.0)/6.0,(-3.0*t*t*t+3.0*t*t+3.0*t+1.0)/6.0,t*t*t/6.0])
	var rgba=Vector4.ZERO
	for x in range(4):
		for y in range(4):
			var at=base+Vector2i(x-1,y-1)
			var value=fixture.field.image.get_pixel(at.x,at.y)
			rgba+=Vector4(value.r,value.g,value.b,value.a)*weights[0][x]*weights[1][y]
	var background=Color("b4bd91")
	return Color(rgba.x+background.r*(1.0-rgba.w),rgba.y+background.g*(1.0-rgba.w),rgba.z+background.b*(1.0-rgba.w))

func compare(first: Image, second: Image=null, shift: Vector2i=Vector2i.ZERO) -> Dictionary:
	var maximum=0.0;var total=0.0;var count=0
	for x in range(48,336,7):
		for y in range(48,208,7):
			var actual=first.get_pixel(x,y)
			var expected=second.get_pixel(x-shift.x,y-shift.y) if second!=null else expected_colour(Vector2(x+.5,y+.5)-fixture.dimensions*.5+fixture.pan)
			var delta=maxf(absf(actual.r-expected.r),maxf(absf(actual.g-expected.g),absf(actual.b-expected.b)))*255.0
			maximum=maxf(maximum,delta);total+=delta;count+=1
	return {"maximum_channel_delta":maximum,"mean_channel_delta":total/maxi(1,count),"pixels":count}

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--relief-shade-output")
	folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/relief_shade_native"
	DirAccess.make_dir_recursive_absolute(folder)
	viewport=SubViewport.new();viewport.size=Vector2i(384,256);viewport.disable_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;app.add_child(viewport)
	fixture=Fixture.new();fixture.material=GroundMaterialBlend.material(false);viewport.add_child(fixture)
	check(fixture.material!=null,"shipping_compatibility_material_is_available")
	if fixture.material!=null:
		for constant in [true,false]:
			fixture.field=field(constant);fixture.field.bind_to(fixture.material);fixture.opposite=false
			var name="constant" if constant else "varying"
			var first=await frame(name);var measured=compare(first);samples.append({"reference":name,"comparison":measured})
			check(measured.maximum_channel_delta<=2 and measured.pixels>=900,"gpu_matches_independent_sixteen_weight_cpu_reference:"+name)
			if not constant:
				fixture.opposite=true;var reordered=await frame("opposite_triangles");var diagonal=compare(first,reordered);samples.append({"triangle_diagonals":diagonal})
				check(diagonal.maximum_channel_delta<=1,"lighting_is_independent_of_mesh_triangle_diagonals")
				fixture.pan+=Vector2(23,19);var moved=await frame("panned");var anchored=compare(reordered,moved,Vector2i(23,19));samples.append({"world_phase":anchored})
				check(anchored.maximum_channel_delta<=2,"camera_pan_preserves_the_source_lighting_phase")
				var panned_reference=compare(moved);samples.append({"reference":"panned","comparison":panned_reference})
				check(panned_reference.maximum_channel_delta<=2,"panned_gpu_matches_the_independent_source_reference")
		fixture.field=field(false,false);fixture.field.bind_to(fixture.material)
		check(not fixture.material.get_shader_parameter("relief_enabled"),"missing_source_support_disables_the_lookup_without_stale_data")
	var failures=checks.filter(func(row):return not row.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"samples":samples,"captures":captures,"build_version":ContentRegistry.APP_VERSION,
		"renderer":RenderingServer.get_current_rendering_method(),"rendering_device":RenderingServer.get_video_adapter_name(),"fixture_size":[384,256],
		"scope":"Native GPU/independent CPU lighting agreement, triangle-diagonal independence and world-phase invariance. Synthetic numerical fixtures, not historical-map screenshots or artistic acceptance.",
		"new_dem_samples":0,"source_images_modified":false,"physical_android_device_tested":OS.has_feature("android"),"ew6_parity_claimed":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RELIEF_SHADE_NATIVE ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures,"samples":samples}));app.get_tree().quit(0 if failures.is_empty() else 1)
