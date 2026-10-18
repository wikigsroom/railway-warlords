class_name MusicPlaybackQA
extends RefCounted

# Native audio players, compressed stream decoding and crossfade lifecycle.
# This is a technical integration test, not a claim of subjective listening.
var checks: Array=[]
var failures: Array=[]
var audio: GameAudio
var app
static func run(application) -> void:
	var qa=MusicPlaybackQA.new();qa.app=application;await qa.execute()
func verify(value: bool, name: String) -> void:
	checks.append({"name":name,"passed":value})
	if not value:failures.append(name);push_error(name)

func report_path() -> String:
	var args=OS.get_cmdline_user_args();var index=args.find("--music-output")
	return args[index+1] if index>=0 and index+1<args.size() else "res://reports/music_native_tests.json"

func execute() -> void:
	app.audio.stop_all();app.audio.set_process(false)
	verify(DisplayServer.get_name()!="headless","native_audio_player_profile")
	audio=GameAudio.new();app.add_child(audio);await app.get_tree().process_frame
	audio.set_process(false)
	verify(audio.music_cache.size()==3 and audio.players.size()==8,"three_prepared_compressed_streams_and_existing_sfx_pool")
	var durations: Dictionary={}
	for id in ["menu","campaign","battle"]:
		var stream: AudioStream=audio.music_cache.get(id)
		verify(stream is AudioStreamOggVorbis and absf(stream.get_length()-180.0)<.001,"audited_three_minute_ogg:"+id)
		if stream!=null:durations[id]=stream.get_length()
	verify(AudioServer.get_mix_rate()==48000,"native_48khz_mixer")
	audio.set_music("menu");audio._process(1.2);await app.get_tree().create_timer(.12).timeout
	verify(audio.music.playing and audio.current_music=="menu" and audio.music.get_playback_position()>0,"menu_decoder_actually_advances")
	audio._process(1.2)
	var first=audio.music
	audio.set_music("campaign");audio._process(1.2);await app.get_tree().create_timer(.12).timeout
	verify(audio.music!=first and audio.music_fading==first and audio.music.playing and first.playing,"old_and_new_scores_overlap_during_transition")
	var total_power=pow(db_to_linear(audio.music.volume_db),2)+pow(db_to_linear(first.volume_db),2)
	verify(absf(total_power-pow(audio.music_volume,2))<.00001,"crossfade_preserves_equal_power_envelope")
	audio._process(1.2)
	verify(not audio.music_fading.playing and audio.music_fading.stream==null,"completed_fade_releases_previous_stream")
	audio.score_events([{"type":"UnitMoved"}],"playing")
	verify(audio.current_music=="campaign","movement_preserves_planning_music")
	audio.score_events([{"type":"DamageApplied"}],"playing");audio._process(2.4)
	verify(audio.current_music=="battle" and audio.combat_hold>0,"actual_combat_events_request_battle_score")
	audio._process(24.0)
	verify(audio.current_music=="campaign" and audio.combat_hold==0,"quiet_period_returns_to_strategic_score")
	audio._process(2.4);audio.music.seek(179.0);await app.get_tree().create_timer(.15).timeout
	var ending=audio.music;audio._process(.01);await app.get_tree().create_timer(.12).timeout
	verify(audio.music!=ending and audio.music.playing and ending.playing and audio.music.get_playback_position()<1,"track_tail_overlaps_fresh_head_without_raster_or_audio_edits")
	audio.music_enabled=false;audio.set_music(audio.current_music)
	verify(not audio.music.playing and not audio.music_fading.playing,"mute_stops_both_crossfade_players")
	audio.set_music("menu");audio.music_enabled=true;audio.set_music("menu");audio._process(1.2)
	verify(audio.current_music=="menu" and audio.music.playing and audio.combat_hold==0,"unmute_resumes_correct_menu_context")
	audio.set_music("victory");verify(audio.current_music=="menu","result_uses_coherent_main_theme_with_existing_victory_sfx")
	audio.stop_all();verify(not audio.music.playing and not audio.music_fading.playing and audio.music_cache.is_empty(),"shutdown_releases_compressed_streams")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"build_version":ContentRegistry.APP_VERSION,"track_durations":durations,"mix_rate":AudioServer.get_mix_rate(),"crossfade_seconds":GameAudio.MUSIC_FADE_SECONDS,"subjective_listening_performed":false,"physical_android_device_tested":false}
	var file=FileAccess.open(report_path(),FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	audio.queue_free();await app.get_tree().process_frame
	print("MUSIC_NATIVE_TEST ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));app.get_tree().quit(0 if report.passed else 1)
