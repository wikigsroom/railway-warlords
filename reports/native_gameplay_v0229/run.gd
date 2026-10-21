extends SceneTree
const Driver=preload("res://reports/native_movie_driver_v0229/attempt_04/visual_playtest.gd")
func _initialize() -> void:
	start.call_deferred()
func start() -> void:
	var app=load("res://app/main.tscn").instantiate()
	root.add_child(app)
	await process_frame
	await Driver.run(app)
