class_name CommanderRoster
extends RefCounted

const PAGE_SIZE=12
const COUNTRIES={"China":"中国","Japan":"日本","France":"法国","Britain":"英国","United States":"美国","Russia":"俄国","Germany":"德国"}
const LEVELS={"brigade":"旅长 / 旅团长","deputy_brigade":"副旅长","division":"师长 / 师团长","deputy_division":"副师长","army_or_higher":"军及以上指挥官","deputy_army_or_higher":"军及以上副职","fleet":"舰队统帅","naval_squadron":"海军战队指挥官","national_high_command":"最高军政指挥","historical_regional_command":"历史区域统帅","historical_theater_command":"历史战区统帅","historical_field_command":"历史军队统帅","brigade_political_co_command":"旅级军政共同指挥","division_political_co_command":"师级军政共同指挥","army_political_co_command":"军及以上军政共同指挥","legacy_pending_office_audit":"原有将领 · 军职复核中","expeditionary_command":"远征军统帅"}

static func service(content: ContentRegistry, id: String) -> Dictionary:
	return content.definition("commander_service",id)

static func grade(record: Dictionary) -> String:
	return str(LEVELS.get(record.get("command_level",""),"军职资料待补充"))

static func alive_on(content: ContentRegistry, id: String, date: String) -> bool:
	var record=service(content,id)
	if record.is_empty() or date.length()<4:return false
	var year=int(date.left(4))
	if year<int(record.get("birth_year",9999))+16 or year>int(record.get("death_year",0)):return false
	if str(record.get("birth_date",""))!="" and date<str(record.birth_date):return false
	if year==int(record.get("birth_year",0))+16 and str(record.get("birth_date","")).length()==10 and date.substr(5,5)<str(record.birth_date).substr(5,5):return false
	if str(record.get("death_date",""))!="" and date>str(record.death_date):return false
	return true

static func entries(content: ContentRegistry, recipe: Dictionary, owner: String) -> Array:
	var deployment=content.definition("commander_deployments",str(recipe.id))
	var result: Array=[]
	var candidates: Array=deployment.get("factions",{}).get(owner,[]).duplicate()
	# Optional conquest reserves are a separately published gameplay pool. They
	# never enter local historical battles or auto-spawn extra military stacks.
	if str(recipe.get("mode",""))=="conquest":
		var recall=content.definition("commander_recall_pools",str(recipe.id))
		candidates.append_array(recall.get("factions",{}).get(owner,[]))
	var used={}
	for entry in candidates:
		var id=str(entry.get("general_id",""))
		if used.has(id) or content.definition("generals",id).is_empty() or not alive_on(content,id,str(recipe.anchor_date)):continue
		if str(recipe.anchor_date)<str(entry.get("eligible_from","0000-00-00")) or str(recipe.anchor_date)>str(entry.get("eligible_through","9999-12-31")):continue
		result.append(entry);used[id]=true
	return result

static func entry_for(content: ContentRegistry, recipe: Dictionary, id: String) -> Dictionary:
	for owner in recipe.faction_roster:
		for entry in entries(content,recipe,str(owner)):
			if str(entry.general_id)==id:return entry.merged({"owner_id":owner})
	return {}

static func deployment_index(content: ContentRegistry, recipe: Dictionary) -> Dictionary:
	var result={}
	for owner in recipe.faction_roster:
		for entry in entries(content,recipe,str(owner)):result[str(entry.general_id)]=entry.merged({"owner_id":owner})
	return result

static func training_candidates(content: ContentRegistry, recipe: Dictionary) -> Array:
	var reference=content.scenarios.get(str(recipe.get("scenario_reference","conq_1924")),{})
	if reference.is_empty():return []
	var available=deployment_index(content,reference)
	return content.tables.generals.filter(func(d):return available.has(str(d.id)))

static func count_summary(content: ContentRegistry, recipe: Dictionary) -> String:
	var parts=PackedStringArray()
	for owner in recipe.faction_roster:
		var roster=entries(content,recipe,str(owner))
		var reserves=roster.filter(func(r):return r.get("deployment_role","")=="conquest_optional_reserve").size()
		var suffix="（含后备%d）"%reserves if reserves>0 else ""
		parts.append("%s %d人%s"%[content.definition("factions",owner).get("name",owner),roster.size(),suffix])
	return " / ".join(parts)

static func matches(record: Dictionary, query: String, country: String="all", level: String="all", era: int=0) -> bool:
	if country!="all" and str(record.get("country",""))!=country:return false
	var command=str(record.get("command_level",""))
	if level=="brigade" and command not in ["brigade","deputy_brigade","brigade_political_co_command"]:return false
	if level=="division" and command not in ["division","deputy_division","division_political_co_command"]:return false
	if level=="army" and command not in ["army_or_higher","deputy_army_or_higher","national_high_command","army_political_co_command","expeditionary_command"]:return false
	if level=="naval" and command not in ["fleet","naval_squadron"]:return false
	if level=="historical" and not command.begins_with("historical_"):return false
	# This archive filter means living adult in the year, never a claim to hold
	# an office continuously between birth and death or to be present in a battle.
	if era>0 and (era<int(record.get("birth_year",9999))+16 or era>int(record.get("death_year",0))):return false
	var text="%s %s %s %s %s %s %s %s"%[record.get("name",""),record.get("documented_title",""),record.get("historical_side",""),record.get("country",""),COUNTRIES.get(record.get("country",""),""),grade(record),record.get("historical_note",""),str(record.get("source_name_variants",[]))]
	return query.strip_edges().is_empty() or text.containsn(query.strip_edges())

static func filtered(content: ContentRegistry, query: String="", country: String="all", level: String="all", era: int=0) -> Array:
	var result: Array=[]
	for d in content.tables.generals:
		if matches(service(content,str(d.id)),query,country,level,era):result.append(d)
	return result
