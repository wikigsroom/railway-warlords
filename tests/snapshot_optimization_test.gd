extends SceneTree

var content=ContentRegistry.new()
var checks: Array=[]
var failures: Array=[]
var fingerprints=preload("res://tests/immutable_state_fingerprint.gd").new()
var trace_commands=0
var traces=[]

func _init() -> void:run.call_deferred()
func check(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func deeply_immutable(value: Variant) -> bool:
	return fingerprints.deeply_immutable(value)

func complete_state_hash(state: Dictionary) -> String:
	return fingerprints.state_hash(state)

func compare_trace(initial: Dictionary, name: String, limit: int, full_phase: bool) -> void:
	fingerprints.cache.clear()
	var actual=StateAccess.clone_transaction(initial)
	var expected=SnapshotReferenceAccess023.clone_transaction(initial)
	var kernel=CommandKernel.new(content);var reference=SnapshotReferenceKernel023.new(content)
	var planner=AIPlanner.new(content,kernel);var reference_planner=AIPlanner.new(content,CommandKernel.new(content))
	check(ContentRegistry.fingerprint(actual)==ContentRegistry.fingerprint(expected),name+":original_complete_start_state")
	var owner=actual.turn_order[actual.phase_index];var commands=0;var actions={}
	while commands<limit and actual.status=="playing":
		if full_phase and actual.turn_order[actual.phase_index]!=owner:break
		var command=planner.choose(actual);var reference_command=reference_planner.choose(expected)
		check(command==reference_command,name+":decision_%03d"%commands)
		var before=complete_state_hash(actual)
		var result=kernel.resolve(actual,command);var reference_result=reference.resolve(expected,reference_command)
		check(result.get("valid",false) and reference_result.get("valid",false),name+":legal_%03d"%commands)
		if not result.get("valid",false) or not reference_result.get("valid",false):break
		check(before==complete_state_hash(actual),name+":input_isolation_%03d"%commands)
		check(result.events==reference_result.events and result.preview==reference_result.preview,name+":ordered_events_and_preview_%03d"%commands)
		check(complete_state_hash(result.state)==complete_state_hash(reference_result.state),name+":all_state_fields_and_rng_%03d"%commands)
		actual=result.state;expected=reference_result.state
		actions[command.type]=int(actions.get(command.type,0))+1;commands+=1;trace_commands+=1
	check(ContentRegistry.fingerprint(actual)==ContentRegistry.fingerprint(expected),name+":original_complete_final_state")
	if full_phase:check(actual.turn_order[actual.phase_index]!=owner or actual.status!="playing",name+":complete_legal_phase")
	traces.append({"name":name,"commands":commands,"actions":actions,"full_phase":full_phase,"final_rng":actual.combat_random})
	print("SNAPSHOT_TRACE ",name," ",commands," commands")

func run() -> void:
	check(content.load_all(),"content_loads")
	check(content.tables.is_read_only(),"published_definitions_immutable")
	var provenance=content.read_json("res://tests/fixtures/reference_v023.json")
	for item in provenance.references:
		check(FileAccess.get_sha256("res://"+item.fixture)==item.reference_sha256,"preserved_reference_bytes:"+item.fixture)
	var state=StateBuilder.create(content,"conq_1922","zhili",{})
	var clone=StateAccess.clone_transaction(state);var before=ContentRegistry.fingerprint(state)
	check(is_same(clone.map.rail_edges[0].path_hexes,state.map.rail_edges[0].path_hexes) and deeply_immutable(clone.map.rail_edges[0].path_hexes),"rail_path_shared_only_when_recursively_immutable")
	clone.map.rail_edges[0].damage="broken";clone.map.rail_edges[0].capacity_left=0
	check(ContentRegistry.fingerprint(state)==before,"rail_damage_and_capacity_do_not_modify_input")
	var editable=StateAccess.clone_transaction(state);editable.map.rail_edges=editable.map.rail_edges.duplicate(true)
	var edited_clone=StateAccess.clone_transaction(editable)
	edited_clone.map.rail_edges[0].path_hexes[0].q+=1
	check(edited_clone.map.rail_edges[0].path_hexes!=editable.map.rail_edges[0].path_hexes,"mutable_editor_rail_paths_are_deep_copied")
	var fingerprint=content.content_hash
	check(content.load_all() and content.content_hash==fingerprint,"immutable_registry_reloads_without_payload_change")
	var altered=StateAccess.clone_transaction(state);var original_hash=complete_state_hash(altered)
	altered.factions[0].resources.cash+=1
	check(complete_state_hash(altered)!=original_hash,"state_digest_detects_mutable_resources")
	original_hash=complete_state_hash(altered);altered.map.rail_edges[0].damage="broken"
	check(complete_state_hash(altered)!=original_hash,"state_digest_detects_mutable_rail_damage")
	var shallow={"child":{"value":1}};shallow.make_read_only()
	var shallow_hash=fingerprints.exact_hash("shallow_guard",shallow);shallow.child.value=2
	check(not deeply_immutable(shallow) and fingerprints.exact_hash("shallow_guard",shallow)!=shallow_hash,"shallow_read_only_never_reuses_mutable_descendant_digest")
	compare_trace(StateBuilder.create(content,"campaign_1924_03","zhili",{}),"published_fog_campaign",12,false)
	var map=ContentRegistry.integerize(content.read_json("res://tests/fixtures/capacity_full_conquest.json"))
	for distribution in ["balanced","concentrated","single_faction"]:
		compare_trace(CapacityFixture.create(content,map.duplicate(true),distribution,4096),distribution,2400,true)
	check(traces.size()==4 and trace_commands>=300,"all_four_comparison_traces_completed")
	var report={"game_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"passed":checks.size()-failures.size(),"failed":failures.size(),"failures":failures,"checks":checks,"trace_commands":trace_commands,"traces":traces,"reference_version":"0.2.3","scope":"Exact archived snapshot access and command kernel, immutable and editor rail paths, definition reload, complete 240-unit legal phases, ordered decisions/events/previews, input isolation and every state field/RNG. Raw whole-state fingerprints also verified at each trace start/end."}
	var file=FileAccess.open("res://reports/snapshot_optimization_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("SNAPSHOT_OPTIMIZATION_TESTS ",report.passed," passed / ",report.failed," failed; ",trace_commands," commands")
	quit(0 if failures.is_empty() else 1)
