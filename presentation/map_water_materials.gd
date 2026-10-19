class_name MapWaterMaterials
extends RefCounted

# Whole immutable Sub2 originals. Existing marine/inland meshes decide extent;
# these IDs describe display materials, never salinity, depth or history.
const SEA_ID="tile_water_sea_v0227"
const RIVER_ID="tile_water_river_v0227"
const INLAND_ID="tile_water_inland_v0227"
const IDS=[SEA_ID,RIVER_ID,INLAND_ID]
const UV_MARKER=4096.0

static func mesh(source: ArrayMesh) -> ArrayMesh:
	if source==null:return null
	# Only UV metadata changes. No vertex, index, color, geographic boundary,
	# source image or source-resource array is modified.
	var result=ArrayMesh.new()
	for surface in range(source.get_surface_count()):
		var arrays=source.surface_get_arrays(surface)
		var uv: PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV].duplicate()
		for index in range(uv.size()):uv[index].x+=UV_MARKER
		arrays[Mesh.ARRAY_TEX_UV]=uv
		result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return result

static func facts() -> Dictionary:
	return {"sea_texture_id":SEA_ID,"river_texture_id":RIVER_ID,"inland_texture_id":INLAND_ID,
		"independent_originals":IDS.size(),"world_texture_period":256.0,
		"source_sampling":"world_anchored_mirrored_three_translations_with_explicit_mip_gradients_and_distance_filter",
		"fixed_wallpaper_period":false,
		"geographic_water_extent_changed":false,"historical_water_color_claimed":false,
		"source_images_modified":false,"legacy_per_cell_water_stamps":false}
