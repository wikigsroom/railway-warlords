extends SceneTree

# Whole native viewports, same match and camera, two in-memory material choices.
# Candidate original PNGs are never resized, repainted or written by this driver.
var app
var textures: Array=[]
const OUT="res://reports/ground_material_v0231/pilot_scale_02"

func _initialize() -> void:call_deferred("execute")

func candidate_material(view) -> ShaderMaterial:
	var original=GroundMaterialBlend.CODE
	var signature="vec3 ground_pigment(vec2 uv, float layer) {"
	var begin=original.find(signature);var end=original.find("// Four bilinear",begin)
	assert(begin>=0 and end>begin)
	var helper=original.substr(begin,end-begin).replace("vec3 ground_pigment(vec2 uv, float layer)","vec3 candidate_pigment(sampler2D candidate_ground, vec2 uv, float layer)")
	for uv in ["uv","uv + ground_offset(a, layer)","uv + ground_offset(b, layer)","uv + ground_offset(c, layer)"]:
		helper=helper.replace("textureGrad(ground_sources, vec3("+uv+", layer), dx, dy)","textureGrad(candidate_ground, "+uv+", dx, dy)")
	assert(not helper.contains("textureGrad(ground_sources"))
	helper=helper.replace("vec2 dx = dFdx(uv);", "uv *= 224.0 / 384.0;\n    vec2 dx = dFdx(uv);")
	var declarations="";var choices=""
	var sources: Dictionary={}
	var base=ProjectSettings.globalize_path("res://").path_join("../..").simplify_path()
	for family in ["temperate_meadow","subtropical_humus"]:
		var uniform="candidate_"+family
		declarations+="uniform sampler2D "+uniform+" : source_color, repeat_enable, filter_linear_mipmap;\n"
		choices+="    if (abs(layer - "+str(float(GroundMaterialBlend.source_layers()[family]))+") < 0.01) return candidate_pigment("+uniform+", uv, layer);\n"
		var source=base.path_join("output/imagegen/warlord/ground_material_v0231/originals/tile_ground_painted_v0231_"+family+"/r001/source.png")
		var image=Image.load_from_file(source);assert(image!=null)
		image.generate_mipmaps()
		var texture=ImageTexture.create_from_image(image);textures.append(texture);sources[uniform]=texture
	var code=original.replace(signature,helper+"\n"+signature+"\n"+choices)
	code=code.replace("uniform sampler2DArray ground_sources",declarations+"uniform sampler2DArray ground_sources")
	var material=view.map_details.ground_material(false).duplicate()
	var shader=Shader.new();shader.code=code;material.shader=shader
	material.set_shader_parameter("ground_sources",GroundMaterialBlend.source_array)
	material.set_shader_parameter("ground_alpha",MapTerrainSurfaces.alpha_for("temperate_meadow",false))
	material.set_shader_parameter("ground_repeat_period",float(MapTerrainSurfaces.macro_data().world_repeat_period))
	for uniform in sources:material.set_shader_parameter(uniform,sources[uniform])
	return material

func execute() -> void:
	assert(not DirAccess.dir_exists_absolute(OUT),"Preserve earlier candidate captures")
	DirAccess.make_dir_recursive_absolute(OUT)
	app=load("res://app/main.tscn").instantiate();root.add_child(app)
	await process_frame
	var captures: Array=[];var states_unchanged=true
	for row in [["wuhan","legion_07","hankou",1.05],["beijing","campaign_1924_05","beijing",.9],["shanhaiguan","campaign_1924_03","shanhaiguan",.88]]:
		app.start_game(row[1],"zhili");app.close_overlay()
		for i in range(16):await process_frame
		var view=app.map_view
		var city=app.match_controller.state.cities.filter(func(c):return c.id==row[2])[0]
		view.camera=HexGrid.to_world(HexGrid.coordinate(city.position));view.zoom=float(row[3]);view.clamp_camera()
		var state_before=ContentRegistry.fingerprint(app.match_controller.state)
		var baseline=view.map_details.ground_material(false)
		var candidate=candidate_material(view)
		var camera=view.camera
		for choice in ["painted"]:
			var material=baseline if choice=="baseline" else candidate
			view.map_details.blend_material=material;view.material=material;view.backdrop_view.material=material
			for control in [true,false]:
				view.show_control=control;view.backdrop_signature="";view.queue_redraw()
				for i in range(16):await process_frame
				var path=OUT+"/"+str(row[0])+"_"+choice+("_control" if control else "_natural")+".png"
				assert(await app.capture_ui(path,"ground_material_pilot"))
				var metadata_path=path.get_basename()+".json"
				var metadata=JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
				metadata["candidate_only"]=true;metadata["shipping_evidence"]=false
				metadata["material_choice"]=choice;metadata["candidate_world_period"]=384;metadata["source_geography_changed"]=false
				metadata["candidate_full_source_dimensions"]=[1254,1254]
				metadata["candidate_texture_import_max_dimension"]=0
				metadata["baseline_import_max_dimension"]=384
				metadata["comparison_limitations"]="Candidate uses full-size source with native mipmaps; accepted installation must be rechecked with normal engine imports."
				var file=FileAccess.open(metadata_path,FileAccess.WRITE);file.store_string(JSON.stringify(metadata,"\t"));file.close()
				assert(view.camera==camera and is_equal_approx(view.zoom,float(row[3])))
				captures.append({"path":path,"sha256":FileAccess.get_sha256(path),"metadata":metadata_path,"metadata_sha256":FileAccess.get_sha256(metadata_path)})
		states_unchanged=states_unchanged and ContentRegistry.fingerprint(app.match_controller.state)==state_before
	var report={"passed":states_unchanged,"base_version":ContentRegistry.APP_VERSION,"mode":"native_development_engine_in_memory_material_trial","captures":captures,"matches_unchanged":states_unchanged,"source_geography_changed":false,"rules_changed":false,"runtime_installed":false,"formal_art_approval":false,"physical_android_tested":false,"manual_image_compositing":false,"raw_complete_viewports":true}
	var file=FileAccess.open(OUT+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GROUND_MATERIAL_PILOT ",JSON.stringify({"passed":states_unchanged,"captures":captures.size()}));quit(0 if states_unchanged else 1)
