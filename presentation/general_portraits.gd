class_name GeneralPortraits
extends RefCounted

const CATALOG_PATH="res://presentation/data/general_portraits.json"
var records: Dictionary={}

func _init() -> void:
	if FileAccess.file_exists(CATALOG_PATH):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(CATALOG_PATH))
		if parsed is Dictionary:records=parsed.get("generals",{})

func resolve(general_id: String, date: String="", stage_override: String="") -> Dictionary:
	var entry: Dictionary=records.get(general_id,{"name":general_id,"variants":[]})
	var result={"general_id":general_id,"name":entry.get("name",general_id),"kind":"identity","asset_id":"","reference_year":0,"age_stage":"","age_years":0,"age_approximate":true,"caption":"该年代暂无肖像"}
	var year=int(date.left(4)) if date.length()>=4 and date.left(4).is_valid_int() else 0
	var born=int(entry.get("birth_year",0));var died=int(entry.get("death_year",9999))
	if born>0 and year>0 and (year<born or (entry.get("date_precision","")=="day" and date<str(entry.get("birth_date","")))):
		result.caption="尚未出生";return result
	var before_sixteenth_birthday=year-born==16 and entry.get("date_precision","")=="day" and date.length()>=10 and date.substr(5,5)<str(entry.get("birth_date","")).substr(5,5)
	if year>0 and born>0 and (year-born<16 or before_sixteenth_birthday):
		result.caption="未到青年阶段 · 约%d岁"%maxi(0,year-born);return result
	var preview=stage_override if not stage_override.is_empty() else ("middle" if year==0 else "")
	var candidates: Array=entry.get("variants",[]).filter(func(v):return preview.is_empty() or v.age_stage==preview)
	var chosen: Dictionary={}
	var target=0
	for stage in entry.get("stages",[]):
		if stage.id==preview:target=int(stage.reference_year)
	for variant in candidates:
		var reference=int(variant.reference_year)
		if year>0 and reference>year:continue
		if chosen.is_empty() or reference>int(chosen.reference_year):chosen=variant
		if year==0 and reference==target:chosen=variant;break
	if chosen.is_empty() and year>=born:
		# A young-stage illustration represents that stage, not a photo taken in
		# its reference year. Never substitute a later life stage here.
		for variant in candidates:
			if variant.age_stage=="young":chosen=variant;break
	if chosen.is_empty():return result
	var age_year=mini(year,died) if year>0 else int(chosen.reference_year)
	var age=maxi(0,age_year-born);var approximate=entry.get("date_precision","year")!="day"
	if not approximate and year>0 and date.length()>=10:
		var effective_date=date if date<=str(entry.get("death_date","9999-12-31")) else str(entry.death_date)
		if effective_date.substr(5,5)<str(entry.birth_date).substr(5,5):age-=1
	var label=""
	for stage in entry.get("stages",[]):
		if stage.id==chosen.age_stage:label=str(stage.label)
	var caption="%s · %s%d岁"%[label,"约" if approximate else "",age]
	if year>died or (entry.get("date_precision","")=="day" and date>str(entry.get("death_date","9999-12-31"))):caption="%s · %d—%d"%[label if label.begins_with("生前") else "生前"+label,born,died]
	result.merge({"kind":"portrait","asset_id":str(chosen.asset_id),"reference_year":int(chosen.reference_year),"age_stage":str(chosen.age_stage),"age_years":age,"age_approximate":approximate,"caption":caption,"reference_caption":"%d年形象"%int(chosen.reference_year),"lifespan":"%d—%d"%[born,died]},true)
	return result
