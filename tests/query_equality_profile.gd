extends SceneTree

func _init() -> void:run.call_deferred()

func run() -> void:
	var content=ContentRegistry.new()
	if not content.load_all():quit(1);return
	var map=ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	var state=CapacityFixture.create(content,map,"single_faction",4096)
	var copied=StateAccess.clone_transaction(state)
	var rows=[]
	for field in ["units","cities","factions","visibility"]:
		var before=Time.get_ticks_usec();var same=true
		for iteration in range(100):same=same and state[field]==copied[field]
		rows.append({"field":field,"same":same,"equality_ms_per_call":(Time.get_ticks_usec()-before)/100000.0})
	for field in ["rail_edges","crossings"]:
		var before=Time.get_ticks_usec();var same=true
		for iteration in range(100):same=same and state.map[field]==copied.map[field]
		rows.append({"field":field,"same":same,"equality_ms_per_call":(Time.get_ticks_usec()-before)/100000.0})
	var before=Time.get_ticks_usec();var same=true
	for iteration in range(100):same=same and content.tables==content.tables
	rows.append({"field":"shared_definitions","same":same,"equality_ms_per_call":(Time.get_ticks_usec()-before)/100000.0})
	var report={"game_version":ContentRegistry.APP_VERSION,"cells":map.cells.size(),"rows":rows}
	var file=FileAccess.open("res://reports/query_equality_profile_v024.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("QUERY_EQUALITY_PROFILE ",JSON.stringify(report));quit()
