extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, id: String) -> void:
	checks.append({"name":id,"passed":ok})
	if not ok:failures.append(id);push_error("COMMANDER_ROSTER: "+id)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"native_content_loads")
	if not failures.is_empty():finish(content);return
	verify(content.tables.generals.size()>=300,"at_least_300_unique_military_commanders")
	verify(content.indexes.generals.size()==content.tables.generals.size(),"no_duplicate_general_ids")
	verify(content.tables.commander_service.size()==content.tables.generals.size(),"one_service_record_per_military_general")
	var names={};var sourced=0;var brigade=0;var division=0
	var lives=content.read_json("res://presentation/data/general_lifespans.json")
	for d in content.tables.generals:
		var service=CommanderRoster.service(content,str(d.id));var life=lives.generals.get(d.id,{})
		verify(not names.has(str(d.name)),"unique_name:"+str(d.id));names[str(d.name)]=true
		verify(not service.is_empty() and service.name==d.name and service.birth_year<service.death_year,"service_identity:"+str(d.id))
		verify(not life.is_empty() and life.stages.size()==4,"four_living_age_specs:"+str(d.id))
		# Several commanders died in their twenties: a teenage archive preview
		# may start at 15. Military deployment still independently requires 16.
		for stage in life.get("stages",[]):verify(int(stage.reference_year)>=int(life.birth_year)+15 and int(stage.reference_year)<=int(life.death_year),"age_within_life:"+str(d.id)+":"+str(stage.id))
		verify(not str(service.get("documented_title","")).is_empty() and not service.get("source_ids",[]).is_empty(),"qualifying_office_and_source:"+str(d.id))
		if not service.get("source_ids",[]).is_empty():sourced+=1
		for id in service.get("source_ids",[]):verify(not content.definition("commander_sources",str(id)).is_empty(),"service_source_resolves:"+str(d.id)+":"+str(id))
		if service.get("command_level")=="brigade":brigade+=1
		if service.get("command_level")=="division":division+=1
	verify(sourced==content.tables.generals.size() and brigade>40 and division>50,"expansion_reaches_actual_brigade_and_division_commands")
	var full_commanders=content.tables.commander_service.filter(func(s):return s.command_level not in ["deputy_division","army_political_co_command","division_political_co_command"])
	verify(full_commanders.size()>=300,"at_least_300_without_counting_deputy_division_or_political_co_command")
	var corrected=CommanderRoster.filtered(content,"刑清忠")
	verify(corrected.size()==1 and corrected[0].name=="邢清忠" and corrected[0].id=="cn_52116e055fe0","documented_name_correction_preserves_source_search_and_stable_id")
	for date in ["1880-01-01","1900-01-01","2010-01-01"]:verify(not CommanderRoster.alive_on(content,"zhang_xueliang",date),"no_prebirth_child_or_posthumous_deployment:"+date)
	verify(not CommanderRoster.alive_on(content,"mao_zedong","1909-12-25") and CommanderRoster.alive_on(content,"mao_zedong","1909-12-26"),"adult_eligibility_respects_known_birthday")
	var divisions=CommanderRoster.filtered(content,"","all","division")
	verify(not divisions.is_empty() and divisions.all(func(d):return CommanderRoster.service(content,str(d.id)).command_level in ["division","deputy_division","division_political_co_command"]),"division_filter_uses_office_level")
	verify(CommanderRoster.filtered(content,"","Japan").all(func(d):return CommanderRoster.service(content,str(d.id)).country=="Japan"),"country_filter")
	verify(CommanderRoster.filtered(content,"does-not-exist-98765").is_empty(),"empty_search_result")
	var chen=CommanderRoster.filtered(content,"第386旅")
	verify(chen.any(func(d):return d.name=="陈赓"),"search_by_historical_formation")
	var scenarios_checked=0
	for id in content.scenarios:
		var recipe=content.scenarios[id];var deployment=content.definition("commander_deployments",str(id))
		verify(not deployment.is_empty() and deployment.anchor_date==recipe.anchor_date,"dated_roster_exists:"+str(id))
		var used={}
		for owner in recipe.faction_roster:
			for entry in CommanderRoster.entries(content,recipe,str(owner)):
				verify(not used.has(str(entry.general_id)),"one_starting_side:"+str(id)+":"+str(entry.general_id));used[str(entry.general_id)]=true
				verify(CommanderRoster.alive_on(content,str(entry.general_id),str(recipe.anchor_date)),"living_starting_commander:"+str(id)+":"+str(entry.general_id))
		if recipe.mode!="legion":scenarios_checked+=1
	verify(scenarios_checked==49,"authored_rosters_cover_all_existing_battles_and_conquests")
	var recipe=content.scenarios.campaign_1924_01
	var state=StateBuilder.create(content,str(recipe.id),"zhili",{})
	verify(state.generals.filter(func(g):return g.owner_id=="fengtian").size()==CommanderRoster.entries(content,recipe,"fengtian").size(),"historical_side_not_truncated_to_legacy_quota")
	verify(state.generals.filter(func(g):return g.owner_id=="fengtian").size()>int(recipe.general_slots),"more_commanders_than_old_uniform_slots_are_retained")
	verify(state.generals.any(func(g):return g.deployment_role=="strategic_reserve" and g.assigned_unit_id==null),"strategic_reserve_does_not_spawn_extra_formations")
	var assigned={}
	for g in state.generals:
		if g.assigned_unit_id==null:continue
		var u=StateAccess.find(state,"units",str(g.assigned_unit_id))
		verify(not assigned.has(u.id) and u.general_id==g.id and u.owner_id==g.owner_id,"one_own_unit_per_commander:"+str(g.id));assigned[u.id]=true
		verify(EffectRules.scope_matches(content.definition("skills",str(g.active_skill_id)).caster_scope,u,content),"auto_assignment_matches_skill_family:"+str(g.id))
	var restored=JSON.parse_string(JSON.stringify(state))
	verify(restored.generals==JSON.parse_string(JSON.stringify(state.generals)),"reserve_and_history_metadata_survive_serialization")
	var early=CommanderRoster.deployment_index(content,content.scenarios.asia_1927)
	verify(not early.has("mao_zedong") and not early.has("peng_dehuai"),"no_future_1927_military_appointments")
	verify(not CommanderRoster.deployment_index(content,content.scenarios.campaign_1900_03).has("waldersee"),"waldersee_not_deployed_before_arrival")
	verify(not CommanderRoster.deployment_index(content,content.scenarios.campaign_1917_03).has("alexei_kaledin"),"don_commander_not_placed_in_petrograd")
	var dagu=content.scenarios.campaign_1860_01
	verify(dagu.faction_roster==["qing","british_empire","french_empire"],"1860_uses_anglo_french_expedition_not_1900_eight_nations")
	var defense=StateBuilder.create(content,str(dagu.id),"qing",{})
	verify(StateAccess.allied(defense,"british_empire","french_empire") and StateAccess.hostile(defense,"qing","french_empire"),"historical_coalition_is_not_at_war_with_itself")
	for owner in dagu.faction_roster:
		verify(defense.units.any(func(u):return u.owner_id==owner),"each_authored_battle_side_has_its_own_formations:"+str(owner))
		verify(defense.generals.any(func(g):return g.owner_id==owner),"each_dagu_side_has_sourced_commanders:"+str(owner))
	verify(defense.objectives[0].type=="hold" and StateAccess.find(defense,"cities","tianjin").owner_id=="qing","qing_defends_dagu_theater_before_tianjin_falls")
	verify(not defense.units.any(func(u):return u.def_id=="machine_gun"),"1860_garrison_does_not_bypass_period_equipment")
	VictoryRules.check(defense,content,[])
	verify(defense.status=="playing","defending_an_owned_city_does_not_instantly_finish_capture_objective")
	var assault=StateBuilder.create(content,str(dagu.id),"french_empire",{})
	verify(assault.objectives[0].type=="capture" and assault.objectives[0].accept_allied_control,"attacking_french_side_receives_coalition_capture_goal")
	StateAccess.find(assault,"cities","tianjin").owner_id="british_empire"
	VictoryRules.check(assault,content,[])
	verify(assault.status!="playing" and assault.winner_id=="french_empire","allied_capture_completes_explicit_coalition_objective")
	verify(content.scenarios.campaign_1860_01.objective_type=="hold" and dagu.player_default=="qing","per_side_initialization_preserves_source_recipe")
	verify(not CommanderRoster.deployment_index(content,content.scenarios.campaign_1890_03).has("ding_ruchang") and not CommanderRoster.deployment_index(content,content.scenarios.campaign_1890_03).has("liu_buchan"),"naval_officers_dead_in_february_are_not_deployed_in_april_1895")
	verify(not CommanderRoster.deployment_index(content,content.scenarios.campaign_1840_02).has("hugh_gough"),"gough_not_present_before_march_1841_arrival")
	var recall_count=0
	for start in content.tables.commander_recall_pools:
		var conquest=content.scenarios[str(start.id)]
		verify(conquest.mode=="conquest" and start.anchor_date==conquest.anchor_date,"optional_reserves_only_in_dated_free_world:"+str(start.id))
		var opening=content.definition("commander_deployments",str(start.id))
		var opening_ids=[]
		for rows in opening.factions.values():
			for entry in rows:opening_ids.append(str(entry.general_id))
		for side in start.factions:
			verify(conquest.faction_roster.has(side),"recall_side_exists:"+str(start.id)+":"+str(side))
			for entry in start.factions[side]:
				recall_count+=1
				var service=CommanderRoster.service(content,str(entry.general_id))
				verify(not opening_ids.has(str(entry.general_id)) and service.historical_side==side,"optional_recall_does_not_duplicate_or_change_side:"+str(start.id)+":"+str(entry.general_id))
				verify(int(service.documented_year)<int(conquest.anchor_date.left(4)) and not entry.auto_assign and entry.deployment_role=="conquest_optional_reserve","recall_has_prior_office_and_never_auto_assigns:"+str(start.id)+":"+str(entry.general_id))
	verify(recall_count>50,"free_world_reserves_expand_player_appointment_options")
	var free_state=StateBuilder.create(content,"asia_1940","kmt",{})
	verify(not free_state.is_empty(),"free_world_registered_player_has_a_playable_start")
	if free_state.is_empty():finish(content);return
	verify(free_state.generals.any(func(g):return g.deployment_role=="conquest_optional_reserve"),"free_world_initializes_optional_reserves")
	for general in free_state.generals:
		if general.deployment_role=="conquest_optional_reserve":verify(general.assigned_unit_id==null,"optional_reserve_waits_for_player_appointment:"+str(general.id))
	var battlefield=StateBuilder.create(content,"campaign_1940_02","ccp",{})
	verify(not battlefield.generals.any(func(g):return g.deployment_role=="conquest_optional_reserve"),"historical_local_battle_has_no_free_world_recall_pool")
	var in1940=CommanderRoster.entries(content,content.scenarios.asia_1940,"ccp")
	var unavailable_ids=content.tables.commander_service.filter(func(s):return s.name in ["林彪","徐海东"]).map(func(s):return str(s.id))
	verify(not in1940.any(func(g):return unavailable_ids.has(str(g.general_id))),"overseas_treatment_and_long_term_illness_do_not_instantly_deploy")
	var april1927=CommanderRoster.entries(content,content.scenarios.asia_1927,"ccp")
	var later_allegiance=content.tables.commander_service.filter(func(s):return s.name in ["叶挺","叶剑英"]).map(func(s):return str(s.id))
	verify(not april1927.any(func(g):return later_allegiance.has(str(g.general_id))),"recall_does_not_backdate_later_party_allegiance")
	var training=content.scenarios.legion_01
	var candidates=CommanderRoster.training_candidates(content,training).map(func(d):return str(d.id))
	verify(candidates.has("wu_peifu") and candidates.has("feng_yuxiang") and not candidates.has("hong_xiuquan"),"training_selection_uses_reference_era")
	verify(not LegionRules.validate(content,training,LegionRules.default_army(content,training),candidates.slice(0,3)).valid,"training_budget_remains_separate_from_historical_rosters")
	verify(not LegionRules.validate(content,training,LegionRules.default_army(content,training),["hong_xiuquan"]).valid,"training_rejects_out_of_era_commander")
	finish(content)

func finish(content: ContentRegistry) -> void:
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"military_commanders":content.tables.get("generals",[]).size(),"all_asia_historical_oob_complete":false}
	var file=FileAccess.open("res://reports/commander_roster_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("COMMANDER_ROSTER_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if report.passed else 1)
