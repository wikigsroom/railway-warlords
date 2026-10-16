class_name GroundMaterialBlend
extends RefCounted

# One runtime texture-array layer per immutable, complete source. No atlas,
# resized image, cropped source or generated raster is written to disk.
static var source_array: Texture2DArray
static var attempted=false
static var layers: Dictionary={}
const WEIGHT_MARKER=1024.0
const CODE="""
shader_type canvas_item;
render_mode unshaded;
uniform sampler2DArray ground_sources : source_color, repeat_enable, filter_linear_mipmap;
uniform float ground_alpha = 0.94;
varying float ground_mode;
varying vec3 ground_layers;
varying vec3 ground_weights;
varying vec2 ground_uv;
varying float ground_coverage;
void vertex() {
    ground_mode = UV.y < -1023.0 ? 1.0 : 0.0;
    if (ground_mode > 0.5) {
        ground_layers = floor(COLOR.rgb * 255.0 + vec3(0.5));
        ground_weights = vec3(UV.x, -UV.y - 1024.0, 1.0 - UV.x + UV.y + 1024.0);
        ground_uv = VERTEX / 384.0;
        ground_coverage = COLOR.a;
    }
}
void fragment() {
    if (ground_mode > 0.5) {
        vec3 weights = clamp(ground_weights, vec3(0.0), vec3(1.0));
        weights = weights * weights * (vec3(3.0) - 2.0 * weights);
        weights /= max(dot(weights, vec3(1.0)), 0.0001);
        vec3 pigment = texture(ground_sources, vec3(ground_uv, ground_layers.x)).rgb;
        if (ground_layers.x != ground_layers.y || ground_layers.x != ground_layers.z) {
            pigment = pigment * weights.x
                + texture(ground_sources, vec3(ground_uv, ground_layers.y)).rgb * weights.y
                + texture(ground_sources, vec3(ground_uv, ground_layers.z)).rgb * weights.z;
        }
        COLOR = vec4(pigment, ground_alpha * ground_coverage);
    }
}
"""

static func source_layers() -> Dictionary:
	if layers.is_empty():
		var families=MapTerrainSurfaces.macro_data().get("records",{}).keys();families.sort()
		for index in range(families.size()):layers[families[index]]=index
	return layers

static func material(strategic: bool) -> ShaderMaterial:
	if DisplayServer.get_name()=="headless":return null
	if not attempted:
		attempted=true
		var images: Array[Image]=[]
		for family in source_layers():
			var id=MapTerrainSurfaces.macro_id(family)
			var texture=ResourceLoader.load("res://assets/tile/"+id+".png","Texture2D",ResourceLoader.CACHE_MODE_IGNORE) as Texture2D
			if texture==null:return null
			var image=texture.get_image()
			if image==null:return null
			if image.is_compressed() and image.decompress()!=OK:return null
			image.convert(Image.FORMAT_RGBA8)
			if not image.has_mipmaps():image.generate_mipmaps()
			images.append(image)
		var array=Texture2DArray.new()
		if array.create_from_images(images)!=OK:return null
		source_array=array
	if source_array==null:return null
	var shader=Shader.new();shader.code=CODE
	var result=ShaderMaterial.new();result.shader=shader
	result.set_shader_parameter("ground_sources",source_array)
	result.set_shader_parameter("ground_alpha",MapTerrainSurfaces.alpha_for("temperate_meadow",strategic))
	return result

static func weights(a: float, b: float) -> Vector2:
	return Vector2(a,-WEIGHT_MARKER-b)
