class_name GeographicGroundField
extends RefCounted

# Categorical scientific reference data. The GPU samples complete immutable
# Sub2 originals; no derived artwork, atlas, crop or recoloured PNG is saved.
const PATH="res://presentation/data/asia_ground_regions.json"
const DATA_SHA256="50a866840af44c12cd80f5f9cff8099c816f7295a1ac907e0d95757355bd53cd"
const UV_MARKER=8192.0
var mesh: ArrayMesh
var image: Image
var texture: ImageTexture
var weight_images: Array[Image]=[]
var weight_texture: Texture2DArray
var weight_dimensions=Vector2i.ZERO
var dimensions=Vector2i.ZERO
var diagnostics: Dictionary={"active":false}

func build(map: Dictionary, source_land: ArrayMesh) -> void:
	mesh=null;image=null;texture=null;dimensions=Vector2i.ZERO;diagnostics={"active":false}
	weight_images.clear();weight_texture=null;weight_dimensions=Vector2i.ZERO
	if str(map.get("id",""))!="asia_strategic" or source_land==null or not FileAccess.file_exists(PATH):return
	if map.get("projection","")!="equirectangular_lonlat_hex_axial" or FileAccess.get_sha256(PATH)!=DATA_SHA256:return
	var data=JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if not data is Dictionary or data.get("format",0)!=1 or data.get("map_id","")!="asia_strategic":return
	for i in range(4):
		if not is_equal_approx(float(data.geographic_bounds[i]),float(map.geographic_bounds[i])):return
	var families=GroundMaterialBlend.source_layers().keys()
	if families!=data.family_names:return
	dimensions=Vector2i(data.dimensions[0],data.dimensions[1])
	if dimensions!=Vector2i(1601,901) or not is_equal_approx(float(data.step_degrees),.1):return
	var bytes=Marshalls.base64_to_raw(data.data_base64).decompress(int(data.uncompressed_bytes),FileAccess.COMPRESSION_GZIP)
	if bytes.size()!=dimensions.x*dimensions.y:return
	var context=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(bytes)
	if context.finish().hex_encode()!=data.payload_sha256:
		push_error("Geographic material lookup checksum mismatch");return
	for value in bytes:
		if value>families.size():push_error("Invalid geographic material family");return
	image=Image.create_from_data(dimensions.x,dimensions.y,false,Image.FORMAT_R8,bytes)
	if DisplayServer.get_name()!="headless":texture=ImageTexture.create_from_image(image)
	weight_dimensions=Vector2i(data.weights_dimensions[0],data.weights_dimensions[1])
	if weight_dimensions!=Vector2i(801,451) or int(data.weights_layers)!=20:return
	var weights=Marshalls.base64_to_raw(data.weights_data_base64).decompress(int(data.weights_uncompressed_bytes),FileAccess.COMPRESSION_GZIP)
	var stride=weight_dimensions.x*weight_dimensions.y
	if weights.size()!=stride*20:return
	context.start(HashingContext.HASH_SHA256);context.update(weights)
	if context.finish().hex_encode()!=data.weights_payload_sha256:
		push_error("Geographic material weights checksum mismatch");return
	for layer in range(20):weight_images.append(Image.create_from_data(weight_dimensions.x,weight_dimensions.y,false,Image.FORMAT_R8,weights.slice(layer*stride,(layer+1)*stride)))
	if DisplayServer.get_name()!="headless":
		weight_texture=Texture2DArray.new()
		if weight_texture.create_from_images(weight_images)!=OK:weight_texture=null;return
	mesh=ArrayMesh.new()
	for surface in range(source_land.get_surface_count()):
		var arrays=source_land.surface_get_arrays(surface)
		var points: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var uvs=PackedVector2Array();uvs.resize(points.size());uvs.fill(Vector2(0,UV_MARKER))
		var colors=PackedColorArray();colors.resize(points.size());colors.fill(Color.WHITE)
		arrays[Mesh.ARRAY_TEX_UV]=uvs;arrays[Mesh.ARRAY_COLOR]=colors
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	diagnostics={"active":true,"data_sha256":FileAccess.get_sha256(PATH),"payload_sha256":data.payload_sha256,
		"dimensions":[dimensions.x,dimensions.y],"step_degrees":data.step_degrees,"nodes":dimensions.x*dimensions.y,
		"source_year":2017,"source_id":data.source_id,"source_land_topology_reused":true,
		"historical_landuse_survey":false,"trees_or_water_added":false,"rule_cells_changed":false,
		"numeric_lookup_gpu_bytes":bytes.size(),"source_pngs_modified":false,"operation_hex_radius":HexGrid.RADIUS}
	diagnostics["weight_dimensions"]=[weight_dimensions.x,weight_dimensions.y]
	diagnostics["weight_layers"]=weight_images.size()
	diagnostics["weight_lookup_gpu_bytes"]=weights.size()
	diagnostics["transition_sigma_degrees"]=data.transition_sigma_degrees
	diagnostics["transition_width_is_illustrative"]=true
	diagnostics["weights_payload_sha256"]=data.weights_payload_sha256

func bind_to(material: ShaderMaterial) -> void:
	if material==null:return
	material.set_shader_parameter("geographic_ground_enabled",texture!=null and mesh!=null and weight_texture!=null)
	if texture==null or weight_texture==null:return
	material.set_shader_parameter("geographic_ground_regions",texture)
	material.set_shader_parameter("geographic_ground_dimensions",Vector2(dimensions))
	material.set_shader_parameter("geographic_ground_weights",weight_texture)
	material.set_shader_parameter("geographic_weight_dimensions",Vector2(weight_dimensions))
	material.set_shader_parameter("geographic_rock_layer",GroundMaterialBlend.source_layers().get("weathered_rock",0))
	material.set_shader_parameter("geographic_scree_layer",GroundMaterialBlend.source_layers().get("alpine_scree",0))

func facts() -> Dictionary:
	var result=diagnostics.duplicate(true)
	result["gpu_texture_available"]=texture!=null
	result["gpu_weights_available"]=weight_texture!=null
	return result
