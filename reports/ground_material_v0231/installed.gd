extends SceneTree

const OUT="res://reports/ground_material_v0231/normal_import_01"
var checks: Array=[]
var captures: Array=[]
func _initialize() -> void:call_deferred("execute")
func verify(ok: bool, name: String) -> void:
 checks.append({"name":name,"passed":ok})
 assert(ok,name)
func execute() -> void:
 assert(not DirAccess.dir_exists_absolute(OUT))
 DirAccess.make_dir_recursive_absolute(OUT)
 var app=load("res://app/main.tscn").instantiate();root.add_child(app)
 await process_frame
 for row in [["wuhan","legion_07","hankou",1.05],["beijing","campaign_1924_05","beijing",.9],["shanhaiguan","campaign_1924_03","shanhaiguan",.88]]:
  app.start_game(row[1],"zhili");app.close_overlay()
  for i in range(16):await process_frame
  var view=app.map_view
  var city=app.match_controller.state.cities.filter(func(c):return c.id==row[2])[0]
  view.camera=HexGrid.to_world(HexGrid.coordinate(city.position));view.zoom=float(row[3]);view.clamp_camera()
  var state_before=ContentRegistry.fingerprint(app.match_controller.state)
  var camera=view.camera
  verify(GroundMaterialBlend.source_array.get_layers()==20 and GroundMaterialBlend.source_array.get_width()==384 and GroundMaterialBlend.source_array.get_height()==384,str(row[0])+":normal_import_array_is_twenty_384px_layers")
  var periods=GroundMaterialBlend.source_periods();var scales=true
  for family in GroundMaterialBlend.source_layers():
   scales=scales and is_equal_approx(periods[GroundMaterialBlend.source_layers()[family]],384.0 if family in ["temperate_meadow","subtropical_humus"] else 224.0)
  verify(scales,str(row[0])+":two_material_scales_and_eighteen_existing_scales")
  verify(view.map_details.ground_material(false).get_shader_parameter("ground_source_periods")==periods,str(row[0])+":normal_material_has_native_shader_uniforms")
  for control in [true,false]:
   view.show_control=control;view.backdrop_signature="";view.queue_redraw()
   for i in range(16):await process_frame
   var path=OUT+"/"+str(row[0])+("_control" if control else "_natural")+".png"
   verify(await app.capture_ui(path,"installed_ground_material"),str(row[0])+":"+str(control)+":complete_native_capture")
   var metadata_path=path.get_basename()+".json"
   var metadata=JSON.parse_string(FileAccess.get_file_as_string(metadata_path))
   metadata["ownership_overlay_enabled"]=control
   metadata["mode"]="development_engine_normal_imports"
   metadata["historical_vegetation_survey"]=false
   var file=FileAccess.open(metadata_path,FileAccess.WRITE);file.store_string(JSON.stringify(metadata,"\t"));file.close()
   verify(view.camera==camera and is_equal_approx(view.zoom,float(row[3])),str(row[0])+":"+str(control)+":same_source_city_and_camera")
   captures.append({"path":path,"sha256":FileAccess.get_sha256(path),"metadata":metadata_path,"metadata_sha256":FileAccess.get_sha256(metadata_path)})
  verify(ContentRegistry.fingerprint(app.match_controller.state)==state_before,str(row[0])+":visibility_does_not_change_match_or_random_stream")
 var report={"passed":true,"build_version":ContentRegistry.APP_VERSION,"checks":checks,"captures":captures,"mode":"development_engine_normal_imports","formal_art_approval":false,"ew6_parity_claimed":false,"physical_android_device_tested":false,"manual_image_compositing":false,"raw_complete_viewports":true}
 var file=FileAccess.open(OUT+"/validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
 print("NORMAL_GROUND_IMPORT ",JSON.stringify({"passed":true,"checks":checks.size(),"captures":captures.size()}));quit()
