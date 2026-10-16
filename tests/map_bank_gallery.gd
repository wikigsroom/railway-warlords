extends SceneTree

# Internal native review viewport. Each card displays one entire unmodified
# source; the screenshot is a raw Godot UI capture, never a stitched concept.
func _init() -> void:run.call_deferred()

func argument(name: String, fallback: String="") -> String:
	var args=OS.get_cmdline_user_args();var index=args.find(name)
	return args[index+1] if index>=0 and index+1<args.size() else fallback

func run() -> void:
	var project_root=ProjectSettings.globalize_path("res://").path_join("../../").simplify_path()
	var originals: Array=[]
	for name in ["map_bank_generation.json","map_settlement_extension_generation.json","map_surface_extension_generation.json"]:
		var path="res://reports/"+name
		if not FileAccess.file_exists(path):continue
		var report=JSON.parse_string(FileAccess.get_file_as_string(path))
		if report is Dictionary:originals.append_array(report.get("assets",[]))
	var family=argument("--family");var category=argument("--category")
	var rows: Array=originals.filter(func(row):return (family.is_empty() or row.family==family) and (category.is_empty() or row.category==category))
	rows.sort_custom(func(a,b):return a.id<b.id)
	var page=maxi(0,int(argument("--page","0")));var per_page=18
	var selected=rows.slice(page*per_page,mini((page+1)*per_page,rows.size()))
	var background=ColorRect.new();background.color=Color("202b2d");background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(background)
	var margin=MarginContainer.new();margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+side,20)
	root.add_child(margin);var column=VBoxContainer.new();margin.add_child(column)
	var font=load("res://assets/font/SourceHanSansSC-Regular.otf")
	var heading=Label.new();heading.text="地图原始素材检查 · "+(family if not family.is_empty() else category)+" · %d/%d"%[page+1,maxi(1,ceili(float(rows.size())/per_page))]
	heading.add_theme_font_override("font",font);heading.add_theme_font_size_override("font_size",26);column.add_child(heading)
	var note=Label.new();note.text="每格为一张完整 Sub2 源图；本页是 Godot 原生检查界面，正式美术批准另行记录。"
	note.add_theme_font_override("font",font);note.add_theme_font_size_override("font_size",17);column.add_child(note)
	var grid=GridContainer.new();grid.columns=6;grid.size_flags_vertical=Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation",10);grid.add_theme_constant_override("v_separation",10);column.add_child(grid)
	for row in selected:
		var card=PanelContainer.new();card.custom_minimum_size=Vector2(300,320);card.size_flags_horizontal=Control.SIZE_EXPAND_FILL;card.size_flags_vertical=Control.SIZE_EXPAND_FILL
		var style=StyleBoxFlat.new();style.bg_color=Color("9ba67d");style.border_color=Color("718373")
		style.set_border_width_all(1);style.set_content_margin_all(8);card.add_theme_stylebox_override("panel",style);grid.add_child(card)
		var stack=VBoxContainer.new();card.add_child(stack)
		var label=Label.new();label.text=row.id;label.clip_text=true;label.add_theme_font_size_override("font_size",13);label.add_theme_color_override("font_color",Color("24392f"));stack.add_child(label)
		var texture=ImageTexture.create_from_image(Image.load_from_file(project_root.path_join(row.source_file)))
		var image=TextureRect.new();image.texture=texture;image.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;image.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		image.custom_minimum_size=Vector2(276,268);image.size_flags_vertical=Control.SIZE_EXPAND_FILL;stack.add_child(image)
	for frame in range(12):await process_frame
	await RenderingServer.frame_post_draw
	var output=argument("--capture-path",ProjectSettings.globalize_path("res://reports/screenshots/map_bank/gallery.png"))
	DirAccess.make_dir_recursive_absolute(output.get_base_dir())
	var error=root.get_texture().get_image().save_png(output)
	var metadata={"passed":error==OK and not selected.is_empty(),"raw_godot_viewport":true,"full_source_textures":true,"manual_raster_compositing":false,"build_version":ContentRegistry.APP_VERSION,"family":family,"category":category,"page":page,"source_count":selected.size(),"available_sources":rows.size(),"sources":selected.map(func(row):return {"id":row.id,"source_file":row.source_file,"source_sha256":row.source_sha256}),"formal_art_approval":false}
	var file=FileAccess.open(output.get_basename()+".json",FileAccess.WRITE);file.store_string(JSON.stringify(metadata,"\t"));file.close()
	print("MAP_BANK_GALLERY ",JSON.stringify(metadata));quit(0 if metadata.passed else 1)
