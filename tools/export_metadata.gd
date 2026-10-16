extends SceneTree

func store_if_changed(path: String, text: String) -> bool:
	if FileAccess.file_exists(path) and FileAccess.get_file_as_string(path)==text:return true
	var file=FileAccess.open(path,FileAccess.WRITE)
	if file==null:push_error("Cannot write public metadata: "+path);return false
	file.store_string(text);file.close();return true

func _init() -> void:
	DirAccess.make_dir_recursive_absolute("res://assets/legal")
	if not store_if_changed("res://assets/legal/GODOT-LICENSE.txt",Engine.get_license_text()):quit(1);return
	if not store_if_changed("res://assets/legal/GODOT-THIRD-PARTY.json",JSON.stringify({"licenses":Engine.get_license_info(),"copyrights":Engine.get_copyright_info()},"\t")):quit(1);return
	var content=ContentRegistry.new()
	if not content.load_all():quit(1);return
	var file=FileAccess.open("res://reports/sample_state_v2.json",FileAccess.WRITE);file.store_string(JSON.stringify(StateBuilder.create(content,"legion_08","zhili",{}),"\t"));file.close()
	print("LICENSES_AND_RUNTIME_SCHEMA_FIXTURE_EXPORTED");quit()
