class_name GameAudio
extends Node

const RATE=22050
const SYNTH=preload("res://audio/audio_synth.gd")
const SFX=["ui_select","order_move","rifle","machine_gun","artillery","explosion","capture","rail","repair","skill","danger","victory","dice","air"]
var players: Array=[]
var music: AudioStreamPlayer
var music_fading: AudioStreamPlayer
var music_cache: Dictionary={}
var music_catalog: Dictionary={}
var fade_elapsed=2.4
var fading_gain=0.0
var combat_hold=0.0
const MUSIC_FADE_SECONDS=2.4
const COMBAT_HOLD_SECONDS=24.0
var enabled=true
var music_enabled=true
var sfx_volume=.65
var music_volume=.25
var cache: Dictionary={}
var cursor=0
var current_music=""
var action_speed=1.0

func stop_all() -> void:
	for p in players:
		if is_instance_valid(p):p.stop();p.stream=null
	if is_instance_valid(music):music.stop();music.stream=null
	if is_instance_valid(music_fading):music_fading.stop();music_fading.stream=null
	cache.clear();music_cache.clear();current_music="";combat_hold=0.0

func _exit_tree() -> void:stop_all()

func _ready() -> void:
	if DisplayServer.get_name()=="headless":return
	# Exported SFX are prepared before the menu. The first battle cue must not
	# synchronously load an imported sound in the middle of a command handoff.
	for id in SFX:
		var path="res://assets/audio/sfx/%s.wav"%id
		if ResourceLoader.exists(path):cache[id]=load(path)
	for i in range(8):
		var p=AudioStreamPlayer.new();add_child(p);players.append(p)
	music=AudioStreamPlayer.new();add_child(music)
	music_fading=AudioStreamPlayer.new();add_child(music_fading)
	var path="res://presentation/data/music_catalog.json"
	if FileAccess.file_exists(path):
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
		if parsed is Dictionary:music_catalog=parsed
	# OGG streams stay compressed. Prepare the three small resources before
	# gameplay, so a combat event never performs a synchronous disk import.
	for id in music_catalog.get("tracks",{}):
		var source=str(music_catalog.tracks[id].get("runtime_file",""))
		if ResourceLoader.exists(source):music_cache[id]=load(source)

func _process(delta: float) -> void:
	if music==null:return
	if combat_hold>0:
		combat_hold=maxf(0,combat_hold-delta)
		if combat_hold==0 and current_music=="battle":set_music("campaign")
	if not music_enabled:return
	fade_elapsed=minf(MUSIC_FADE_SECONDS,fade_elapsed+delta)
	apply_music_gain()
	if fade_elapsed>=MUSIC_FADE_SECONDS and music_fading.playing:music_fading.stop();music_fading.stream=null
	if music.playing and music.stream!=null:
		var remaining=music.stream.get_length()-music.get_playback_position()-AudioServer.get_time_since_last_mix()
		if remaining<=MUSIC_FADE_SECONDS and fade_elapsed>=MUSIC_FADE_SECONDS:
			# Audited originals have natural fades, not a claimed seamless edit.
			# Overlap the actual tail and head at runtime without changing bytes.
			switch_music_stream(music.stream)

func apply_music_gain() -> void:
	var phase=clampf(fade_elapsed/MUSIC_FADE_SECONDS,0,1)
	music.volume_db=linear_to_db(maxf(.000001,music_volume*sin(phase*PI*.5)))
	music_fading.volume_db=linear_to_db(maxf(.000001,music_volume*fading_gain*cos(phase*PI*.5)))

func switch_music_stream(stream: AudioStream) -> void:
	var old_gain=sin(clampf(fade_elapsed/MUSIC_FADE_SECONDS,0,1)*PI*.5) if music.playing else 0.0
	music_fading.stop();music_fading.stream=null
	var previous=music;music=music_fading;music_fading=previous
	music.stream=stream;fading_gain=old_gain;fade_elapsed=0.0
	apply_music_gain()
	if music_enabled:music.play()

static func make_sfx(id: String) -> AudioStreamWAV:
	var duration={"ui_select":.08,"order_move":.28,"rifle":.18,"machine_gun":.45,"artillery":.7,"explosion":.8,"capture":.5,"rail":.8,"repair":.45,"skill":.6,"danger":.7,"victory":1.6,"dice":.43,"air":1.1}.get(id,.2)
	var rng=RandomNumberGenerator.new();rng.seed=abs(id.hash())
	var bytes=PackedByteArray();bytes.resize(int(duration*RATE)*2)
	var smooth=0.0
	for i in range(int(duration*RATE)):
		var t=float(i)/RATE;var noise=SYNTH.noise(rng);smooth=lerpf(smooth,noise,.15);var sample=0.0
		match id:
			"ui_select":sample=sin(TAU*650*t)*exp(-t*55)*.22+smooth*exp(-t*80)*.08
			"order_move":sample=smooth*.35*exp(-fmod(t,.09)*40)+sin(TAU*90*t)*.12*exp(-t*8)
			"rifle":sample=noise*exp(-t*45)*.65+sin(TAU*(120-70*t)*t)*exp(-t*28)*.3
			"machine_gun":sample=noise*exp(-fmod(t,.09)*55)*.5+sin(TAU*95*t)*exp(-fmod(t,.09)*40)*.2
			"artillery":sample=sin(TAU*(62-30*t)*t)*exp(-t*7)*.6+smooth*exp(-t*9)*.4+noise*exp(-t*90)*.3
			"explosion":sample=smooth*exp(-t*6)*.65+sin(TAU*46*t)*exp(-t*7)*.3
			"capture":sample=(sin(TAU*392*t)+sin(TAU*523.25*t)*.5)*exp(-t*7)*.3
			"rail":sample=smooth*.3*exp(-fmod(t,.12)*25)+sin(TAU*440*t)*SYNTH.sfx_envelope(t,duration,.04,.5)*.07
			"repair":sample=(sin(TAU*960*t)*.17+noise*.15)*exp(-fmod(t,.15)*50)
			"skill":sample=(sin(TAU*(300+250*t)*t)*.22+sin(TAU*600*t)*.1)*SYNTH.sfx_envelope(t,duration,.08,.65)
			"dice":
				var local=fmod(t,.075);var pitch=730-95*int(t/.075)
				sample=(sin(TAU*pitch*t)*.23+noise*.18)*exp(-local*85)*exp(-t*3.5)
			"air":sample=(sin(TAU*79*t)*.20+sin(TAU*158*t)*.09+smooth*.17)*(0.7+0.3*sin(TAU*17*t))*SYNTH.sfx_envelope(t,duration,.18,.75)
			"danger":sample=sin(TAU*196*t)*.3*exp(-fmod(t,.35)*10)+sin(TAU*185*t)*.12*exp(-fmod(t,.35)*12)
			"victory":
				var frequencies=[261.63,329.63,392.0,523.25];var index=mini(3,int(t/.25));var local=fmod(t,.25)
				sample=sin(TAU*frequencies[index]*t)*.32*exp(-local*6)*minf(1,(duration-t)*3)
		sample*=minf(1,t*RATE/15)*minf(1,(duration-t)*150)
		bytes.encode_s16(i*2,int(clampf(sample,-.9,.9)*32767))
	var stream=AudioStreamWAV.new();stream.format=AudioStreamWAV.FORMAT_16_BITS;stream.mix_rate=RATE;stream.data=bytes;return stream

static func make_music(id: String) -> AudioStreamWAV:
	var seconds=16.0;var samples=int(seconds*RATE);var bytes=PackedByteArray();bytes.resize(samples*2)
	var notes=[0,3,7,10,7,5,3,0,0,5,7,12,10,7,5,3]
	if id=="battle":notes=[0,0,7,3,5,5,10,7,0,3,7,10,7,5,3,0]
	if id=="victory":notes=[0,4,7,12,7,9,7,4,0,4,7,9,12,9,7,4]
	var root=130.81 if id!="battle" else 110.0
	for i in range(samples):
		var t=float(i)/RATE;var local=fmod(t,1.0);var note=notes[int(t)%16];var frequency=root*pow(2.0,float(note)/12)
		var melody=(sin(TAU*frequency*t)+sin(TAU*frequency*2*t)*.2)*exp(-local*3)*.16
		var bass=sin(TAU*(root*.5 if int(t/4)%2==0 else root*.75)*t)*.07
		var drone=(sin(TAU*root*t)+sin(TAU*root*1.498*t))*.035
		var tick=sin(TAU*70*t)*exp(-fmod(t,.5)*45)*(.065 if id=="battle" else .025)
		var boundary=minf(1,t*3)*minf(1,(seconds-t)*3)
		bytes.encode_s16(i*2,int(clampf((melody+bass+drone+tick)*boundary,-.8,.8)*32767))
	var stream=AudioStreamWAV.new();stream.format=AudioStreamWAV.FORMAT_16_BITS;stream.mix_rate=RATE;stream.data=bytes;stream.loop_mode=AudioStreamWAV.LOOP_FORWARD;stream.loop_begin=0;stream.loop_end=samples;return stream

func play(id: String) -> void:
	if not enabled or players.is_empty():return
	if not cache.has(id):
		var path="res://assets/audio/sfx/%s.wav"%id;cache[id]=load(path) if ResourceLoader.exists(path) else make_sfx(id)
	var p=players[cursor%players.size()];cursor+=1;p.stream=cache[id];p.volume_db=linear_to_db(sfx_volume);p.pitch_scale=clampf(action_speed,.75,1.5) if id in ["order_move","rail","air","dice"] else 1.0;p.play()

func set_music(id: String) -> void:
	if music==null:return
	if id=="victory":id="menu"
	if id!="battle":combat_hold=0.0
	if current_music!=id:
		var stream: AudioStream=music_cache.get(id)
		if stream==null:
			var legacy_id="campaign" if id=="menu" else id
			var path="res://assets/audio/music/%s.wav"%legacy_id
			stream=load(path) if ResourceLoader.exists(path) else make_music(legacy_id)
		if stream is AudioStreamWAV:stream.loop_mode=AudioStreamWAV.LOOP_DISABLED
		elif stream is AudioStreamOggVorbis:stream.loop=false
		switch_music_stream(stream);current_music=id
	if music_enabled and not music.playing:
		fade_elapsed=0.0;fading_gain=0.0;music.play()
	elif not music_enabled:
		music.stop();music_fading.stop();fade_elapsed=MUSIC_FADE_SECONDS
	apply_music_gain()

func score_events(events: Array, status: String) -> void:
	# Presentation-only tension, independent of dice, AI and simulation time.
	if status!="playing":return
	for event in events:
		if str(event.get("type","")) in ["DamageApplied","UnitDefeated","CityCaptured"]:
			set_music("battle");combat_hold=COMBAT_HOLD_SECONDS;return

func on_events(events: Array, state: Dictionary, content: ContentRegistry) -> void:
	for e in events:
		match e.type:
			"UnitMoved":play("order_move")
			"DamageApplied":
				var attacker=StateAccess.find(state,"units",str(e.get("attacker_id")));var family=content.definition("units",attacker.get("def_id","")).get("family","")
				play("artillery" if family=="artillery" else ("machine_gun" if attacker.get("def_id")=="machine_gun" else "rifle"))
			"UnitDefeated":play("explosion")
			"CityCaptured":play("capture")
			"RailTransported":play("rail")
			"RailRepaired","FortRepaired","BuildingCompleted":play("repair")
			"SkillActivated":play("skill")
			"Attrition":play("danger")
			"MatchFinished":play("victory" if state.status=="won" else "danger");set_music("victory" if state.status=="won" else "campaign")
