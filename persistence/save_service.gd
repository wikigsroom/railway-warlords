class_name SaveService
extends RefCounted

var root_path: String="user://saves"
var error: String=""
var content: ContentRegistry
var last_presentation: Dictionary={}

func _init(path: String = "user://saves", registry: ContentRegistry = null) -> void:
	root_path=path
	content=registry
	DirAccess.make_dir_recursive_absolute(root_path)

func path_for(slot: String) -> String:return root_path+"/"+slot+".json"

func write(slot: String, payload: Dictionary, content_hash: String = "", presentation: Dictionary = {}) -> bool:
	if not valid_slot(slot):error="存档槽无效";return false
	payload=ContentRegistry.integerize(pack_map(payload,content_hash))
	var envelope={"schema_version":2,"game_version":ContentRegistry.APP_VERSION,"saved_at":Time.get_datetime_string_from_system(),"content_hash":content_hash,"checksum":ContentRegistry.fingerprint(payload),"payload":payload}
	if not presentation.is_empty():
		envelope.presentation=ContentRegistry.integerize(presentation.duplicate(true))
		envelope.presentation_checksum=ContentRegistry.fingerprint(envelope.presentation)
	var path=path_for(slot);var temporary=path+".tmp";var backup=path+".bak"
	var file=FileAccess.open(temporary,FileAccess.WRITE)
	if file==null:error="无法写入存档：%s"%FileAccess.get_open_error();return false
	file.store_string(JSON.stringify(envelope));file.flush();file.close()
	if read_verified(temporary).is_empty():error="临时存档校验失败";return false
	if FileAccess.file_exists(backup):DirAccess.remove_absolute(backup)
	if FileAccess.file_exists(path):
		if DirAccess.rename_absolute(path,backup)!=OK:error="无法保留上一份存档";return false
	if DirAccess.rename_absolute(temporary,path)!=OK:
		if FileAccess.file_exists(backup):DirAccess.rename_absolute(backup,path)
		error="提交存档失败，已保留备份";return false
	error="";return true

func read_verified(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):return {}
	var json=JSON.new()
	if json.parse(FileAccess.get_file_as_string(path))!=OK or not json.data is Dictionary:return {}
	var value=ContentRegistry.integerize(json.data)
	if value.get("schema_version",0) not in [1,2] or not value.get("payload") is Dictionary:return {}
	if value.get("checksum","")!=ContentRegistry.fingerprint(value.payload):return {}
	if value.has("presentation") and (not value.presentation is Dictionary or value.get("presentation_checksum","")!=ContentRegistry.fingerprint(value.presentation)):return {}
	return value

func load_slot(slot: String, expected_content_hash: String = "") -> Dictionary:
	last_presentation={}
	if not valid_slot(slot):error="存档槽无效";return {}
	var path=path_for(slot);var envelope=read_verified(path)
	if envelope.is_empty():envelope=read_verified(path+".bak")
	if envelope.is_empty():error="存档及备份无法读取";return {}
	if not expected_content_hash.is_empty() and envelope.content_hash!=expected_content_hash:error="存档属于另一版规则或地图";return {}
	var payload=envelope.payload
	if payload.has("scenario_id"):
		if payload.get("map",{}).has("_template_reference"):
			payload=unpack_map(payload,envelope.content_hash)
			if payload.is_empty():return {}
		if int(payload.get("schema_version",0))!=2:error="旧版战局缺少必要运行字段，请重新开局";return {}
		if not payload.get("map") is Dictionary or not payload.get("units") is Array:error="战局结构无效";return {}
		var random=payload.get("combat_random",{})
		if int(payload.get("ruleset_version",0))!=ContentRegistry.RUNTIME_RULESET_VERSION or not random is Dictionary or random.get("algorithm")!="park_miller_48271_v1" or int(random.get("state",0))<=0 or int(random.get("state",0))>=CombatRandom.MODULUS or int(random.get("draws",-1))<0:
			error="战局规则或随机战况记录无效，请重新开局";return {}
		StateAccess.freeze_map(payload.map)
	last_presentation=envelope.get("presentation",{}).duplicate(true)
	error="";return payload

func pack_map(payload: Dictionary, content_hash: String) -> Dictionary:
	if content==null or content_hash!=content.content_hash or not payload.has("scenario_id"):return payload
	var map=payload.get("map",{});var template=content.maps.get(map.get("id",""),{})
	if template.is_empty() or not map.has("dynamic_cell_offsets") or map.cells.size()!=template.cells.size():return payload
	for field in template:
		if field in ["cells","rail_edges"]:continue
		if not is_same(map.get(field),template[field]):return payload
	var offsets=map.dynamic_cell_offsets;var changed=[]
	if not is_same(map.cells,template.cells):
		for i in range(map.cells.size()):
			if offsets.has(str(i)):
				if map.cells[i].id!=template.cells[i].id or map.cells[i].position!=template.cells[i].position:return payload
				changed.append({"offset":i,"cell":map.cells[i]})
			elif not is_same(map.cells[i],template.cells[i]):return payload
	var compressed={"id":map.id,"_template_reference":{"format":1,"content_hash":content_hash},"_cell_changes":changed}
	for field in map:
		if field=="cells":continue
		if field in ["rail_edges","reference_pois","dynamic_cell_offsets"] or not template.has(field):compressed[field]=map[field]
	var result=payload.duplicate(false);result.map=compressed
	var full_fields=[];var full_ids=[]
	for i in range(payload.get("visibility",[]).size()):
		var sight=payload.visibility[i];var fields=[]
		for field in ["visible_cell_ids","explored_cell_ids"]:
			var ids=sight.get(field,[])
			if not ids is Array or not ids.is_read_only() or ids.size()!=map.cells.size():continue
			if full_ids.is_empty():full_ids=VisibilityRules.full_ids(map.cells)
			if ids==full_ids:fields.append(field)
		if fields.is_empty():continue
		if full_fields.is_empty():result.visibility=payload.visibility.duplicate(false)
		result.visibility[i]=sight.duplicate(false)
		for field in fields:result.visibility[i].erase(field)
		full_fields.append({"index":i,"faction_id":sight.faction_id,"fields":fields})
	if not full_fields.is_empty():result._full_visibility_reference=full_fields
	return result

func unpack_map(payload: Dictionary, saved_hash: String) -> Dictionary:
	var packed=payload.map;var reference=packed.get("_template_reference",{})
	if content==null or content.content_hash!=saved_hash or reference.get("content_hash","")!=saved_hash or reference.get("format",0)!=1:
		error="存档需要相同版本的地图资源";return {}
	var template=content.maps.get(packed.get("id",""),{})
	if template.is_empty():error="存档地图不存在";return {}
	var map=template.duplicate(false);map.rail_edges=template.rail_edges.duplicate(true)
	var changes=packed.get("_cell_changes",[]);var seen={}
	if not changes is Array:error="存档地图变化结构无效";return {}
	if not changes.is_empty():map.cells=template.cells.duplicate(false)
	for change in changes:
		if not change is Dictionary or not change.get("cell") is Dictionary:error="存档地形变化无效";return {}
		var offset=int(change.get("offset",-1))
		if offset<0 or offset>=template.cells.size() or seen.has(offset) or change.cell.get("id")!=template.cells[offset].id or change.cell.get("position")!=template.cells[offset].position:
			error="存档地形坐标无效";return {}
		seen[offset]=true;map.cells[offset]=change.cell
	for field in packed:
		if field not in ["id","_template_reference","_cell_changes"]:map[field]=packed[field]
	if not map.get("dynamic_cell_offsets") is Dictionary:error="存档地形索引无效";return {}
	var expected={}
	for offset in seen:expected[str(offset)]=true
	if map.dynamic_cell_offsets!=expected:error="存档地形索引不一致";return {}
	var result=payload.duplicate(false);result.map=map
	if payload.has("_full_visibility_reference"):
		var references=payload._full_visibility_reference
		if not references is Array or not payload.get("visibility") is Array:error="存档视野引用无效";return {}
		result.visibility=payload.visibility.duplicate(true)
		var full_ids=[];var restored={}
		for cell in map.cells:full_ids.append(cell.id)
		full_ids.make_read_only()
		for record in references:
			if not record is Dictionary or not record.get("fields") is Array:error="存档视野字段无效";return {}
			var index=int(record.get("index",-1))
			if index<0 or index>=result.visibility.size() or restored.has(index) or result.visibility[index].get("faction_id")!=record.get("faction_id"):error="存档视野所属势力无效";return {}
			restored[index]=true
			for field in record.fields:
				if field not in ["visible_cell_ids","explored_cell_ids"] or result.visibility[index].has(field):error="存档视野引用冲突";return {}
				result.visibility[index][field]=full_ids
		result.erase("_full_visibility_reference")
	return result

func list_slots() -> Array:
	var list: Array=[]
	for slot in ["manual_1","manual_2","manual_3","manual_4","manual_5","auto_1","auto_2","auto_3"]:
		var e=read_verified(path_for(slot));var recovery=false
		if e.is_empty():e=read_verified(path_for(slot)+".bak");recovery=not e.is_empty()
		list.append({"id":slot,"exists":not e.is_empty(),"saved_at":e.get("saved_at",""),"scenario_id":e.get("payload",{}).get("scenario_id",""),"round":e.get("payload",{}).get("round",0),"backup":recovery})
	return list

func valid_slot(slot: String) -> bool:return slot in ["manual_1","manual_2","manual_3","manual_4","manual_5","auto_1","auto_2","auto_3","profile","settings","test"]
