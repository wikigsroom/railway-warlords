extends SceneTree

var checks: Array=[]
var failures: Array=[]
func _init() -> void:run.call_deferred()
func verify(ok: bool, name: String) -> void:
	checks.append({"name":name,"passed":ok})
	if not ok:failures.append(name);push_error(name)

func run() -> void:
	var library=AssetLibrary.new();var ids=MapArtBank.ids("pine_sparse").slice(0,6)
	verify(ids.size()==6,"actual_registered_originals_available")
	library.request_map_prefetch(ids+ids+["missing_bank_original_for_qa"])
	verify(library.map_prefetch_queue.size()==7,"duplicate_requests_coalesce")
	library.poll_map_prefetch()
	verify(library.map_prefetch_inflight.size()<=2,"background_concurrency_is_bounded")
	var began=Time.get_ticks_msec();var peak=library.map_prefetch_inflight.size()
	while not library.map_prefetch_queue.is_empty() or not library.map_prefetch_inflight.is_empty():
		library.poll_map_prefetch();peak=maxi(peak,library.map_prefetch_inflight.size())
		if Time.get_ticks_msec()-began>30000:break
		await create_timer(.01).timeout
	verify(library.map_prefetch_queue.is_empty() and library.map_prefetch_inflight.is_empty(),"all_own_requests_are_consumed_without_a_second_submission")
	verify(peak<=2 and library.map_prefetch_requested==6,"only_existing_originals_are_requested_once")
	for id in ids:
		var original=library.texture("scenery",id)
		verify(original!=null and original==ResourceLoader.load("res://assets/scenery/"+str(id)+".png"),"prefetch_returns_the_exact_imported_original_"+str(id))
	verify(library.synchronous_map_misses==0,"prepared_originals_need_no_synchronous_load_when_drawn")
	verify(library.texture("scenery","missing_bank_original_for_qa")==null,"missing_original_keeps_the_existing_null_fallback_contract")
	library.request_map_prefetch(ids)
	verify(library.map_prefetch_queue.is_empty(),"a_repeated_camera_region_does_not_reload_cached_originals")
	var more=MapArtBank.ids("pine_dense").slice(0,4)
	library.request_map_prefetch(more);library.poll_map_prefetch();library.request_map_prefetch([])
	began=Time.get_ticks_msec()
	while not library.map_prefetch_inflight.is_empty():
		library.poll_map_prefetch()
		if Time.get_ticks_msec()-began>30000:break
		await create_timer(.01).timeout
	verify(library.map_prefetch_queue.is_empty() and library.map_prefetch_inflight.is_empty(),"camera_change_drains_existing_workers_without_leaving_unobserved_jobs")
	verify(more.all(func(id):return not library.textures.has("scenery/"+str(id))),"obsolete_prefetch_results_do_not_fill_the_next_map_cache")
	library.request_map_prefetch(MapArtBank.ids("pine_sparse").slice(6,10));library.poll_map_prefetch()
	var draining=library.map_prefetch_inflight.values().duplicate()
	verify(draining.size()==2,"shutdown_check_starts_two_real_unconsumed_original_requests")
	library.finish_map_prefetch()
	verify(library.map_prefetch_queue.is_empty() and library.map_prefetch_inflight.is_empty(),"scene_shutdown_drains_our_own_pending_and_inflight_requests")
	verify(draining.all(func(path):return ResourceLoader.load_threaded_get_status(path)==ResourceLoader.THREAD_LOAD_INVALID_RESOURCE),"scene_shutdown_releases_the_engine_thread_load_task_handles")
	for i in 420:
		var key="scenery/qa_bank_"+str(i);library.textures[key]=null;library.touch_map_texture(key)
	verify(library.map_texture_order.size()==AssetLibrary.MAP_TEXTURE_CACHE_LIMIT,"prefetch_does_not_raise_the_existing_map_memory_entry_limit")
	verify(library.portrait_texture_order.is_empty(),"map_prefetch_never_reads_or_evicts_portraits")
	var result={"passed":failures.is_empty(),"checks":checks,"failures":failures,"peak_concurrent_requests":peak,"actual_originals_requested":library.map_prefetch_requested,"physical_android_device_tested":false}
	var file=FileAccess.open("res://reports/map_pan_v0233/prefetch_tests.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"\t"));file.close()
	print("MAP_PREFETCH_CHECKS ",checks.size()," passed=",failures.is_empty());quit(0 if failures.is_empty() else 1)
