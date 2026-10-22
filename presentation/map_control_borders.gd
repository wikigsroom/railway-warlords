extends RefCounted

const LineIndex = preload("res://presentation/source_line_index.gd")
const PATH = "res://presentation/data/control_border_graph.json"
static var catalog: Dictionary = {}
static var input_hashes: Dictionary = {}
var records: Array = []
var active: Array = []
var previous_owners: Dictionary = {}
var diagnostics: Dictionary = {"enabled": false}

static func data() -> Dictionary:
	if catalog.is_empty() and FileAccess.file_exists(PATH):
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(PATH))
		if parsed is Dictionary: catalog = parsed
	return catalog

static func matches(path: String, expected: String) -> bool:
	if not input_hashes.has(path): input_hashes[path] = FileAccess.get_sha256("res://" + path)
	return not expected.is_empty() and input_hashes[path] == expected

func prepare(map_id: String, year: String) -> void:
	records.clear(); active.clear(); previous_owners.clear()
	diagnostics = {"enabled": false, "coast_outlines_drawn": 0, "duplicate_pair_strokes": 0,
		"different_owner_pairs": 0, "same_owner_pairs_suppressed": 0, "unassigned_pairs_suppressed": 0}
	var source: Dictionary = data().get("maps", {}).get(map_id, {})
	if source.is_empty(): return
	if not matches("content/maps/" + map_id + ".json", source.get("map_sha256", "")) or not matches(source.get("zone_source_file", ""), source.get("zone_source_sha256", "")):
		diagnostics["disabled_reason"] = "source_hash_mismatch"
		push_warning("Control border graph does not match its source: " + map_id)
		return
	var period: Dictionary = source.get("periods", {}).get(year, {})
	if period.is_empty(): return
	for edge in period.get("edges", []):
		var paths: Array = []
		for raw in edge.lines:
			var points = PackedVector2Array()
			for point in raw: points.append(Vector2(point[0], point[1]))
			paths.append(points)
		var index = LineIndex.new(); index.build(paths)
		records.append({"city_a": edge.city_a, "city_b": edge.city_b, "index": index})
	diagnostics.merge({"enabled": true, "source_map_id": map_id, "source_period": year,
		"source_edge_pairs": records.size(), "historical_military_frontiers_claimed": false,
		"source_geometry_modified": false, "coast_and_frame_excluded": true}, true)

func visible(owners: Dictionary, view: Rect2) -> Array:
	if previous_owners != owners:
		previous_owners = owners.duplicate()
		active.clear()
		var same = 0; var unassigned = 0
		for edge in records:
			var a = str(owners.get(edge.city_a, "")); var b = str(owners.get(edge.city_b, ""))
			if a.is_empty() or b.is_empty(): unassigned += 1; continue
			if a == b: same += 1; continue
			active.append({"owner_a": a, "owner_b": b, "index": edge.index})
		diagnostics.merge({"different_owner_pairs": active.size(), "same_owner_pairs_suppressed": same,
			"unassigned_pairs_suppressed": unassigned}, true)
	var result: Array = []
	for edge in active:
		for points in edge.index.visible(view):
			result.append({"points": points, "owner_a": edge.owner_a, "owner_b": edge.owner_b})
	return result

func facts() -> Dictionary:
	return diagnostics.duplicate()
