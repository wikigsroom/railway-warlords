extends SceneTree

const Borders = preload("res://presentation/map_control_borders.gd")
var checks: Array = []
var failures: Array = []

func _init() -> void: run.call_deferred()

func verify(value: bool, name: String) -> void:
	checks.append({"name": name, "passed": value})
	if not value: failures.append(name); push_error(name)

func run() -> void:
	var content = ContentRegistry.new()
	verify(content.load_all(), "production_content_loads")
	var atlas = Borders.data()
	var whole = Rect2(-100000, -100000, 200000, 200000)
	for map_id in ["jingfeng", "jingjin", "conquest_china", "hankou", "ningpu"]:
		var before = ContentRegistry.fingerprint(content.maps[map_id])
		for year in ["1920", "1922", "1924"]:
			var graph = Borders.new(); graph.prepare(map_id, year)
			verify(graph.facts().enabled and not graph.records.is_empty(), "source_bound_graph_loads:" + map_id + ":" + year)
			var owners = {}
			for edge in graph.records: owners[edge.city_a] = "unified"; owners[edge.city_b] = "unified"
			verify(graph.visible(owners, whole).is_empty(), "friendly_internal_subdivisions_have_no_political_strokes:" + map_id + ":" + year)
			verify(graph.facts().same_owner_pairs_suppressed == graph.records.size(), "all_friendly_pairs_are_suppressed:" + map_id + ":" + year)
			var city = str(graph.records[0].city_a)
			owners[city] = "opposing"
			var hostile = graph.visible(owners, whole)
			verify(not hostile.is_empty() and hostile.all(func(row): return row.owner_a != row.owner_b), "capture_creates_only_hostile_common_edges:" + map_id + ":" + year)
			verify(graph.visible(owners, Rect2(-90000, -90000, 1, 1)).is_empty(), "offscreen_boundary_segments_are_culled:" + map_id + ":" + year)
			owners[city] = "unified"
			verify(graph.visible(owners, whole).is_empty(), "owner_change_back_removes_stale_hostile_edges:" + map_id + ":" + year)
			owners.erase(city)
			verify(graph.visible(owners, whole).is_empty() and graph.facts().unassigned_pairs_suppressed > 0, "unknown_owners_do_not_invent_political_edges:" + map_id + ":" + year)
			verify(owners.size() > 0 and graph.visible({}, whole).is_empty(), "unassigned_map_has_no_strokes:" + map_id + ":" + year)
		verify(ContentRegistry.fingerprint(content.maps[map_id]) == before, "border_preparation_does_not_mutate_map_or_fill_geometry:" + map_id)
	var absent = Borders.new(); absent.prepare("unsupported_map", "1924")
	verify(not absent.facts().enabled and absent.visible({}, whole).is_empty(), "unsupported_geography_has_no_fabricated_fallback")
	var missing_year = Borders.new(); missing_year.prepare("jingfeng", "1840")
	verify(not missing_year.facts().enabled, "missing_historical_period_is_not_silently_relabelled")
	var saved_hash = atlas.maps.jingfeng.map_sha256
	atlas.maps.jingfeng.map_sha256 = "invalid_test_identity"
	var stale = Borders.new(); stale.prepare("jingfeng", "1924")
	verify(not stale.facts().enabled and stale.facts().get("disabled_reason", "") == "source_hash_mismatch", "stale_geometry_binding_is_rejected")
	atlas.maps.jingfeng.map_sha256 = saved_hash
	verify(HexGrid.RADIUS == 48 and MapView.TERRITORY_OPACITY == .26 and MapView.TERRITORY_FIELD_OPACITY == .21,
		"operation_hex_and_translucent_control_fill_are_preserved")
	var output = ""
	var args = OS.get_cmdline_user_args()
	for i in range(args.size() - 1):
		if args[i] == "--output": output = args[i + 1]
	var report = {"passed": failures.is_empty(), "checks": checks, "failures": failures,
		"graph_sha256": FileAccess.get_sha256(Borders.PATH), "shipping_exe": false, "physical_android_device_tested": false}
	if not output.is_empty():
		var file = FileAccess.open(output.path_join("validation.json"), FileAccess.WRITE)
		file.store_string(JSON.stringify(report, "\t")); file.close()
	print("CONTROL_BORDERS_TEST ", JSON.stringify({"passed": failures.is_empty(), "checks": checks.size(), "failures": failures}))
	quit(0 if failures.is_empty() else 1)
