extends SceneTree

var content=ContentRegistry.new()
var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error("MAP_DETAIL: "+name)

func center_of(rect: Rect2) -> Vector2:return rect.get_center()

func run() -> void:
	verify(content.load_all(),"content_loads")
	if not failures.is_empty():finish();return
	var library=AssetLibrary.new()
	var asia=StateBuilder.create(content,"asia_1840","qing",{})
	var before=ContentRegistry.fingerprint(asia)
	var view=MapView.new();view.size=Vector2(1280,720);view.setup(content,library);view.set_state(asia)
	var relief_diagnostics=view.relief.diagnostics.duplicate(true)
	var landcover_count=view.historical_landcover_features.size()
	verify(view.relief.mesh!=null,"strategic_layer_builds_relief_mesh")
	verify(view.relief.features.size()>0,"strategic_layer_places_source_terrain_features")
	verify(landcover_count>=8,"strategic_layer_shows_only_dated_sourced_landcover_landmarks")
	verify(view.relief.contours.is_empty() and not relief_diagnostics.get("generated_continental_contours",true),"continental_scale_does_not_invent_surveyed_contours")
	verify(relief_diagnostics.get("geographic_gradient_in_meters",false) and not relief_diagnostics.get("strategic_category_relief",true) and not str(asia.map.get("physical_relief_source","")).is_empty() and relief_diagnostics.get("source","")==asia.map.physical_relief_source and asia.map.cells.any(func(cell):return cell.get("elevation_m",0)!=null and float(cell.get("elevation_m",0))>2000),"strategic_relief_uses_attributed_numeric_elevation_and_physical_slopes")
	verify(view.river_lines.size()>=200 and view.coast_lines.size()>=400,"strategic_layer_keeps_real_hydrography_and_coastline_vectors")
	verify(view.river_lines.filter(func(line):return line[0]!=line[-1]).size()==252,"source_open_rivers_are_not_closed_by_false_chords")
	verify(view.detail_river_lines.size()>=600,"strategic_layer_loads_sourced_minor_tributaries")
	verify(view.territory_field_diagnostics.get("enabled",false) and int(view.territory_field_diagnostics.get("cells_assigned",0))>=2000,"strategic_control_field_covers_real_land_cells")
	verify(int(view.territory_field_diagnostics.get("owners",0))>=12 and int(view.territory_field_diagnostics.get("border_segments",0))>=200,"strategic_control_field_keeps_multi_faction_boundaries")
	verify(MapView.TERRITORY_FIELD_OPACITY>0.10 and MapView.TERRITORY_FIELD_OPACITY<0.40,"strategic_control_field_is_translucent")
	var territory_field_diagnostics=view.territory_field_diagnostics.duplicate(true)
	verify(before==ContentRegistry.fingerprint(asia),"relief_preparation_does_not_mutate_authoritative_asia_state")
	view.fit_map();var full_center=view.world_bounds.get_center()
	verify(view.camera_bounds_source=="full_map" and view.camera.distance_to(full_center)<1.0,"free_world_fits_full_asia_bounds")
	var free_bounds=view.camera_bounds
	view.free()

	var campaign=StateBuilder.create(content,"campaign_1840_01","qing",{})
	var campaign_view=MapView.new();campaign_view.size=Vector2(1280,720);campaign_view.setup(content,library);campaign_view.set_state(campaign)
	verify(campaign_view.camera_bounds_source.begins_with("campaign_theatre:"),"strategic_campaign_has_local_camera_theatre")
	verify(campaign_view.camera_bounds.size.x<campaign_view.world_bounds.size.x*.72 and campaign_view.camera_bounds.size.y<campaign_view.world_bounds.size.y*.72,"campaign_theatre_is_smaller_than_continental_asia")
	campaign_view.camera=campaign_view.world_bounds.end+Vector2(100000,100000);campaign_view.zoom=.72;campaign_view.clamp_camera()
	verify(campaign_view.camera.x<=campaign_view.camera_bounds.end.x+1 and campaign_view.camera.y<=campaign_view.camera_bounds.end.y+1,"campaign_camera_clamps_to_local_theatre_maximum")
	campaign_view.camera=campaign_view.world_bounds.position-Vector2(100000,100000);campaign_view.clamp_camera()
	verify(campaign_view.camera.x>=campaign_view.camera_bounds.position.x-1 and campaign_view.camera.y>=campaign_view.camera_bounds.position.y-1,"campaign_camera_clamps_to_local_theatre_minimum")
	verify(free_bounds.size.x>campaign_view.camera_bounds.size.x,"free_world_boundary_remains_continental")
	campaign_view.free()

	var tactical=StateBuilder.create(content,"campaign_1924_03","zhili",{})
	var tactical_view=MapView.new();tactical_view.size=Vector2(1280,720);tactical_view.setup(content,library);tactical_view.set_state(tactical)
	verify(not tactical.map.get("strategic_scale",false) and tactical_view.camera_bounds_source=="full_map","tactical_campaign_uses_its_authored_local_extent")
	verify(tactical_view.crossing_markers.size()>=4 and tactical_view.crossing_markers.all(func(c):return c.kind in ["bridge","ferry"]),"tactical_map_draws_sourced_bridge_and_ferry_markers")
	tactical_view.free()

	var playback=BattlePlayback.new();var probe=StateBuilder.unit("motion_probe","rifle","qing",{"q":0,"r":0},content)
	playback.active=true;playback.current={"kind":"move","unit_id":"motion_probe","path":[{"q":0,"r":0},{"q":1,"r":0},{"q":2,"r":0}],"duration":1.0};playback.elapsed=.34
	var foot=playback.motion_visual(probe,content)
	probe.def_id="cavalry";var horse=playback.motion_visual(probe,content)
	probe.def_id="armored_train";playback.current.kind="rail";var train=playback.motion_visual(probe,content)
	verify(foot.profile=="foot" and horse.profile=="cavalry" and train.profile=="rail","movement_profiles_follow_unit_family")
	verify(foot.offset!=horse.offset and horse.scale!=train.scale,"movement_profiles_have_distinct_visual_cadence")

	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION,"relief":relief_diagnostics,"territory_field":territory_field_diagnostics,"landcover_feature_count":landcover_count,"scope":"Strategic terrain detail, sourced dated landcover landmarks, translucent current-owner field, campaign camera theatre boundaries and unit-family movement profiles."}
	var file=FileAccess.open("res://reports/map_detail_boundary_motion_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_DETAIL_BOUNDARY_MOTION_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}))
	quit(0 if failures.is_empty() else 1)

func finish() -> void:
	var report={"passed":false,"checks":checks,"failures":failures,"content_hash":content.content_hash,"game_version":ContentRegistry.APP_VERSION}
	var file=FileAccess.open("res://reports/map_detail_boundary_motion_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close();quit(1)
