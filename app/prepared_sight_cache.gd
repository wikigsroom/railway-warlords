class_name PreparedSightCache
extends RefCounted

# Only pure immutable ID arrays and dictionaries cross the worker boundary.
# Mutable/editor inputs are rebuilt. Each thread owns its cache slots.
static var _contexts: Dictionary={}
static var _mutex=Mutex.new()
var sources: Dictionary={}
var indexes: Dictionary={}

static func current() -> PreparedSightCache:
	var caller=OS.get_thread_caller_id()
	_mutex.lock()
	if not _contexts.has(caller):_contexts[caller]=PreparedSightCache.new()
	var context:PreparedSightCache=_contexts[caller]
	_mutex.unlock()
	return context

static func release_current() -> void:
	_mutex.lock();_contexts.erase(OS.get_thread_caller_id());_mutex.unlock()

func build(ids: Array, slot: String) -> Dictionary:
	if ids.is_read_only() and sources.has(slot) and is_same(sources[slot],ids):return indexes[slot]
	var values={}
	for id in ids:values[id]=true
	values.make_read_only()
	var ordered=values.keys();ordered.make_read_only()
	var result={"ids":values,"known":ordered}
	result.make_read_only()
	if ids.is_read_only():sources[slot]=ids;indexes[slot]=result
	return result
