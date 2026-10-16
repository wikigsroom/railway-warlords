class_name ContentRegistry
extends RefCounted

const RUNTIME_RULESET_VERSION=9
const APP_VERSION="0.2.20"

var tables: Dictionary = {}
var indexes: Dictionary = {}
var maps: Dictionary = {}
var scenarios: Dictionary = {}
var rules: Dictionary = {}
var geography_sources: Dictionary = {}
var content_hash: String = ""
var errors: Array = []

func load_all() -> bool:
	# Published definitions are immutable; reload creates a new editable registry.
	tables={};indexes={}
	var catalog = read_json("res://content/definitions/catalog.json")
	if catalog.is_empty():
		return false
	for table in catalog.get("tables", []):
		var data = integerize(read_json("res://content/definitions/%s.json" % table))
		tables[table] = data
		if data is Array:
			var index: Dictionary = {}
			for record in data:
				if record.has("id"):
					if index.has(record.id):
						errors.append("重复定义：%s" % record.id)
					index[record.id] = record
			indexes[table] = index
	rules = tables.get("rules", {})
	content_hash = fingerprint(tables)
	var manifest = read_json("res://content/maps/catalog.json")
	for map_id in manifest.get("maps", []):
		maps[map_id] = integerize(read_json("res://content/maps/%s.json" % map_id))
		StateAccess.freeze_value(maps[map_id])
	var scenario_list = read_json("res://content/scenarios/catalog.json")
	for scenario_id in scenario_list.get("scenarios", []):
		scenarios[scenario_id] = integerize(read_json("res://content/scenarios/%s.json" % scenario_id))
	geography_sources=read_json("res://content/geography_sources.json")
	for general in tables.get("generals", []):
		if not indexes.skills.has(general.passive_skill) or not indexes.skills.has(general.active_skill):
			errors.append("将领战法引用失效：%s" % general.id)
	for unit in tables.get("units", []):
		if unit.hp <= 0 or unit.range_min > unit.range_max:
			errors.append("兵种数值失效：%s" % unit.id)
	content_hash = fingerprint({"ruleset_version":RUNTIME_RULESET_VERSION,"definitions":tables,"maps":maps,"scenarios":scenarios,"geography_sources":geography_sources})
	if errors.is_empty():StateAccess.freeze_value(tables)
	return errors.is_empty() and not rules.is_empty() and not scenarios.is_empty()

func definition(table: String, id: String) -> Dictionary:
	return indexes.get(table, {}).get(id, {})

static func conquest_reference_only(city: Dictionary, date: String) -> bool:
	return city.get("conquest_reference_only",false) or date<city.get("reference_only_before","0000-00-00") or date<city.get("protected_before","0000-00-00") or date>=city.get("reference_only_from","9999-12-31")

static func conquest_owner(city: Dictionary, date: String, scenario_id: String = "") -> String:
	# Asia scenarios publish starting control per timeline.  This is a scenario
	# deployment record, not a claim that a faction held every intervening county.
	if not scenario_id.is_empty() and city.get("reference_owner_by_scenario",{}).has(scenario_id):
		return str(city.reference_owner_by_scenario[scenario_id])
	var year=int(date.substr(0,4))
	if year==1920 and city.id in ["beijing","nanyuan","changxindian"]:return "anhui"
	if year>=1922 and city.id in ["nanyuan","changxindian","zhuozhou","langfang","yangcun"]:return "zhili"
	if year==1924 and city.id in ["qinhuangdao","shanhaiguan"]:return "zhili"
	return str(city.get("control_overrides_by_year",{}).get(str(year),city.get("reference_owner","")))

func playable_factions(scenario_id: String) -> Array:
	var recipe=scenarios.get(scenario_id,{})
	if recipe.is_empty():return []
	if recipe.mode!="conquest":return recipe.faction_roster.duplicate()
	var result: Array=[]
	for owner in recipe.faction_roster:
		if maps[recipe.map_id].cities.any(func(c):return c.level>=2 and not conquest_reference_only(c,recipe.anchor_date) and conquest_owner(c,recipe.anchor_date,scenario_id)==owner):result.append(owner)
	return result

static func administration_year(date: String) -> String:
	var year=int(date.substr(0,4))
	if year in [1920,1921]:return "1920"
	if year in [1922,1923]:return "1922"
	if year>=1924 and year<=1927:return "1924"
	return ""

static func administration_name(city: Dictionary, date: String) -> String:
	if city.id=="qingdao" and date>="1922-12-10" and date<"1929-01-01":return "胶澳商埠"
	return administration_label(city.get("administration_by_year",{}).get(administration_year(date),"尚未核实"),date)

static func administration_label(name: String, date: String) -> String:
	if name!="川边特别区":return name
	# The February 7 appointment is attested in the official military-history
	# PDF, p.40; the precise enactment day of the regional rename is not inferred
	# from that appointment. Early February uses a geographic reference label.
	if date>="1925-02-07":return "西康特别区"
	if date>="1925-02-01":return "川边地区"
	return name

func read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		errors.append("缺少内容：%s" % path)
		return {}
	var parser := JSON.new()
	if parser.parse(FileAccess.get_file_as_string(path)) != OK:
		errors.append("内容解析错误：%s" % path)
		return {}
	return parser.data

static func integerize(value: Variant) -> Variant:
	if value is Dictionary:
		var result: Dictionary = {}
		for key in value:
			result[key] = integerize(value[key])
		return result
	if value is Array:
		var result: Array = []
		for item in value:
			result.append(integerize(item))
		return result
	if value is float and value == floor(value):
		return int(value)
	return value

static func normalize(value: Variant) -> Variant:
	if value is Dictionary:
		var result: Dictionary = {}
		var keys = value.keys()
		keys.sort()
		for key in keys:
			result[key] = normalize(value[key])
		return result
	if value is Array:
		var result: Array = []
		var all_ids: bool = not value.is_empty()
		for item in value:
			result.append(normalize(item))
			all_ids = all_ids and item is Dictionary and item.has("id")
		if all_ids:
			result.sort_custom(func(a, b): return str(a.id) < str(b.id))
		return result
	return value

static func fingerprint(value: Variant) -> String:
	return JSON.stringify(normalize(value), "", true).sha256_text()
