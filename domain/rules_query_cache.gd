class_name RulesQueryCache
extends RefCounted

# Only the owning thread reads or resizes a context's containers. Main-thread
# rendering and the serialized rules worker must never share mutable indexes.
static var _main_context: RulesQueryCache
static var _contexts: Dictionary={}
static var _contexts_mutex=Mutex.new()
static var _main_thread_id=OS.get_main_thread_id()

var last_cells: Array=[]
var cell_index: Dictionary={}
var cell_offsets: Dictionary={}
var occupancy_sources: Dictionary={}
var occupancy_indexes: Dictionary={}
var visible_sources: Dictionary={}
var visible_counts: Dictionary={}
var visible_sets: Dictionary={}
var full_cells: Array=[]
var full_ids: Array=[]
var rail_source: Array=[]
var rail_date=""
var rail_version=-1
var rail_links: Dictionary={}
var crossing_source: Array=[]
var crossing_links: Dictionary={}
var reachable_source: Dictionary={}
var reachable_cells: Array=[]
var reachable_inputs: Dictionary={}
var reachable_graph: Dictionary={}

static func current() -> RulesQueryCache:
	var thread_id=OS.get_thread_caller_id()
	if thread_id==_main_thread_id:
		if _main_context==null:_main_context=RulesQueryCache.new()
		return _main_context
	_contexts_mutex.lock()
	if not _contexts.has(thread_id):_contexts[thread_id]=RulesQueryCache.new()
	var context: RulesQueryCache=_contexts[thread_id]
	_contexts_mutex.unlock()
	return context

static func release_current() -> void:
	var thread_id=OS.get_thread_caller_id()
	if thread_id==_main_thread_id:return
	_contexts_mutex.lock();_contexts.erase(thread_id);_contexts_mutex.unlock()
