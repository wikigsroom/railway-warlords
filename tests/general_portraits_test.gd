extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func run() -> void:
	var content=ContentRegistry.new();verify(content.load_all(),"native_content_loaded")
	var library=GeneralPortraits.new()
	var history=JSON.parse_string(FileAccess.get_file_as_string("res://content/history/asia_timeline.json"))
	var people: Array=content.tables.generals.duplicate(true)
	for figure in history.political_figures:
		if not people.any(func(p):return p.id==figure.id):people.append({"id":figure.id,"name":figure.name_zh})
	var manifest=JSON.parse_string(FileAccess.get_file_as_string("res://assets/manifest.json"))
	var assets={}
	for row in manifest.assets:assets[row.id]=row
	verify(library.records.size()==people.size() and people.size()==33,"every_registered_person_and_general_has_explicit_presentation")
	var catalog=JSON.parse_string(FileAccess.get_file_as_string(GeneralPortraits.CATALOG_PATH))
	verify(catalog.production_complete and catalog.missing_age_stages.is_empty(),"all_four_stages_produced")
	var originals={};var portraits=0;var identities=0
	for general in people:
		var chosen=library.resolve(general.id)
		if chosen.kind=="identity":identities+=1
		else:portraits+=1
		verify(chosen.name==general.name,"identity_matches_rules_catalog:"+general.id)
		var seen={}
		for stage in library.records[general.id].stages:
			var preview=library.resolve(general.id,"",stage.id)
			verify(preview.kind=="portrait" and preview.age_stage==stage.id and preview.reference_year==stage.reference_year,"explicit_age_stage:"+general.id+":"+stage.id)
			seen[preview.asset_id]=true
		verify(seen.size()==4,"four_distinct_originals:"+general.id)
		verify(not library.records[general.id].reference_urls.is_empty(),"lifespan_source_recorded:"+general.id)
		for variant in library.records[general.id].variants:
			var asset: Dictionary=assets.get(variant.asset_id,{})
			var path=str(asset.get("engine_path",""))
			verify(not path.is_empty() and FileAccess.get_sha256(path)==variant.asset_sha256 and variant.asset_sha256==asset.get("source_sha256",""),"original_bytes_bound_to_catalog:"+variant.asset_id)
			verify(ResourceLoader.exists(path) and not variant.exact_year_photograph_claimed,"loadable_interpretive_original:"+variant.asset_id)
			originals[variant.asset_id]=true
	verify(originals.size()==135 and portraits==33 and identities==0,"135_originals_cover_all_33_people_and_four_stages")
	for figure in history.political_figures:
		verify(library.records.has(figure.id),"political_figure_included:"+figure.id)
	for id in ["daoguang","xianfeng","ito_hirobumi","nicholas_ii"]:
		verify(not content.tables.generals.any(func(g):return g.id==id) and not library.records[id].military_deployable,"archive_does_not_create_military_general:"+id)
	var xianfeng=library.resolve("xianfeng","", "middle")
	verify(xianfeng.age_years==26 and xianfeng.caption.begins_with("在位中期"),"short_life_does_not_invent_middle_aged_xianfeng")
	for example in [["li_hongzhang","1860-01-01",1860],["li_hongzhang","1889-12-31",1873],["li_hongzhang","1890-01-01",1890],["li_hongzhang","1900-01-01",1900],["yamagata_aritomo","1917-09-01",1917],["mao_zedong","1927-08-01",1927],["mao_zedong","1940-08-20",1940],["chiang_kai_shek","1940-01-01",1940]]:
		verify(library.resolve(example[0],example[1]).reference_year==example[2],"chronological_boundary:%s:%s"%[example[0],example[1]])
	verify(library.resolve("li_hongzhang","1840-01-01").age_stage=="young","young_illustration_covers_early_adult_year_without_later_stage")
	verify(library.resolve("wu_peifu","1917-01-01").reference_year==1914,"warlord_uses_appropriate_pre_1920_stage")
	verify(library.resolve("mao_zedong","1893-12-25").kind=="identity","no_portrait_before_exact_birth_day")
	verify(library.resolve("mao_zedong","1900-01-01").kind=="identity","no_adult_face_for_childhood")
	verify(library.resolve("mao_zedong","1909-12-25").kind=="identity" and library.resolve("mao_zedong","1909-12-26").kind=="portrait","sixteenth_birthday_boundary_respects_exact_date")
	for example in [["1917-01-01","young",23],["1917-12-26","young",24],["1947-01-01","middle",53],["1947-12-26","middle",54]]:
		var record=library.resolve("mao_zedong",example[0])
		verify(record.name=="李德胜" and record.age_stage==example[1] and record.age_years==example[2] and not record.age_approximate,"requested_age_and_birthday:"+example[0])
	var posthumous=library.resolve("mao_zedong","1990-01-01")
	verify(posthumous.age_years==82 and posthumous.caption.begins_with("生前"),"no_posthumous_aging")
	var short_life=library.resolve("guo_songling","1947-01-01")
	verify(short_life.reference_year==1925 and short_life.age_years==42 and short_life.caption.contains("生前"),"short_life_retains_last_living_period")
	verify(not short_life.caption.contains("生前生前"),"posthumous_caption_does_not_duplicate_living_prefix")
	verify(library.resolve("unknown_general","1940-01-01").kind=="identity","missing_identity_has_explicit_fallback")
	var hong=library.resolve("hong_xiuquan","1860-05-01")
	verify(hong.kind=="portrait" and hong.age_stage=="middle" and hong.reference_year==1855,"hong_has_generated_interpretive_middle_portrait")
	var scenario_count=0
	for id in content.scenarios:
		var scenario: Dictionary=content.scenarios[id]
		var date=str(scenario.get("anchor_date",""))
		if date.is_empty():continue
		var year=int(date.left(4));var before=ContentRegistry.fingerprint(scenario);var valid=true
		for general in content.tables.generals:
			var chosen=library.resolve(general.id,date)
			valid=valid and (chosen.kind=="identity" or chosen.reference_year<=year or chosen.age_stage=="young")
		verify(valid and ContentRegistry.fingerprint(scenario)==before,"dated_lookup_never_changes_or_anticipates_scenario:"+id)
		scenario_count+=1
	verify(scenario_count>=40,"dated_checks_cover_published_scenario_catalog")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"content_hash":content.content_hash,"dated_scenarios":scenario_count,"originals":originals.size(),"formal_art_approval":false,"historical_likeness_approval":false}
	var file=FileAccess.open("res://reports/general_portraits_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("GENERAL_PORTRAITS_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if report.passed else 1)
