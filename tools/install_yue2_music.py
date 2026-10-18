"""Install audited local YuE2 instrumentals, preserving all generation evidence."""
from pathlib import Path
import hashlib
import json
import shutil

from build_release import P, current_version

MUSIC_ROOT=Path('E:/dev/sandbox/模型配乐')
BATCH=MUSIC_ROOT/'output/YuE2/RailwayWarlords_20261017'
ROWS=[('menu','01_menu_embers'),('campaign','02_strategy_rivers'),('battle','03_battle_railfront')]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy_original(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha(source)!=sha(target):raise ValueError('Immutable music evidence differs: '+str(target))
    if not target.exists():shutil.copyfile(source,target)
    if sha(source)!=sha(target):raise ValueError('Music copy changed bytes')

def main():
    tracks={}
    for role,name in ROWS:
        job=BATCH/name
        state=json.loads((job/'state.json').read_text(encoding='utf-8'))
        # The actual saved manifest is authoritative, not a directory glob or a
        # requested target length. The skill's complete waveform audit must pass.
        delivery_path=job/'delivery.json'
        delivery=json.loads(delivery_path.read_text(encoding='utf-8'))
        audits=sorted(job.glob('verification/audit_*.json'))
        if not audits:raise ValueError('Missing full-decode music audit: '+name)
        audit_path=audits[-1];audit=json.loads(audit_path.read_text(encoding='utf-8'))
        if not audit.get('passed',False):raise ValueError('Music audit failed: '+name)
        spec=json.loads((job/'request.json').read_text(encoding='utf-8'))
        if spec.get('vocal') or spec.get('language')!='instrumental' or any('lyrics' in x for x in spec['sections']):raise ValueError('Vocal score is forbidden')
        if spec['duration_seconds']!=180:raise ValueError('Unexpected music length')
        files={Path(row['file']).suffix.lstrip('.'):row for row in delivery['files']}
        ogg=Path(files['ogg']['file']);wav=Path(files['wav']['file']);mp3=Path(files['mp3']['file'])
        for file in [ogg,wav,mp3]:
            if not file.is_relative_to(job) or not file.is_file():raise ValueError('Audio escaped its own job')
            expected=files[file.suffix.lstrip('.')]
            measured=next((row for row in audit['files'] if row['file']==str(file)),{})
            if sha(file)!=expected['sha256'] or measured.get('sha256')!=sha(file) or measured.get('samples_per_channel')!=8640000:
                raise ValueError('Audited music identity/sample count mismatch: '+str(file))
        runtime=P/'assets/audio/music'/f'{name}.ogg'
        copy_original(ogg,runtime)
        archive=P/'docs/music-provenance'/name
        for filename in ['request.json','score.abc','timeline.json','lyrics.txt','state.json','workflow_api.json','history.json','delivery.json']:
            copy_original(job/filename,archive/filename)
        raw=Path(delivery['source'])
        if not raw.is_relative_to(job) or raw.suffix!='.flac':raise ValueError('Unexpected generated original')
        copy_original(raw,archive/raw.name)
        copy_original(audit_path,archive/'waveform_audit.json')
        copy_original(mp3,P/'docs/audio'/f'{name}.mp3')
        copy_original(wav,P/'docs/audio'/f'{name}.wav')
        tracks[role]=dict(id=name,title=spec['title'],runtime_file='res://'+runtime.relative_to(P).as_posix(),
            runtime_sha256=sha(runtime),duration_seconds=180,bpm=spec['bpm'],key=spec['key'],vocal=False,
            production_route='music-gen-local-YuE2/native-Windows/offline',prompt_id=state['prompt_id'],
            source_job=str(job),source_delivery_sha256=sha(delivery_path),waveform_audit_sha256=sha(audit_path),
            raw_original='docs/music-provenance/'+name+'/'+raw.name,raw_original_sha256=sha(raw),
            raw_seconds=delivery['source_seconds'],master_tempo_ratio=delivery['tempo_ratio'],
            measured_loudness=delivery['measured_loudness'],
            spec='docs/music-provenance/'+name+'/request.json',score='docs/music-provenance/'+name+'/score.abc',
            mp3='docs/audio/'+name+'.mp3',wav='docs/audio/'+name+'.wav',
            subjective_listening_performed=False)
    catalog=dict(schema=1,production_version=current_version(),tracks=tracks,
                 no_voice_requested=True,no_dialogue_or_lyrics=True,source_audio_unmodified=True,
                 crossfade_seconds=2.4,combat_hold_seconds=24,legacy_procedural_wavs_retained=True)
    write(P/'presentation/data/music_catalog.json',catalog)
    write(P/'reports/music_installation.json',dict(passed=True,version=current_version(),tracks=tracks,
          source_audio_modified=False,rasters_added=0,subjective_listening_performed=False,physical_android_device_tested=False))
    print(json.dumps(dict(installed=len(tracks),total_seconds=540,version=current_version())))

if __name__=='__main__':main()
