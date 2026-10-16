extends RefCounted

var cache={}

func deeply_immutable(value: Variant) -> bool:
	if value is Array:
		if not value.is_read_only():return false
		for child in value:
			if not deeply_immutable(child):return false
	elif value is Dictionary:
		if not value.is_read_only():return false
		for key in value:
			if not deeply_immutable(value[key]):return false
	return true

func exact_hash(field: String, value: Variant) -> String:
	var records=cache.get(field,[])
	for record in records:
		if is_same(record.value,value):return record.hash
	var fingerprint=ContentRegistry.fingerprint(value)
	# A shallow read-only container is insufficient: every descendant must be
	# immutable before its original serialized SHA can be reused by identity.
	if deeply_immutable(value):
		records.append({"value":value,"hash":fingerprint});cache[field]=records
	return fingerprint

func state_hash(state: Dictionary) -> String:
	var payload=state.duplicate(false);payload.map=state.map.duplicate(false)
	for field in state.map:
		var value=state.map[field]
		if value is Array or value is Dictionary:
			payload.map[field]={"exact_serialized_sha256":exact_hash("map."+field,value)}
	payload.visibility=[]
	for sight in state.visibility:
		var copied=sight.duplicate(false)
		for field in sight:
			var value=sight[field]
			if value is Array or value is Dictionary:
				copied[field]={"exact_serialized_sha256":exact_hash("sight."+sight.faction_id+"."+field,value)}
		payload.visibility.append(copied)
	return ContentRegistry.fingerprint(payload)

func result_hash(result: Dictionary) -> String:
	var payload=result.duplicate(false)
	if payload.has("state"):payload.state={"all_state_fields_sha256":state_hash(result.state)}
	return ContentRegistry.fingerprint(payload)
