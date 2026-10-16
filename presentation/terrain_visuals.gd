class_name TerrainVisuals
extends RefCounted

## Deterministic presentation rules for the authored terrain PNGs.
##
## The authoritative map cell remains the source of truth for movement and
## history. This helper only resolves which existing, immutable visual tile may
## be shown in a cell and how strongly it should be blended with the surveyed
## land/water surface.

const SUPPORTED_KINDS: Array[String] = [
	"city", "ford", "forest", "hill", "mountain", "peak", "plain", "port", "river", "road", "sea", "wetland"
]
const FEATURE_KINDS: Array[String] = ["city", "ford", "port", "river", "road"]

static func kind_for_cell(cell: Dictionary) -> String:
	if cell.is_empty():
		return "plain"
	var detailed := str(cell.get("terrain_id", ""))
	var natural := str(cell.get("natural_terrain_id", detailed))
	# Named historical land-cover landmarks may provide a presentation-only
	# class on an otherwise plain strategic cell. The real rule terrain still
	# wins for roads, cities, rivers and water, so this never changes movement,
	# ownership or combat. The overlay is populated only from the sourced
	# feature catalogue by MapView.prepare_geography().
	var presentation := str(cell.get("presentation_terrain_id", ""))
	if presentation in ["forest", "wetland"] and detailed not in FEATURE_KINDS and detailed != "sea" and natural != "sea":
		return presentation
	# A tactical feature takes precedence over a broad natural class. This keeps
	# roads, fords and cities visible without changing the rule-layer terrain.
	if detailed in FEATURE_KINDS:
		return detailed
	if detailed == "sea" or natural == "sea":
		return "sea"
	if detailed in SUPPORTED_KINDS and detailed != "plain":
		return detailed
	if natural in SUPPORTED_KINDS:
		return natural
	if detailed in SUPPORTED_KINDS:
		return detailed
	return "plain"

static func tile_id(cell: Dictionary) -> String:
	var kind := kind_for_cell(cell)
	if kind in ["plain", "sea"]:
		return ""
	var seed := absi(hash(str(cell.get("id", ""))))
	return "tile_%s_%02d" % [kind, 1 + seed % 2]

static func blend_alpha(kind: String, strategic: bool, zoom: float) -> float:
	if kind in ["plain", "sea"]:
		return 0.0
	var floor_zoom := 0.16 if strategic else 0.30
	var span := 0.38 if strategic else 0.58
	var detail := clampf((zoom - floor_zoom) / span, 0.0, 1.0)
	# The source tiles carry the atlas painting; the alpha is the presentation
	# hierarchy that lets a player distinguish forest, marsh and relief from the
	# surveyed land mesh underneath. Keep the political wash separate so these
	# values never turn a control field into an opaque fill.
	var category_lift: float = float({
		"forest": 0.09,
		"wetland": 0.10,
		"hill": 0.05,
		"mountain": 0.07,
		"peak": 0.10,
		"river": 0.11,
		"road": 0.05,
		"city": 0.10,
		"ford": 0.10,
		"port": 0.10
	}.get(kind, 0.0))
	# Tactical relief sprites provide the large 2.5D silhouette.  Keep the
	# underlying cell texture quieter for hill/mountain/peak so the silhouette,
	# contours and terrain transitions form one depth stack instead of three
	# equally strong copies of the same mountain.
	var detail_gain: float = 0.34 if strategic else 0.42
	if strategic:
		# The strategic atlas already has a continuous land mesh and sparse 2.5D
		# landmark sprites. Keep named forest patches legible without turning each
		# source cell into an opaque dark honeycomb.
		detail_gain=float({"forest":0.20,"wetland":0.18,"hill":0.17,"mountain":0.20,"peak":0.22}.get(kind,detail_gain))
	if not strategic:
		# Tactical relief sprites provide the recognisable 2.5D silhouette. Keep
		# their cell textures quiet enough that a range reads as a connected land
		# form rather than a wall of repeated grey hexes.
		detail_gain=float({"hill":0.22,"mountain":0.18,"peak":0.16}.get(kind,detail_gain))
	var base: float = 0.22 + detail * detail_gain + category_lift
	if kind in FEATURE_KINDS:
		base += 0.04
	return clampf(base, 0.20, 0.76)

static func transition_color(kind: String) -> Color:
	return {
		"city": Color("b79a63"),
		"ford": Color("729c9b"),
		"forest": Color("4c6651"),
		"hill": Color("6e7158"),
		"mountain": Color("4d5c54"),
		"peak": Color("384c49"),
		"port": Color("5b8d94"),
		"river": Color("397c91"),
		"road": Color("987d59"),
		"wetland": Color("657d72"),
		"plain": Color("b0a778"),
		"sea": Color("397083")
	}.get(kind, Color("7d806b"))

static func is_detail_kind(kind: String) -> bool:
	return kind not in ["plain", "sea"]

static func edge_profile(cells: Dictionary, hex: Vector2i, kind: String) -> Dictionary:
	# A terrain tile is a presentation surface, so its silhouette follows the
	# actual six neighbours instead of filling every cell with the same opaque
	# hex.  Empty neighbours are treated as plain fallback; they never create a
	# new rule cell, biome or administrative border.
	var boundary_edges=0
	var boundary_corners=0
	var neighbor_kinds: Array[String]=[]
	for direction in HexGrid.DIRECTIONS:
		var neighbor: Dictionary=cells.get(hex+direction,{})
		var neighbor_kind=kind_for_cell(neighbor)
		neighbor_kinds.append(neighbor_kind)
		if neighbor_kind!=kind:boundary_edges+=1
	for index in range(6):
		var next=(index+1)%6
		if neighbor_kinds[index]!=kind and neighbor_kinds[next]!=kind:boundary_corners+=1
	return {"boundary_edges":boundary_edges,"boundary_corners":boundary_corners,"neighbor_kinds":neighbor_kinds}

static func tile_radius(kind: String, profile: Dictionary, strategic: bool) -> float:
	# Natural relief sits inside the cell and lets the surveyed base show around
	# it.  Cities, roads, fords and rivers keep a fuller footprint because their
	# object must remain selectable/readable at tactical scale.
	var radius=45.8 if kind in FEATURE_KINDS else (44.6 if kind in ["forest","wetland"] else 43.8)
	var edges=int(profile.get("boundary_edges",0))
	var corners=int(profile.get("boundary_corners",0))
	if edges>=4:radius-=1.4
	elif edges>=2:radius-=.8
	if corners>=3:radius-=.45
	if strategic:radius+=.65
	return clampf(radius,40.8,46.4)

static func keep_at_overview(cell: Dictionary, kind: String, strategic: bool, zoom: float) -> bool:
	if not strategic or kind in FEATURE_KINDS:
		return true
	# At continental zoom, one stamp per source cell would turn a mountain
	# corridor into a noisy checkerboard. Keep a deterministic subset of the
	# same source cells; the full set returns at campaign/tactical zoom.
	var divisor := 1
	if zoom < .30:
		divisor=3
	elif zoom < .40:
		divisor=2
	return absi(hash(str(cell.get("id", "")))) % divisor == 0
