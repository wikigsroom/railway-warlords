extends SceneTree

# Actual imported sources through the production Compatibility shader. These
# synthetic, complete viewport captures are diagnostics, not gameplay artwork.
class Fixture extends Node2D:
	var layer: int = 0
	var dimensions = Vector2(512, 384)
	var pan = Vector2.ZERO
	func _draw() -> void:
		draw_set_transform(dimensions * .5 - pan)
		var rect = Rect2(pan - dimensions * .5, dimensions)
		var points = PackedVector2Array([rect.position, Vector2(rect.end.x, rect.position.y), rect.end, Vector2(rect.position.x, rect.end.y)])
		var color = Color(layer / 255.0, layer / 255.0, layer / 255.0, 1)
		var uv = GroundMaterialBlend.weights(1, 0)
		draw_polygon(points, PackedColorArray([color, color, color, color]), PackedVector2Array([uv, uv, uv, uv]))

var viewport: SubViewport
var fixture: Fixture
var checks: Array = []
var measurements: Array = []
var folder: String
const FAMILIES = ["temperate_meadow", "alluvial_loam", "flood_meadow", "subtropical_humus"]

func _init() -> void:
	run.call_deferred()

func check(value: bool, name: String) -> void:
	checks.append({"name": name, "passed": value})
	if not value: push_error(name)

func frame(enabled: bool) -> Image:
	fixture.material.set_shader_parameter("ground_seam_feather", enabled)
	fixture.queue_redraw()
	viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	for i in range(4): await process_frame
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()

func edge_delta(image: Image, vertical: bool) -> Dictionary:
	var total = 0.0
	var maximum = 0.0
	var count = 0
	var crossing = image.get_width() / 2 if vertical else image.get_height() / 2
	var length = image.get_height() if vertical else image.get_width()
	for along in range(12, length - 12):
		# Omit the crossing of the other repeat boundary: each axis is tested
		# independently, with the corner separately covered by the image.
		if abs(along - length / 2) < 12: continue
		var a = image.get_pixel(crossing - 1, along) if vertical else image.get_pixel(along, crossing - 1)
		var b = image.get_pixel(crossing, along) if vertical else image.get_pixel(along, crossing)
		var delta = maxf(absf(a.r - b.r), maxf(absf(a.g - b.g), absf(a.b - b.b))) * 255.0
		total += delta
		maximum = maxf(maximum, delta)
		count += 1
	return {"mean_channel_delta": total / maxi(1, count), "maximum_channel_delta": maximum, "pixels": count}

func run() -> void:
	var args = OS.get_cmdline_user_args()
	var index = args.find("--output")
	folder = args[index + 1] if index >= 0 and index + 1 < args.size() else "res://reports/ground_hierarchy_v0235/edges"
	DirAccess.make_dir_recursive_absolute(folder)
	check(DisplayServer.get_name() != "headless", "native_gpu_required")
	viewport = SubViewport.new()
	viewport.size = Vector2i(512, 384)
	viewport.disable_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	root.add_child(viewport)
	fixture = Fixture.new()
	fixture.material = GroundMaterialBlend.material(false)
	viewport.add_child(fixture)
	check(fixture.material != null, "production_material_available")
	if fixture.material != null:
		fixture.material.set_shader_parameter("ground_alpha", 1.0)
		fixture.material.set_shader_parameter("ground_stochastic", false)
		for family in FAMILIES:
			fixture.pan = Vector2.ZERO
			fixture.layer = GroundMaterialBlend.source_layers()[family]
			var id = MapTerrainSurfaces.macro_id(family)
			var source = load("res://assets/tile/" + id + ".png") as Texture2D
			var image = source.get_image()
			check(source.get_width() == 384 and source.get_height() == 384 and image.has_mipmaps(), "normal_import_384_mips:" + family)
			var original = await frame(false)
			var adjusted = await frame(true)
			# Independent controls expose an interior line through direct,
			# unfeathered sampling. Retain that natural brush/grain contrast;
			# a seam test must not require every line to become uniformly flat.
			var period = MapTerrainSurfaces.macro_period(family)
			fixture.pan = Vector2(period * .5, 0)
			var interior_x = await frame(false)
			fixture.pan = Vector2(0, period * .5)
			var interior_y = await frame(false)
			var source_hash = FileAccess.get_sha256("res://assets/tile/" + id + ".png")
			for axis in [true, false]:
				var before = edge_delta(original, axis)
				var after = edge_delta(adjusted, axis)
				var interior = edge_delta(interior_x if axis else interior_y, axis)
				measurements.append({"family": family, "axis": "x" if axis else "y", "before": before, "after": after, "independent_interior": interior, "source_sha256": source_hash})
				check(after.mean_channel_delta <= interior.mean_channel_delta + .5 and after.mean_channel_delta < before.mean_channel_delta, "repeat_edge_matches_interior_grain_and_reduces_join:" + family + (":x" if axis else ":y"))
			check(original.save_png(folder + "/" + family + "_before.png") == OK, "before_viewport_saved:" + family)
			check(adjusted.save_png(folder + "/" + family + "_after.png") == OK, "after_viewport_saved:" + family)
		var before_total = 0.0
		var after_total = 0.0
		for row in measurements:
			before_total += row.before.mean_channel_delta * row.before.pixels
			after_total += row.after.mean_channel_delta * row.after.pixels
		check(before_total > 0 and after_total <= before_total * .7, "combined_repeat_edge_gradient_reduced_at_least_30_percent")
	var failures = checks.filter(func(row): return not row.passed)
	var report = {"passed": failures.is_empty(), "checks": checks, "measurements": measurements,
		"build_version": ContentRegistry.APP_VERSION, "development_material_revision": MapTerrainSurfaces.macro_data().material_identity_revision,
		"renderer": RenderingServer.get_current_rendering_method(), "rendering_device": RenderingServer.get_video_adapter_name(),
		"scope": "Native Windows development-engine source-edge fixture; stochastic translations disabled to isolate opposite-edge joins. Both enabled and bypassed modes use the same imported complete originals. Not a shipping executable or gameplay acceptance.",
		"source_images_modified": false, "source_uv_mirrored": false, "physical_android_device_tested": false, "formal_art_approval": false, "ew6_parity_claimed": false}
	var file = FileAccess.open(folder + "/validation.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("GROUND_SOURCE_EDGES_GPU ", JSON.stringify({"passed": failures.is_empty(), "checks": checks.size(), "failures": failures, "measurements": measurements}))
	quit(0 if failures.is_empty() else 1)
