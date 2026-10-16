extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func tap(view: MapView, at: Vector2, touch: bool=false) -> void:
	if touch:
		var event=InputEventScreenTouch.new();event.index=0;event.position=at;event.pressed=true;view._gui_input(event);event.pressed=false;view._gui_input(event)
	else:
		var event=InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT;event.position=at;event.pressed=true;view._gui_input(event);event.pressed=false;view._gui_input(event)

func run() -> void:
	var app=load("res://app/main.tscn").instantiate();app.qa_save_path="user://qa/places_%d"%Time.get_ticks_usec();root.size=Vector2i(1920,1080);root.add_child(app)
	await process_frame
	app.start_game("campaign_1924_03","zhili");app.close_overlay();await process_frame;await process_frame
	var view: MapView=app.map_view;var catalog=HistoricalPlaces.data()
	verify(catalog.places.size()==67,"67_sourced_additional_places_load_from_shipping_resource")
	verify(catalog.sources.size()==16,"source_attribution_is_available")
	verify(view.places.nodes.size()==view.state.map.cities.size()+32,"jingfeng_preserves_authored_cities_and_adds_32_geographic_nodes")
	verify(HistoricalPlaces.kind({"id":"tianjin"},"1924-12-31")=="capital" and HistoricalPlaces.kind({"id":"tianjin"},"1925-01-01")=="city","tianjin_province_rank_is_bounded_to_verified_period")
	verify(HistoricalPlaces.kind({"id":"shijiazhuang"},"1924-01-01")=="market" and HistoricalPlaces.kind({"id":"tangshan"},"1924-01-01")=="market","modern_municipal_status_is_not_projected_back_to_1924")
	verify(HistoricalPlaces.kind(catalog.places.filter(func(p):return p.id=="place_hefei")[0],view.state.date)=="county" and HistoricalPlaces.kind({"id":"zhengzhou"},view.state.date)=="county","hefei_and_zhengzhou_are_not_modern_province_capitals")
	verify(view.places.index.place_baodi.province=="京兆地方" and view.places.index.place_chadao.province=="直隶","jingzhao_membership_and_pre_1928_chadao_administration")
	var village=view.places.index.place_beiyingzi
	app.selected_unit_id="";app.selected_city_id="";app.selected_poi_id="";app.refresh_battle();view.camera=village.at;view.zoom=.76;view.clamp_camera()
	var before=ContentRegistry.fingerprint(app.match_controller.state)
	var selected: Array=[];var hexes: Array=[];view.place_selected.connect(func(id):selected.append(id));view.hex_selected.connect(func(hex):hexes.append(hex))
	var screen=view.world_to_screen(village.at)
	tap(view,screen)
	verify(selected==["place_beiyingzi"] and hexes.is_empty() and app.selected_poi_id=="place_beiyingzi","native_mouse_hit_opens_the_correct_village_inspector")
	tap(view,screen,true)
	verify(selected.size()==2 and hexes.is_empty(),"native_touch_tap_opens_place_once_without_duplicate_mouse_event")
	verify(ContentRegistry.fingerprint(app.match_controller.state)==before,"place_inspection_never_changes_city_economy_visibility_or_saved_rules")
	var press=InputEventMouseButton.new();press.button_index=MOUSE_BUTTON_LEFT;press.position=screen;press.pressed=true;view._gui_input(press)
	var move=InputEventMouseMotion.new();move.button_mask=MOUSE_BUTTON_MASK_LEFT;move.position=screen+Vector2(80,40);move.relative=Vector2(80,40);view._gui_input(move);press.position=move.position;press.pressed=false;view._gui_input(press)
	verify(selected.size()==2,"dragging_across_a_village_pans_without_opening_its_details")
	view.camera=village.at;view.clamp_camera();view.selected_unit_id=app.match_controller.state.units[0].id
	tap(view,view.world_to_screen(village.at))
	verify(selected.size()==2 and hexes.size()==1,"selected_unit_keeps_hex_order_input_over_place_icons")
	view.selected_unit_id="";view.show_places=false
	verify(view.place_at_screen(view.world_to_screen(village.at)).is_empty(),"hidden_place_overlay_has_no_invisible_click_targets")
	view.show_places=true
	verify(not HistoricalPlaces.visible_at(village,view.state.date,.10) and HistoricalPlaces.visible_at(village,view.state.date,.10,village.id),"overview_hides_minor_places_while_selected_place_stays_visible")
	verify(HistoricalPlaces.visible_at({"id":"place_anqing","kind":"capital"},view.state.date,.01),"province_capitals_remain_legible_in_full_country_view")
	var meshes=view.places.zones.map(func(zone):return zone.mesh.get_instance_id());var old_signature=view.places.owner_signature
	var changed=app.match_controller.state.duplicate(false);changed.cities=changed.cities.duplicate(true);changed.cities[0].owner_id="fengtian"
	view.places.update_owners(changed)
	verify(view.places.owner_signature!=old_signature and view.places.zones.map(func(zone):return zone.mesh.get_instance_id())==meshes,"capture_recolors_control_areas_without_rebuilding_or_changing_geography")
	view.places.update_owners(app.match_controller.state)
	verify(view.places.control_city(app.match_controller.state,village.at).id=="shanhaiguan","village_control_uses_its_actual_neighboring_game_city")
	app.start_game("campaign_1920_01","zhili");app.close_overlay();await process_frame
	verify(app.map_view.places.map_key=="jingjin" and app.map_view.places.nodes.size()==app.match_controller.state.map.cities.size()+23,"switching_to_a_different_coastline_rebuilds_place_footprints_after_the_new_land_index")
	var file=FileAccess.open("res://reports/historical_places_tests.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"content_hash":app.content.content_hash,"build_version":ContentRegistry.APP_VERSION,"presentation_data_sha256":FileAccess.get_sha256("res://presentation/data/settlements_v023.json"),"physical_android_device_tested":false},"\t"));file.close()
	print("HISTORICAL_PLACES_TESTS ",checks.size()-failures.size()," passed / ",failures.size()," failed");app.queue_free();await process_frame;quit(0 if failures.is_empty() else 1)
