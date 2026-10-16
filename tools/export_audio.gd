extends SceneTree

func _init() -> void:
	DirAccess.make_dir_recursive_absolute("res://assets/audio/sfx");DirAccess.make_dir_recursive_absolute("res://assets/audio/music")
	for id in GameAudio.SFX:
		var stream=GameAudio.make_sfx(id);var result=stream.save_to_wav("res://assets/audio/sfx/%s.wav"%id)
		if result!=OK:push_error("Audio export failed: "+id);quit(1);return
	for id in ["campaign","battle","victory"]:
		var stream=GameAudio.make_music(id);stream.save_to_wav("res://assets/audio/music/%s.wav"%id)
	print("Generated ",GameAudio.SFX.size()," distinct sound effects and 3 original 16-second music loops.");quit()
