extends SceneTree

var checks: Array=[]
var failures: Array=[]

func _init() -> void:run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func plane(slope: Vector2) -> AtlasRelief:
	var relief=AtlasRelief.new();relief.meters_per_world_unit=1000.0/48.0
	for q in range(-2,3):
		for r in range(-2,3):
			var h=Vector2i(q,r);var position=HexGrid.to_world(h)*relief.meters_per_world_unit
			var cell={"id":HexGrid.key(h),"position":HexGrid.position(h),"terrain_id":"hill","natural_terrain_id":"hill","region_id":"theater","render_land_covered":true,"elevation_m":1000.0+position.dot(slope),"relief_sample_m":240.0}
			relief.cells[HexGrid.key(h)]=cell
	return relief

func run() -> void:
	var slope=Vector2(.08,-.045);var relief=plane(slope);var center: Dictionary=relief.cells["0,0"]
	var before=ContentRegistry.fingerprint(relief.cells)
	verify(relief.height_gradient(center).distance_to(slope)<.00001,"physical_slope_matches_independent_analytic_plane_in_metres")
	var translated=plane(slope)
	for cell in translated.cells.values():cell.elevation_m+=1100.0
	verify(relief.height_gradient(center).distance_to(translated.height_gradient(translated.cells["0,0"]))<.00001,"height_offset_does_not_change_slope_or_invent_landforms")
	var facing_light=plane(Vector2(.16,.16));var away_light=plane(Vector2(-.16,-.16))
	var lit=facing_light.shade(facing_light.cells["0,0"]);var dark=away_light.shade(away_light.cells["0,0"])
	verify(lit.get_luminance()>dark.get_luminance()+.12,"opposite_surveyed_slopes_receive_distinct_consistent_upper_left_light")
	var flat=plane(Vector2.ZERO);flat.cells["0,0"].relief_sample_m=0
	verify(flat.height_gradient(flat.cells["0,0"])==Vector2.ZERO and flat.shade(flat.cells["0,0"]).a<=.03,"flat_lowlands_remain_quiet_without_false_relief")
	var finite=true
	for cell in relief.cells.values():
		var color=relief.shade(cell)
		finite=finite and is_finite(color.r) and is_finite(color.g) and is_finite(color.b) and color.a>=0 and color.a<=.5
	verify(finite,"continuous_relief_colours_are_finite_and_translucent")
	verify(ContentRegistry.fingerprint(relief.cells)==before,"lighting_does_not_mutate_source_cell_or_rule_fields")
	var source_shades: Dictionary={}
	for cell in relief.cells.values():source_shades[cell.id]=relief.shade(cell)
	var field=ReliefShadeField.new();field.build(relief.cells,source_shades)
	verify(field.source_count==relief.cells.size() and field.origin_hex==Vector2i(-4,-4) and field.dimensions==Vector2i(9,9),"numerical_field_preserves_negative_axial_coordinates_with_two_sample_padding")
	var exact=true;var affine=true
	for cell in relief.cells.values():
		var h=HexGrid.coordinate(cell.position);var at=h-field.origin_hex;var stored=field.image.get_pixel(at.x,at.y);var source_color: Color=source_shades[cell.id]
		for pair in [[stored.r,source_color.r*source_color.a],[stored.g,source_color.g*source_color.a],[stored.b,source_color.b*source_color.a],[stored.a,source_color.a]]:exact=exact and absf(pair[0]-pair[1])<=.5001/255.0
		var uv=field.uv(h);var expected=(Vector2(h-field.origin_hex)+Vector2(.5,.5))/Vector2(field.dimensions)
		affine=affine and Vector2(uv.x,uv.y-ReliefShadeField.UV_MARKER).distance_to(expected)<.0001
	verify(exact,"every_gpu_lookup_component_is_the_quantized_premultiplied_source_lighting_within_half_a_byte")
	verify(affine,"relief_texture_coordinates_remain_world_fixed_and_affine_in_the_source_hex_basis")
	verify(field.image.get_format()==Image.FORMAT_RGBA8 and not field.image.has_mipmaps() and field.image.get_pixel(0,0)==Color(0,0,0,0),"portable_numerical_lookup_has_transparent_unsupported_samples_and_no_invented_edge_elevation")
	verify(field.facts().new_dem_samples==0 and not field.facts().raster_art_generated and not field.facts().source_images_modified,"lighting_data_is_not_counted_as_new_art_or_new_geographic_measurements")
	verify(ContentRegistry.fingerprint(relief.cells)==before,"building_the_numerical_lighting_field_preserves_every_source_and_rule_value")
	field.build(relief.cells,{})
	verify(field.image==null and field.texture==null and field.source_count==0 and field.dimensions==Vector2i.ZERO,"missing_source_support_clears_stale_field_without_extrapolation")
	for sample in [["ns",true],["ew",false]]:
		var ridge=plane(Vector2.ZERO)
		for cell in ridge.cells.values():
			var p=HexGrid.to_world(HexGrid.coordinate(cell.position))
			cell.elevation_m=900.0-pow(p.x if sample[1] else p.y,2)*.012
		verify(ridge.crest_axis(ridge.cells["0,0"])==sample[0],"crest_orientation_follows_independent_"+sample[0]+"_height_field")
	var single=AtlasRelief.new();single.cells={"0,0":center}
	verify(single.height_gradient(center)==Vector2.ZERO,"missing_neighbours_do_not_generate_unbounded_extrapolated_slopes")
	var data=JSON.parse_string(FileAccess.get_file_as_string("res://presentation/data/relief_visuals.json"))
	verify(data.records.size()==4 and data.full_texture_draw and not data.source_pngs_modified,"four_directional_relief_sources_have_full_texture_metadata")
	relief.asset_metadata=data.records
	var rects_valid=true;var loaded=true
	var library=AssetLibrary.new()
	for id in data.records:
		var bounds=Vector2(176,146);var rect=relief.source_rect(id,bounds)
		var row=data.records[id];var alpha=row.alpha_bounds
		var scale=rect.size.x/row.dimensions[0]
		var alpha_foot=rect.position+Vector2((alpha[0]+alpha[2])*.5,alpha[3])*scale
		rects_valid=rects_valid and alpha_foot.length()<.001 and rect.size.x>0 and rect.size.y>0 and absf(rect.size.x/rect.size.y-float(row.dimensions[0])/row.dimensions[1])<.001
		loaded=loaded and library.texture("scenery",id)!=null
	verify(rects_valid,"whole_source_aspect_and_alpha_foot_anchor_are_preserved_without_cropping")
	verify(loaded,"all_four_relief_source_textures_are_available_to_runtime")
	var abstract=plane(Vector2.ZERO);var map_cells=abstract.cells.values()
	for cell in map_cells:cell.elevation_m=null;cell.relief_sample_m=null;cell.natural_terrain_id="mountain"
	var map={"cells":map_cells,"rail_edges":[],"strategic_scale":true,"hex_radius_m":100000}
	var shape={"exterior":PackedVector2Array([Vector2(-1000,-1000),Vector2(1000,-1000),Vector2(1000,1000),Vector2(-1000,1000)]),"holes":[]}
	var categorical_before=ContentRegistry.fingerprint(map)
	abstract.build(map,[shape],[])
	verify(abstract.contours.is_empty() and not abstract.diagnostics.generated_continental_contours,"continental_category_bands_never_become_false_surveyed_contours")
	verify(ContentRegistry.fingerprint(map)==categorical_before,"continental_relief_preserves_all_source_cells")
	verify(not abstract.features.is_empty() and abstract.features.all(func(feature):return (feature.asset_id in data.records or feature.asset_id in MapArtBank.data().get("records",{})) and feature.axis in ["ew","ns"]),"eligible_terrain_uses_directional_relief_sources")
	var culling_equal=true
	for area in [Rect2(-160,-120,230,210),Rect2(-800,-600,1600,1200),Rect2(170,70,40,60),Rect2(3000,3000,20,20)]:
		var brute=abstract.features.filter(func(feature):return area.intersects(feature.footprint))
		culling_equal=culling_equal and ContentRegistry.fingerprint(brute)==ContentRegistry.fingerprint(abstract.visible_features(area))
	verify(culling_equal,"spatial_relief_queries_equal_brute_force_with_identical_depth_order")
	var report={"passed":failures.is_empty(),"failed":failures.size(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"scope":"Physical-slope lighting, source-derived symbolic crest direction, full immutable texture anchoring; not full historical geography or commercial art approval."}
	var file=FileAccess.open("res://reports/relief_surface_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("RELIEF_SURFACE_TEST ",JSON.stringify(report));quit(0 if failures.is_empty() else 1)
