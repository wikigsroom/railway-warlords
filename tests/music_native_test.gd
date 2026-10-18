extends SceneTree

func _init() -> void:run.call_deferred()
func run() -> void:
	var app=load("res://app/main.tscn").instantiate();root.add_child(app)
	await process_frame
	await MusicPlaybackQA.run(app)
