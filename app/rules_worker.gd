class_name RulesWorker
extends RefCounted

# One FIFO worker for all controllers. It only runs data rules and save I/O;
# scene changes, signals, textures and the atomic state swap stay on the main thread.
static var _shared: RulesWorker
var _users=0
var _thread=Thread.new()
var _mutex=Mutex.new()
var _wake=Semaphore.new()
var _queue: Array[RulesJob]=[]
var _stopping=false

static func acquire() -> RulesWorker:
	assert(OS.get_thread_caller_id()==OS.get_main_thread_id())
	if _shared==null:
		_shared=RulesWorker.new()
		var error=_shared._thread.start(_shared._work)
		assert(error==OK,"Unable to start the serialized native rules worker")
	_shared._users+=1
	return _shared

func release() -> void:
	assert(OS.get_thread_caller_id()==OS.get_main_thread_id())
	_users-=1
	if _users>0:return
	_mutex.lock();_stopping=true
	for job in _queue:job.cancel()
	_queue.clear();_mutex.unlock();_wake.post()
	if _thread.is_started():_thread.wait_to_finish()
	RulesWorker._shared=null

func submit(kind: String, snapshot: Dictionary, arguments: Dictionary, content: ContentRegistry, planner: AIPlanner = null, presentation: Dictionary = {}) -> RulesJob:
	var job=RulesJob.new(kind,snapshot,arguments,content,planner,presentation)
	_mutex.lock();_queue.append(job);_mutex.unlock();_wake.post()
	return job

func _work() -> void:
	while true:
		_wake.wait();_mutex.lock()
		if _stopping:_mutex.unlock();break
		var job: RulesJob=_queue.pop_front() if not _queue.is_empty() else null
		_mutex.unlock()
		if job!=null:job.execute()
	RulesQueryCache.release_current()
	PreparedSightCache.release_current()
