extends SceneTree

const TerrainVisuals = preload("res://presentation/terrain_visuals.gd")

var checks: Array=[]
var failures: Array=[]

func _init() -> void:
	run.call_deferred()

func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:
		failures.append(name)
		push_error("TERRAIN_VISUALS: "+name)

func run() -> void:
	verify(TerrainVisuals.kind_for_cell({"terrain_id":"forest","natural_terrain_id":"plain"})=="forest","detailed_forest_overrides_natural_plain")
	verify(TerrainVisuals.kind_for_cell({"terrain_id":"city","natural_terrain_id":"plain"})=="city","city_feature_is_preserved")
	verify(TerrainVisuals.kind_for_cell({"terrain_id":"plain","natural_terrain_id":"mountain"})=="mountain","natural_mountain_fallback")
	verify(TerrainVisuals.kind_for_cell({"terrain_id":"sea","natural_terrain_id":"sea"})=="sea","sea_is_continuous_surface")
	var first=TerrainVisuals.tile_id({"id":"stable-cell","terrain_id":"hill"})
	var second=TerrainVisuals.tile_id({"id":"stable-cell","terrain_id":"hill"})
	verify(first==second and first in ["tile_hill_01","tile_hill_02"],"tile_variant_is_deterministic")
	verify(TerrainVisuals.tile_id({"id":"plain","terrain_id":"plain"}).is_empty(),"plain_uses_continuous_surface")
	verify(TerrainVisuals.blend_alpha("hill",true,.16)>0.0 and TerrainVisuals.blend_alpha("hill",true,.60)>TerrainVisuals.blend_alpha("hill",true,.16),"strategic_detail_strength_scales_with_zoom")
	verify(TerrainVisuals.blend_alpha("sea",true,.80)==0.0,"sea_tile_is_not_repeated_over_water_mesh")
	var overview_a=TerrainVisuals.keep_at_overview({"id":"overview-a"},"mountain",true,.28)
	verify(overview_a==TerrainVisuals.keep_at_overview({"id":"overview-a"},"mountain",true,.28),"overview_relief_sampling_is_deterministic")
	verify(TerrainVisuals.keep_at_overview({"id":"feature"},"city",true,.18),"overview_keeps_city_features")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"game_version":ContentRegistry.APP_VERSION,"scope":"Deterministic per-cell terrain texture resolution and zoom-aware blending."}
	var file=FileAccess.open("res://reports/terrain_visual_resolver_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("TERRAIN_VISUAL_RESOLVER_TESTS ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}))
	quit(0 if failures.is_empty() else 1)
