class_name GeographicReliefField
extends RefCounted

# A numerical scientific height table, never a generated/repainted art raster.
# Reuse the precise land triangles, including islands and existing water holes;
# lighting coverage must not depend on neighbouring coarse operation hexes.
const PATH="res://presentation/data/asia_presentation_dem.json"
const DATA_SHA256="4f6b4ba758715300e1793b22a28b2d41f1849f8bd618efbf518e5cfc680d7e3d"
const UV_MARKER=4096.0
var mesh: ArrayMesh
var image: Image
var texture: ImageTexture
var dimensions=Vector2i.ZERO
var bounds=Rect2()
var world_origin=Vector2.ZERO
var world_extent=Vector2.ONE
var step_degrees=0.0
var diagnostics: Dictionary={"active":false}

func build(map: Dictionary, source_land: ArrayMesh) -> void:
	mesh=null;image=null;texture=null;dimensions=Vector2i.ZERO;diagnostics={"active":false}
	if str(map.get("id",""))!="asia_strategic" or source_land==null:return
	if map.get("projection","")!="equirectangular_lonlat_hex_axial" or not FileAccess.file_exists(PATH):return
	var started=Time.get_ticks_usec()
	if FileAccess.get_sha256(PATH)!=DATA_SHA256:
		push_error("Numerical geographic relief source checksum mismatch");return
	var data=JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if not data is Dictionary or data.get("format",0)!=1 or data.get("map_id","")!="asia_strategic":return
	# ContentRegistry integerizes whole numeric values in the playable map.
	# Array equality distinguishes int/float elements; compare physical values.
	if data.geographic_bounds.size()!=4 or map.geographic_bounds.size()!=4:return
	for i in range(4):
		if not is_equal_approx(float(data.geographic_bounds[i]),float(map.geographic_bounds[i])):return
	dimensions=Vector2i(data.dimensions[0],data.dimensions[1]);step_degrees=float(data.step_degrees)
	var box: Array=data.geographic_bounds
	bounds=Rect2(float(box[0]),float(box[1]),float(box[2])-float(box[0]),float(box[3])-float(box[1]))
	if dimensions!=Vector2i(roundi(bounds.size.x/step_degrees)+1,roundi(bounds.size.y/step_degrees)+1):return
	if data.encoding!="gzip_base64_signed_int16_big_endian_metres" or int(data.nodata_samples)!=0:return
	var bytes=Marshalls.base64_to_raw(data.data_base64).decompress(int(data.uncompressed_bytes),FileAccess.COMPRESSION_GZIP)
	if bytes.size()!=dimensions.x*dimensions.y*2:return
	var hashing=HashingContext.new();hashing.start(HashingContext.HASH_SHA256);hashing.update(bytes)
	if hashing.finish().hex_encode()!=data.payload_sha256:
		push_error("Numerical geographic relief payload checksum mismatch");return
	# Bias the signed integer in runtime memory before hardware interpolation.
	# Interpolating signed two's-complement bytes directly would invent enormous
	# ridges where a real coastal height crosses zero. Source bytes stay intact.
	for offset in range(0,bytes.size(),2):bytes[offset]=bytes[offset]^128
	image=Image.create_from_data(dimensions.x,dimensions.y,false,Image.FORMAT_RG8,bytes)
	if DisplayServer.get_name()!="headless":texture=ImageTexture.create_from_image(image)
	world_origin=Vector2.ZERO
	world_extent=Vector2(bounds.size.x/float(map.longitude_step_deg)*72.0,bounds.size.y/float(map.latitude_step_deg)*sqrt(3.0)*48.0)
	mesh=ArrayMesh.new()
	var vertices=0;var triangles=0
	for surface in range(source_land.get_surface_count()):
		var arrays=source_land.surface_get_arrays(surface)
		var points: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		var uvs=PackedVector2Array();uvs.resize(points.size());uvs.fill(Vector2(0,UV_MARKER))
		var colors=PackedColorArray();colors.resize(points.size());colors.fill(Color.WHITE)
		arrays[Mesh.ARRAY_TEX_UV]=uvs;arrays[Mesh.ARRAY_COLOR]=colors
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
		vertices+=points.size();triangles+=indices.size()/3 if not indices.is_empty() else points.size()/3
	diagnostics={"active":true,"source_id":data.source_id,"source_zoom":data.source_zoom,"data_sha256":DATA_SHA256,
		"payload_sha256":data.payload_sha256,"dimensions":[dimensions.x,dimensions.y],"node_samples":dimensions.x*dimensions.y,
		"source_projected_pixel_size_m":data.source_projected_pixel_size_m,"step_degrees":step_degrees,
		"source_rounding_error_m":data.maximum_rounding_error_m,"gpu_lookup_bytes":dimensions.x*dimensions.y*2,
		"gpu_encoding":"RG8_signed_metres_biased_by_32768_before_linear_interpolation","nodata_samples":0,
		"land_vertices":vertices,"land_triangles":triangles,"land_topology_reused":true,
		"depends_on_three_land_hexes":false,"clipped_to_source_land_and_existing_water_holes":true,
		"preparation_ms":(Time.get_ticks_usec()-started)/1000.0,"historical_landcover_claimed":false,
		"exact_summit_heights_claimed":false,"rules_map_mutated":false,"raster_art_generated":false}

func bind_to(material: ShaderMaterial, enabled: bool=true) -> void:
	if material==null:return
	material.set_shader_parameter("geographic_relief_enabled",enabled and texture!=null and mesh!=null)
	if texture==null:return
	material.set_shader_parameter("geographic_heights",texture)
	material.set_shader_parameter("geographic_dimensions",Vector2(dimensions))
	material.set_shader_parameter("geographic_world_origin",world_origin)
	material.set_shader_parameter("geographic_world_extent",world_extent)
	material.set_shader_parameter("geographic_bounds",Vector4(bounds.position.x,bounds.position.y,bounds.end.x,bounds.end.y))

func elevation_node(x: int,y: int) -> float:
	if image==null or x<0 or y<0 or x>=dimensions.x or y>=dimensions.y:return NAN
	var value=image.get_pixel(x,y)
	return roundf(value.r*255.0)*256.0+roundf(value.g*255.0)-32768.0

func world_to_uv(point: Vector2) -> Vector2:
	# Node table endpoints are texel centres, not the outer texture edges.
	var fraction=(point-world_origin)/world_extent
	return (fraction*Vector2(dimensions-Vector2i.ONE)+Vector2(.5,.5))/Vector2(dimensions)

func facts() -> Dictionary:
	var result=diagnostics.duplicate(true)
	result["gpu_texture_available"]=texture!=null
	return result
