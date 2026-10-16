class_name ReliefShadeField
extends RefCounted

# Numerical GPU lookup data, not a painted or generated art asset. Values are
# premultiplied source-cell lighting; unsupported land/water stays transparent.
# No new DEM samples, terrain categories, source images or files are produced.
const UV_MARKER=512.0
var origin_hex=Vector2i.ZERO
var dimensions=Vector2i.ZERO
var image: Image
var texture: ImageTexture
var source_count=0

func build(cells: Dictionary, shades: Dictionary) -> void:
	image=null;texture=null;source_count=0;dimensions=Vector2i.ZERO
	var low=Vector2i(2147483647,2147483647);var high=-low
	for key in cells:
		var cell: Dictionary=cells[key]
		if not shades.has(cell.id):continue
		var hex=HexGrid.coordinate(cell.position)
		low=Vector2i(mini(low.x,hex.x),mini(low.y,hex.y));high=Vector2i(maxi(high.x,hex.x),maxi(high.y,hex.y))
	if low.x>high.x:return
	origin_hex=low-Vector2i(2,2);dimensions=high-low+Vector2i(5,5)
	var pixels=PackedByteArray();pixels.resize(dimensions.x*dimensions.y*4);pixels.fill(0)
	for key in cells:
		var cell: Dictionary=cells[key]
		if not shades.has(cell.id):continue
		var at=HexGrid.coordinate(cell.position)-origin_hex;var color: Color=shades[cell.id]
		var offset=(at.y*dimensions.x+at.x)*4
		pixels[offset]=clampi(roundi(color.r*color.a*255),0,255)
		pixels[offset+1]=clampi(roundi(color.g*color.a*255),0,255)
		pixels[offset+2]=clampi(roundi(color.b*color.a*255),0,255)
		pixels[offset+3]=clampi(roundi(color.a*255),0,255);source_count+=1
	image=Image.create_from_data(dimensions.x,dimensions.y,false,Image.FORMAT_RGBA8,pixels)
	if DisplayServer.get_name()!="headless":texture=ImageTexture.create_from_image(image)

func uv(hex: Vector2i) -> Vector2:
	var coordinate=(Vector2(hex-origin_hex)+Vector2(.5,.5))/Vector2(dimensions)
	return Vector2(coordinate.x,UV_MARKER+coordinate.y)

func bind_to(material: ShaderMaterial, enabled: bool=true) -> void:
	if material==null:return
	material.set_shader_parameter("relief_enabled",enabled and texture!=null)
	if texture!=null:
		material.set_shader_parameter("relief_shades",texture)
		material.set_shader_parameter("relief_dimensions",Vector2(dimensions))

func facts() -> Dictionary:
	return {"method":"source_cell_cubic_bspline_lighting","source_samples":source_count,"lookup_dimensions":[dimensions.x,dimensions.y],"lookup_bytes":dimensions.x*dimensions.y*4,"data_texture_format":"RGBA8_premultiplied_numerical_lighting","gpu_texture_available":texture!=null,"new_dem_samples":0,"source_images_modified":false,"raster_art_generated":false,"interpolation_stencil":[4,4],"maximum_contributing_samples":16,"rules_map_mutated":false}
