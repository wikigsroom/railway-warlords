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
uniform float ground_repeat_period = 224.0;
uniform bool ground_stochastic = true;
uniform bool relief_enabled = false;
uniform sampler2D relief_shades : repeat_disable, filter_linear;
uniform vec2 relief_dimensions = vec2(1.0);
varying float relief_mode;
varying vec2 relief_uv;
varying float ground_mode;
varying vec3 ground_layers;
varying vec3 ground_weights;
varying vec2 ground_uv;
varying float ground_coverage;
varying float scenery_mode;
varying vec2 scenery_foot;
void vertex() {
    relief_mode = UV.y >= 512.0 && UV.y <= 513.0 ? 1.0 : 0.0;
    relief_uv = vec2(UV.x, UV.y - 512.0);
    ground_mode = UV.y < -1023.0 ? 1.0 : 0.0;
    scenery_mode = UV.y >= 2048.0 && UV.y <= 2049.0 ? 1.0 : 0.0;
    if (scenery_mode > 0.5) {
        scenery_foot = COLOR.rg;
        COLOR = vec4(1.0, 1.0, 0.98, COLOR.a);
        UV.y -= 2048.0;
    }
    if (ground_mode > 0.5) {
        ground_layers = floor(COLOR.rgb * 255.0 + vec3(0.5));
        ground_weights = vec3(UV.x, -UV.y - 1024.0, 1.0 - UV.x + UV.y + 1024.0);
        ground_uv = VERTEX / ground_repeat_period;
        ground_coverage = COLOR.a;
    }
}
vec2 ground_offset(vec2 vertex, float layer) {
    vec2 key = vec2(dot(vertex, vec2(127.1, 311.7)), dot(vertex, vec2(269.5, 183.3)));
    return fract(sin(key + vec2(layer * 19.19)) * 43758.5453);
}
// Three translated whole-source samples share a world-anchored triangular
// lattice. Their smooth weights remove a fixed wallpaper period; no texture
// is painted, rotated, cut into an atlas or saved as a derived raster.
vec3 ground_pigment(vec2 uv, float layer) {
    vec2 dx = dFdx(uv);
    vec2 dy = dFdy(uv);
    if (!ground_stochastic) {
        return textureGrad(ground_sources, vec3(uv, layer), dx, dy).rgb;
    }
    vec2 lattice = vec2(uv.x - uv.y * 0.57735027, uv.y * 1.15470054) * 0.35;
    vec2 cell = floor(lattice);
    vec2 f = fract(lattice);
    float upper = step(1.0, f.x + f.y);
    vec2 a = cell + vec2(upper);
    vec2 b = cell + vec2(1.0, 0.0);
    vec2 c = cell + vec2(0.0, 1.0);
    vec3 weights = mix(vec3(1.0 - f.x - f.y, f.x, f.y),
        vec3(f.x + f.y - 1.0, 1.0 - f.y, 1.0 - f.x), upper);
    weights = clamp(weights, vec3(0.0), vec3(1.0));
    weights = weights * weights * (vec3(3.0) - 2.0 * weights);
    weights /= max(dot(weights, vec3(1.0)), 0.0001);
    return textureGrad(ground_sources, vec3(uv + ground_offset(a, layer), layer), dx, dy).rgb * weights.x
        + textureGrad(ground_sources, vec3(uv + ground_offset(b, layer), layer), dx, dy).rgb * weights.y
        + textureGrad(ground_sources, vec3(uv + ground_offset(c, layer), layer), dx, dy).rgb * weights.z;
}
// Four bilinear fetches evaluate the sixteen positive cubic B-spline weights.
// World/axial UVs are affine across the entire source mesh: its triangle edges
// cannot introduce a different lighting function or camera-dependent phase.
vec4 continuous_relief(vec2 uv) {
    vec2 p = uv * relief_dimensions - vec2(0.5);
    vec2 base = floor(p);
    vec2 f = fract(p);
    vec2 w0 = pow(vec2(1.0) - f, vec2(3.0)) / 6.0;
    vec2 w1 = (3.0 * f*f*f - 6.0 * f*f + vec2(4.0)) / 6.0;
    vec2 w2 = (-3.0 * f*f*f + 3.0 * f*f + 3.0 * f + vec2(1.0)) / 6.0;
    vec2 w3 = f*f*f / 6.0;
    vec2 g0 = w0 + w1;
    vec2 g1 = w2 + w3;
    vec2 a = (base - vec2(1.0) + w1/g0 + vec2(0.5)) / relief_dimensions;
    vec2 b = (base + vec2(1.0) + w3/g1 + vec2(0.5)) / relief_dimensions;
    return texture(relief_shades, a) * g0.x * g0.y
        + texture(relief_shades, vec2(b.x, a.y)) * g1.x * g0.y
        + texture(relief_shades, vec2(a.x, b.y)) * g0.x * g1.y
        + texture(relief_shades, b) * g1.x * g1.y;
}
void fragment() {
    if (relief_mode > 0.5 && relief_enabled) {
        vec4 shade = continuous_relief(relief_uv);
        COLOR = vec4(shade.rgb / max(shade.a, 0.0001), shade.a);
    } else if (ground_mode > 0.5) {
        vec3 weights = clamp(ground_weights, vec3(0.0), vec3(1.0));
        weights = weights * weights * (vec3(3.0) - 2.0 * weights);
        weights /= max(dot(weights, vec3(1.0)), 0.0001);
        vec3 pigment = ground_pigment(ground_uv, ground_layers.x);
        if (ground_layers.x != ground_layers.y || ground_layers.x != ground_layers.z) {
            pigment = pigment * weights.x
                + ground_pigment(ground_uv, ground_layers.y) * weights.y
                + ground_pigment(ground_uv, ground_layers.z) * weights.z;
        }
        COLOR = vec4(pigment, ground_alpha * ground_coverage);
    } else if (scenery_mode > 0.5) {
        COLOR.a *= 1.0 - smoothstep(scenery_foot.x, scenery_foot.y, UV.y);
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
	result.set_shader_parameter("ground_repeat_period",float(MapTerrainSurfaces.macro_data().get("world_repeat_period",224)))
	result.set_shader_parameter("ground_alpha",MapTerrainSurfaces.alpha_for("temperate_meadow",strategic))
	return result

static func weights(a: float, b: float) -> Vector2:
	return Vector2(a,-WEIGHT_MARKER-b)

static func draw_grounded_feature(canvas: CanvasItem, source: Texture2D, rect: Rect2, id: String, alpha: float) -> bool:
	var row: Dictionary=MapArtBank.data().get("records",{}).get(id,{})
	if row.is_empty():return false
	# Only the lower 12% of the measured opaque silhouette blends into its
	# existing ground. Source UVs still cover the entire original, with all
	# transparent margins; placement and the reserved full footprint are intact.
	var occupied=row.alpha_bounds;var height=float(row.dimensions[1])
	var end=float(occupied[3])/height
	var start=end-float(occupied[3]-occupied[1])/height*.12
	var tint=Color(start,end,1.0,alpha)
	var points=PackedVector2Array([rect.position,rect.position+Vector2(rect.size.x,0),rect.end,rect.position+Vector2(0,rect.size.y)])
	var uv=PackedVector2Array([Vector2(0,2048),Vector2(1,2048),Vector2(1,2049),Vector2(0,2049)])
	canvas.draw_polygon(points,PackedColorArray([tint,tint,tint,tint]),uv,source)
	return true
