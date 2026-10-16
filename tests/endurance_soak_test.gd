extends SceneTree

const ExactFingerprint = preload("res://tests/immutable_state_fingerprint.gd")
const QA_METADATA_FIELDS = ["scenario_id", "match_id", "combat_random", "content_hash", "round_limit"]

var content = ContentRegistry.new()
var kernel: CommandKernel
var fingerprints = ExactFingerprint.new()
var failures: Array = []
var checkpoints: Array = []
var actions: Dictionary = {}
var output_root = ""
var command_count = 0
var invariant_checks = 0
var replay_commands = 0
var started = 0

func _init() -> void:
	run.call_deferred()

func argument(name: String, fallback: String) -> String:
	var args = OS.get_cmdline_user_args()
	var index = args.find(name)
	return args[index + 1] if index >= 0 and index + 1 < args.size() else fallback

func file_sha(path: String) -> String:
	var hashing = HashingContext.new()
	hashing.start(HashingContext.HASH_SHA256)
	hashing.update(FileAccess.get_file_as_bytes(path))
	return hashing.finish().hex_encode()

func write_json(name: String, value: Dictionary) -> void:
	var file = FileAccess.open(output_root.path_join(name), FileAccess.WRITE)
	if file == null:
		failures.append("cannot_write:" + name)
		return
	file.store_string(JSON.stringify(value, "\t"))
	file.close()

func baseline_hash(state: Dictionary) -> String:
	var value = state.duplicate(false)
	for field in QA_METADATA_FIELDS:
		value.erase(field)
	return fingerprints.state_hash(value)

func check_invariants(state: Dictionary) -> Array:
	var errors: Array = []
	var occupied = {}
	var identifiers = {}
	var owners = {}
	for faction in state.factions:
		owners[faction.id] = true
		for resource in faction.resources:
			if faction.resources[resource] < 0:
				errors.append("negative_resource:" + faction.id + ":" + resource)
	for unit in state.units:
		if identifiers.has(unit.id):
			errors.append("duplicate_unit:" + unit.id)
		identifiers[unit.id] = true
		if not owners.has(unit.owner_id) or content.definition("units", unit.def_id).is_empty():
			errors.append("unknown_unit_definition_or_owner:" + unit.id)
		if unit.hp <= 0 or unit.hp > unit.max_hp or unit.ammo < 0 or unit.ap_left < 0:
			errors.append("invalid_unit_values:" + unit.id)
		if unit.position == null:
			if unit.cargo_parent_id == null or StateAccess.find(state, "units", unit.cargo_parent_id).is_empty():
				errors.append("missing_carrier:" + unit.id)
			continue
		var coordinate = HexGrid.coordinate(unit.position)
		var key = HexGrid.key(coordinate)
		if occupied.has(key):
			errors.append("overlap:" + key)
		occupied[key] = unit.id
		var cell = StateAccess.cell(state, coordinate)
		if cell.is_empty() or cell.region_id == "restricted":
			errors.append("unit_outside_playable_map:" + unit.id)
	if state.phase_index < 0 or state.phase_index >= state.turn_order.size():
		errors.append("invalid_phase_index")
	var random = state.combat_random
	if random.state <= 0 or random.state >= CombatRandom.MODULUS or random.draws < 0:
		errors.append("invalid_combat_random")
	return errors

func trim_fingerprint_cache() -> void:
	# Keep every field in the exact fingerprint while bounding retained old
	# visibility snapshots. The production fingerprint implementation is unchanged.
	for field in fingerprints.cache:
		var records: Array = fingerprints.cache[field]
		if str(field).begins_with("sight.") and records.size() > 2:
			fingerprints.cache[field] = records.slice(records.size() - 2)

func run() -> void:
	started = Time.get_ticks_msec()
	output_root = argument("--output-root", "res://reports/endurance/adhoc")
	DirAccess.make_dir_recursive_absolute(output_root)
	if not content.load_all():
		failures.append("content_load:" + str(content.errors))
		write_json("result.json", {"passed": false, "failures": failures})
		quit(1)
		return
	var production_hash = content.content_hash
	var scenario = argument("--scenario", "conq_1924")
	var player = argument("--player", content.scenarios[scenario].player_default)
	var target_rounds = int(argument("--rounds", "100"))
	var qa_budget = maxi(target_rounds + 20, int(content.scenarios[scenario].round_limit))
	var original_recipe = content.scenarios[scenario].duplicate(true)
	var original_recipe_sha = file_sha("res://content/scenarios/" + scenario + ".json")
	var state = StateBuilder.create(content, scenario, player, {}, "normal")
	if state.is_empty():
		failures.append("starting_state_unavailable")
		write_json("result.json", {"passed": false, "failures": failures})
		quit(1)
		return
	var baseline = baseline_hash(state)
	var original_round_limit = int(state.round_limit)
	var original_match_id = str(state.match_id)
	var original_random = state.combat_random.duplicate(true)
	var initial_units = state.units.size()
	var initial_cities = state.cities.size()
	var qa_recipe = original_recipe.duplicate(true)
	qa_recipe.id = "qa_endurance_" + scenario
	qa_recipe.round_limit = qa_budget
	content.scenarios[qa_recipe.id] = qa_recipe
	content.content_hash = ContentRegistry.fingerprint({"production_content_hash": production_hash, "qa_recipe": qa_recipe})
	state.scenario_id = qa_recipe.id
	state.round_limit = qa_budget
	state.content_hash = content.content_hash
	state.match_id = argument("--seed", "qa_endurance_20261012_" + scenario)
	state.combat_random = CombatRandom.initialize(state.match_id)
	var starting_deployment_preserved = baseline_hash(state) == baseline
	if not starting_deployment_preserved:
		failures.append("starting_state_changed_beyond_qa_metadata")
	kernel = CommandKernel.new(content)
	var save_root = "user://qa/endurance/" + str(Time.get_ticks_usec())
	var storage = SaveService.new(save_root, content)
	if not storage.write("test", state, content.content_hash):
		failures.append("initial_save:" + storage.error)
	else:
		if DirAccess.copy_absolute(storage.path_for("test"), output_root.path_join("initial_snapshot.json")) != OK:
			failures.append("initial_snapshot_copy")
	var rng = RandomNumberGenerator.new()
	rng.seed = 19241023
	var scheduled: Dictionary = {}
	for index in range(20):
		var first = 1 + int(index * target_rounds / 20)
		var last = mini(target_rounds - 1, int((index + 1) * target_rounds / 20))
		# Leave one complete ordinary round for the final three-command replay.
		scheduled[rng.randi_range(first, last)] = index
	var phase_key = ""
	var phase_commands = 0
	var checkpoint_phase = -1
	var checkpoint_offset = 0
	var checkpoint_round = -1
	var last_round = -1
	var planner: AIPlanner
	var shadow: Dictionary = {}
	var shadow_remaining = 0
	var trace = FileAccess.open(output_root.path_join("commands.jsonl"), FileAccess.WRITE)
	if trace == null:
		failures.append("cannot_write_command_trace")
	var guard = maxi(20000, target_rounds * state.turn_order.size() * 1000)
	while failures.is_empty() and state.status == "playing" and state.round <= target_rounds and command_count < guard:
		if state.round != last_round:
			last_round = state.round
			if scheduled.has(state.round):
				var live: Array = []
				for index in range(state.turn_order.size()):
					if not StateAccess.faction(state, state.turn_order[index]).eliminated:
						live.append(index)
				checkpoint_phase = live[rng.randi_range(0, live.size() - 1)]
				checkpoint_offset = rng.randi_range(1, 3)
				checkpoint_round = state.round
			write_json("progress.json", {"running": true, "round": state.round, "commands": command_count, "checkpoints": checkpoints.size(), "elapsed_ms": Time.get_ticks_msec() - started})
			if state.round == 1 or state.round % 10 == 0:
				print("ENDURANCE_PROGRESS ", state.round, " commands=", command_count, " checkpoints=", checkpoints.size())
		var owner = state.turn_order[state.phase_index]
		var key = owner + ":" + str(StateAccess.faction(state, owner).own_phase_index)
		if key != phase_key:
			phase_key = key
			phase_commands = 0
			planner = AIPlanner.new(content, kernel)
		var command = planner.choose(state)
		var random_before = state.combat_random.duplicate(true)
		var checkpoint_now = checkpoint_round == state.round and state.phase_index >= checkpoint_phase and (phase_commands + 1 >= checkpoint_offset or command.type == "EndPhase")
		var before_hash = fingerprints.state_hash(state) if checkpoint_now else ""
		var preview = kernel.preview(state, command)
		if not preview.valid or state.combat_random != random_before:
			failures.append("invalid_or_rng_mutating_preview:" + str(command))
			break
		if checkpoint_now:
			if fingerprints.state_hash(state) != before_hash:
				failures.append("preview_changed_full_state")
				break
			if not shadow.is_empty():
				failures.append("overlapping_checkpoint_replay")
				break
			var slot = "manual_" + str(rng.randi_range(1, 5))
			if not storage.write(slot, state, content.content_hash):
				failures.append("checkpoint_write:" + storage.error)
				break
			shadow = storage.load_slot(slot, content.content_hash)
			if shadow.is_empty() or fingerprints.state_hash(shadow) != before_hash or not shadow.map.cells.is_read_only():
				failures.append("checkpoint_load_full_state_or_immutable_geometry")
				break
			var name = "checkpoint_%02d.json" % checkpoints.size()
			if DirAccess.copy_absolute(storage.path_for(slot), output_root.path_join(name)) != OK:
				failures.append("checkpoint_copy")
				break
			checkpoints.append({"round": state.round, "phase_index": state.phase_index, "actor": owner, "phase_command_offset": phase_commands, "slot": slot, "snapshot": name, "snapshot_sha256": file_sha(output_root.path_join(name)), "full_state_sha256": before_hash, "combat_random": random_before, "replayed_commands": 0})
			shadow_remaining = 3
			checkpoint_round = -1
		var previous_version = state.state_version
		var previous_round = state.round
		var result = kernel.resolve(state, command)
		if not result.valid:
			failures.append("command_rejected:" + str(command))
			break
		if not shadow.is_empty():
			var replay_preview = kernel.preview(shadow, command)
			var replay = kernel.resolve(shadow, command)
			if ContentRegistry.fingerprint(replay_preview) != ContentRegistry.fingerprint(preview) or not replay.valid or fingerprints.result_hash(replay) != fingerprints.result_hash(result):
				failures.append("checkpoint_replay_changed_preview_events_full_state_or_rng")
				break
			shadow = replay.state
			shadow_remaining -= 1
			checkpoints[-1].replayed_commands += 1
			replay_commands += 1
			if shadow_remaining == 0:
				# Continue the long run from the actually loaded/replayed state.
				result.state = shadow
				shadow = {}
		state = result.state
		var violations = check_invariants(state)
		invariant_checks += 1
		if state.state_version != previous_version + 1 or state.round < previous_round or state.round > previous_round + 1 or state.combat_random.draws < random_before.draws:
			violations.append("version_round_or_rng_regressed")
		if not violations.is_empty():
			failures.append_array(violations)
			write_json("failure_snapshot.json", {"command": command, "state": state, "violations": violations})
			break
		command_count += 1
		phase_commands += 1
		actions[command.type] = int(actions.get(command.type, 0)) + 1
		trace.store_line(JSON.stringify({"index": command_count, "round_before": previous_round, "actor": owner, "command": command, "events_sha256": ContentRegistry.fingerprint(result.events), "state_version": state.state_version, "combat_random": state.combat_random}))
		trim_fingerprint_cache()
	if trace != null:
		trace.close()
	var completed = state.round - 1
	var published_recipe_unchanged = content.scenarios[scenario] == original_recipe and file_sha("res://content/scenarios/" + scenario + ".json") == original_recipe_sha
	if completed < target_rounds:
		failures.append("did_not_complete_requested_rounds:" + str(completed) + ":" + state.status)
	if checkpoints.size() != 20 or replay_commands != 60 or not checkpoints.all(func(row): return row.replayed_commands == 3):
		failures.append("twenty_random_phase_three_command_replays_incomplete")
	if not published_recipe_unchanged or int(actions.get("Attack", 0)) == 0 or int(actions.get("Move", 0)) == 0:
		failures.append("published_recipe_changed_or_no_actual_combat_and_movement")
	var report = {"passed": failures.is_empty(), "failures": failures, "game_version": ContentRegistry.APP_VERSION, "production_content_hash": production_hash, "qa_content_hash": content.content_hash, "source_scenario": scenario, "source_recipe_sha256": original_recipe_sha, "player": player, "qa_scenario": qa_recipe.id, "original_round_limit": original_round_limit, "qa_round_budget": qa_budget, "qa_metadata_fields": QA_METADATA_FIELDS, "starting_deployment_and_all_nonmetadata_fields_preserved": starting_deployment_preserved, "published_recipe_unchanged": published_recipe_unchanged, "original_random_match_id": original_match_id, "original_initial_combat_random": original_random, "repeatable_combat_seed": state.match_id, "requested_rounds": target_rounds, "completed_rounds": completed, "final_round": state.round, "final_status": state.status, "result_reason": state.get("result_reason", ""), "commands": command_count, "rejected_commands": failures.filter(func(value): return str(value).begins_with("command_rejected:")).size(), "actions": actions, "invariant_checks": invariant_checks, "initial_units": initial_units, "final_units": state.units.size(), "initial_cities": initial_cities, "actual_cells": state.map.cells.size(), "checkpoints": checkpoints, "replayed_commands": replay_commands, "final_combat_random": state.combat_random, "final_full_state_sha256": fingerprints.state_hash(state), "elapsed_ms": Time.get_ticks_msec() - started, "physical_android_device_tested": false, "historical_deployment_release_proof": false, "scope": "Native Godot headless reliability test. Original published conquest starting state; only QA identity/random/hash/deadline metadata differs. All ordinary AI, commands, combat, elimination and unification rules execute. Twenty randomly selected phases save/load/replay three real commands and resume the loaded state. The extended QA deadline is not a published historical scenario or human balance proof."}
	write_json("result.json", report)
	write_json("progress.json", {"running": false, "passed": report.passed, "round": state.round, "commands": command_count, "checkpoints": checkpoints.size()})
	print("ENDURANCE_RESULT ", JSON.stringify({"passed": report.passed, "completed_rounds": completed, "commands": command_count, "checkpoints": checkpoints.size(), "replayed_commands": replay_commands, "failures": failures}))
	quit(0 if report.passed else 1)
