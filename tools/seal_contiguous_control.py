"""Bind scoped source checks and actually viewed normal viewports; no export claim."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

P=Path(__file__).resolve().parents[1]
R=P/'reports/ground_layers_v0238'
BASE='0926a6fbc55fa9734b7688481f89a07a02966db2'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=P)


def main():
    target=R/'scope01.json'
    if target.exists():raise FileExistsError('Immutable source-scope receipt')
    prefixes=['content','domain','ai','persistence','assets','presentation/data']
    changed=git('diff','--name-only',BASE,'--',*prefixes).decode('utf-8').splitlines()
    assert sorted(changed)==['content/content_registry.gd','presentation/data/coastal_control_asia.json',
                             'presentation/data/control_land_clip.json'],changed
    assert not git('ls-files','--others','--exclude-standard','--',*prefixes).strip()
    registry=git('show',BASE+':content/content_registry.gd')
    assert (P/'content/content_registry.gd').read_bytes()==registry.replace(b'APP_VERSION="0.2.37"',b'APP_VERSION="0.2.38"',1)
    assert 'config/version="0.2.38"' in (P/'project.godot').read_text(encoding='utf-8')
    presets=(P/'export_presets.cfg').read_text(encoding='utf-8')
    assert 'version/code=43' in presets and 'version/name="0.2.38"' in presets
    assert 'file_version="0.2.38.0"' in presets
    reports={name:read(R/name/'validation.json') for name in ['after01','rules01','relief01','control01']}
    identities={name:read(R/name/'identity.json') for name in reports}
    inputs=identities['after01']['working_code_and_data_sha256']
    for name,report in reports.items():
        assert report['passed'] and report['build_version']=='0.2.38'
        assert identities[name]['working_code_and_data_sha256']==inputs
        assert read(R/name/'result.json')['source_unchanged_during_run']
        log=(R/name/'native.log').read_text(encoding='utf-8',errors='replace')
        assert not any(s in log for s in ['SCRIPT ERROR:','SHADER ERROR:','\nERROR:'])
    assert [len(reports[n]['checks']) for n in ['rules01','relief01','control01','after01']]==[48,23,37,9]
    audit=read(R/'source_audit01.json');assert audit['passed']
    for name,checksum in audit['input_sha256'].items():assert sha(P/name)==checksum
    old=read(R/'vector_rebuild01/control_land_clip.json')['maps']['asia_strategic']
    new=read(P/'presentation/data/control_land_clip.json')['maps']['asia_strategic']
    assert old['city_zones']==new['city_zones'] and old['inland_water']==new['inland_water']
    capture_index={c['file']:c for c in reports['after01']['captures']}
    viewed=[]
    for name in ['himalaya_control.png','himalaya_natural.png','tianjin_control.png','tianjin_natural.png']:
        row=capture_index[name];path=R/'after01'/name
        assert row['ordinary_renderer'] and row['renderer_overrides']==[] and row['raw_godot_capture']
        assert sha(path)==row['sha256']
        viewed.append(dict(file=path.relative_to(P).as_posix(),sha256=row['sha256'],actually_viewed=True,
                           ordinary_source_renderer=True,shipping_exe=False))
    control=reports['control01']
    water=sum(c['water_pixels'] for c in control['cases'])
    assert water==1767 and max(c['water_max_channel_delta'] for c in control['cases'])==0
    changed_runtime=[p for p in git('diff','--name-only',BASE).decode('utf-8').splitlines()
                     if p.split('/')[0] in ['app','content','domain','ai','presentation','persistence','audio']
                     or p in ['project.godot','export_presets.cfg']]
    fresh={name:sha(P/name) for name in changed_runtime}
    assert all(inputs.get(name,checksum)==checksum for name,checksum in fresh.items())
    docs=['README.md','README.en.md','docs/00_程序文档索引.md','docs/23_当前完成度评估.md',
          'docs/60_控制填色接缝与基础网格去重.md']
    result=dict(review_completed=True,scope_checks_passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
                controller_sha256=sha(__file__),base_commit=BASE,version='0.2.38',
                protected_changes=changed,fresh_changed_runtime_sha256=fresh,
                native_check_counts={'control_rules':48,'relief_coastal':23,'normal_window_control':37,'camera_state':9},
                native_input_identity_reused_from_completed_captures=True,
                original_art_check='Unchanged tracked/untracked asset set against base Git revision; no new raw-PNG byte audit or new original-art approval claimed.',
                city_influence_and_inland_water_values_unchanged=True,water_samples=water,water_max_channel_delta=0,
                minimap_pixel_checks='5 skipped because the production HUD hides the minimap',
                actually_viewed_normal_source_viewports=viewed,visual_target_met=False,
                independent_geographic_audit_sha256=sha(R/'source_audit01.json'),
                native_precision_collapsed_triangle_count=len(audit['native_collapsed_triangles']),
                invalid_first_camera_preserved=True,
                new_windows_export=False,new_android_export=False,android_code_prepared_only=43,
                new_full_regression=False,latest_delivered_preview='0.2.37',
                new_raster_art=0,new_music_tracks=0,
                future_music_route='music-gen-remote-YuE2 / remote native Windows RTX 3080 / instrumental',
                physical_android_device_tested=False,formal_art_approval=False,
                remaining=['jagged city-influence borders','repeated landform silhouettes','sparse or uniform lowlands',
                           'crowded labels and units','historical administrative captions','complete unit actions',
                           'overall EW6 art and UI quality','0.2.38 dual-platform preview export','physical Motorola X30 acceptance'])
    with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    missing=[];links=0
    for name in docs:
        path=P/name;text=path.read_text(encoding='utf-8')
        for raw in re.findall(r'\]\(([^)]+)\)',text):
            dest=raw.strip().split(' "',1)[0].strip('<>')
            if not dest or dest.startswith(('#','http:','https:','app:','codex:','mailto:')):continue
            dest=unquote(dest.split('#',1)[0]);candidate=Path(dest)
            if not candidate.is_absolute():candidate=path.parent/candidate
            if not candidate.exists():missing.append([name,dest])
            links+=1
    assert not missing,missing
    summary=dict(passed=True,controller_sha256=sha(__file__),scope_sha256=sha(target),
                 documents_checked=len(docs),local_links_checked=links,missing_links=missing,
                 raw_png_art_bytes_rehashed=0,legacy_gif_playback_retested=False,
                 shipping_exe_checked=False,new_full_native_gate_run=False)
    with (R/'documentation01.json').open('x',encoding='utf-8',newline='\n') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
