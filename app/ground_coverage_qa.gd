class_name GroundCoverageQA
extends RefCounted

# Native numerical source-coast fixtures, explicitly not gameplay screenshots.
class Fixture extends Node2D:
	var center=Vector2.ZERO
	var mesh: ArrayMesh
	var enabled=true
	const SIZE=384
	const SCALE=3.0
	const BASE=Color("254751")
	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO,Vector2.ONE*SIZE),BASE)
		draw_set_transform(Vector2.ONE*SIZE*.5-center*SCALE,0,Vector2.ONE*SCALE)
		if enabled and mesh!=null:draw_mesh(mesh,null)

var app
var viewport: SubViewport
var fixture: Fixture
var checks: Array=[]
var cases: Array=[]
static func run(application) -> void:
	var qa=GroundCoverageQA.new();qa.app=application;await qa.execute()
func verify(value: bool,name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:push_error("GROUND_COVERAGE_NATIVE: "+name)
func frame() -> Image:
	fixture.queue_redraw();viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
	for i in range(4):await app.get_tree().process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()
func physical_land(map: Dictionary) -> AtlasRelief:
	var relief=AtlasRelief.new()
	for row in map.render_land:
		var exterior=PackedVector2Array();var holes: Array=[]
		for xy in row.exterior:exterior.append(Vector2(float(xy[0]),float(xy[1])))
		for ring in row.holes:
			var hole=PackedVector2Array()
			for xy in ring:hole.append(Vector2(float(xy[0]),float(xy[1])))
			holes.append(hole)
		relief.land.append({"exterior":exterior,"holes":holes})
		var bounds=Rect2(exterior[0],Vector2.ZERO)
		for point in exterior:bounds=bounds.expand(point)
		relief.land_bounds.append(bounds)
	return relief

func execute() -> void:
	var args=OS.get_cmdline_user_args();var index=args.find("--ground-coverage-output")
	var folder=args[index+1] if index>=0 and index+1<args.size() else "res://reports/ground_coverage_native"
	DirAccess.make_dir_recursive_absolute(folder)
	viewport=SubViewport.new();viewport.size=Vector2i(384,384);viewport.disable_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED;app.add_child(viewport)
	fixture=Fixture.new();fixture.material=GroundMaterialBlend.material(false)
	fixture.texture_repeat=CanvasItem.TEXTURE_REPEAT_ENABLED;fixture.texture_filter=CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	viewport.add_child(fixture)
	for id in ["asia_strategic","jingfeng","hankou","jingjin"]:
		var map=JSON.parse_string(FileAccess.get_file_as_string("res://content/maps/"+id+".json"))
		var coverage=MapGroundCoverage.for_map(map);var details=MapDetails.new()
		details.source_ground_coverage=coverage;details.ground_families=coverage.families;details.ground_clips=coverage.clips
		var hex_key="";var mode="source_coast" if id in ["asia_strategic","jingfeng"] else "functional_underlay"
		if mode=="source_coast":
			for key in coverage.clips:
				var rows: Array=coverage.clips[key];var area=0.0
				for i in range(0,rows.size(),3):
					var a=Vector2(rows[i][0],rows[i][1]);var b=Vector2(rows[i+1][0],rows[i+1][1]);var c=Vector2(rows[i+2][0],rows[i+2][1])
					area+=absf((b-a).cross(c-a))*.5
				if area>2000 and area<4000:hex_key=key;break
		else:
			for key in coverage.supplements:
				if coverage.supplements[key].rule_terrain in ["city","port","road","ford"] and not coverage.clips.has(key):hex_key=key;break
		verify(not hex_key.is_empty(),"actual_source_case_available:"+id)
		if hex_key.is_empty():continue
		var hex=HexGrid.from_key(hex_key);fixture.center=HexGrid.to_world(hex)
		var group={"vertices":PackedVector3Array(),"colors":PackedColorArray(),"uvs":PackedVector2Array()}
		details.append_continuous_ground(group,hex,coverage.families[hex_key])
		var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=group.vertices;arrays[Mesh.ARRAY_COLOR]=group.colors;arrays[Mesh.ARRAY_TEX_UV]=group.uvs
		fixture.mesh=ArrayMesh.new();fixture.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		fixture.enabled=false;var base=await frame();fixture.enabled=true;var image=await frame()
		var relief=physical_land(map);var water=0;var changed_land=0;var max_water_delta=0.0
		for x in range(10,374,4):
			for y in range(10,374,4):
				var point=fixture.center+(Vector2(x+.5,y+.5)-Vector2.ONE*192)/3.0
				var is_land=relief.dry_point(point);var safe=true
				for offset in [Vector2(1,0),Vector2(-1,0),Vector2(0,1),Vector2(0,-1)]:
					if relief.dry_point(point+offset)!=is_land:safe=false;break
				if not safe:continue
				var a=base.get_pixel(x,y);var b=image.get_pixel(x,y)
				var delta=maxf(absf(a.r-b.r),maxf(absf(a.g-b.g),absf(a.b-b.b)))*255.0
				if not is_land:water+=1;max_water_delta=maxf(max_water_delta,delta)
				elif HexGrid.from_world(point)==hex and delta>3:changed_land+=1
		if mode=="source_coast":verify(water>=100 and max_water_delta<=1,"source_water_stays_unpainted:"+id)
		verify(changed_land>=100,"actual_source_land_or_functional_ground_has_visible_texture:"+id)
		var path=folder+"/"+id+".png";image.save_png(path)
		cases.append({"map":id,"hex":hex_key,"mode":mode,"water_pixels":water,"max_water_channel_delta":max_water_delta,"textured_land_pixels":changed_land,"capture":path,"numerical_fixture_not_gameplay_screenshot":true})
	var failed=checks.filter(func(row):return not row.passed)
	var report={"passed":failed.is_empty(),"checks":checks,"failures":failed,"cases":cases,"build_version":ContentRegistry.APP_VERSION,"scope":"Four unmodified native numerical viewport fixtures from source coast/city cells, shipping shader and clipped mesh builder. Independent point-in-source-land water witnesses; not art approval or gameplay captures.","source_images_modified":false,"physical_android_device_tested":false,"ew6_parity_claimed":false}
	var file=FileAccess.open(folder+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_COVERAGE_NATIVE ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failed}));app.get_tree().quit(0 if report.passed else 1)
