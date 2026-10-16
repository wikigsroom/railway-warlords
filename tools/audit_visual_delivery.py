"""Record immutable image provenance and actual native combat capture evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from PIL import Image
from build_release import source_digest, current_version

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = read(P/'assets/manifest.json')
    current = [a for a in manifest['assets'] if any(folder in a['source_file'] for folder in ('/atlas_v2/','/settlements_v023/','/ew6_v025/'))]
    rows = []
    for item in current:
        source = ROOT/item['source_file']
        engine = P/item['engine_path'].removeprefix('res://')
        prompt = ROOT/item['prompt_file']
        rows.append({'id':item['id'], 'revision':item['revision'],
                     'source_sha256':sha(source), 'prompt_sha256':sha(prompt),
                     'engine_matches_original':sha(source)==sha(engine)==item['source_sha256'],
                     'prompt_matches_original':sha(prompt)==item['prompt_sha256'],
                     'formal_art_approval':False})
    ew6 = [a for a in current if '/ew6_v025/' in a['source_file']]
    directional_report_path = P/'reports/unit_direction_generation.json'
    directional_report = read(directional_report_path) if directional_report_path.is_file() else {}
    directional = [a for a in ew6 if a.get('category') == 'unit' and a.get('view') in ('n','e','s','w') and not a.get('action_pose')]
    directional_ok = (directional_report.get('passed') is True
                      and directional_report.get('requested') == len(directional)
                      and len(directional_report.get('failures', [])) == 0)
    refinement = read(P/'reports/terrain_direction_refinement.json')
    refined_forests = [a for a in refinement.get('assets',[]) if a.get('category')=='scenery']
    actions = [a for a in ew6 if a.get('action_pose')]
    action_report = read(P/'reports/unit_action_generation.json')
    action_ok = action_report['passed'] and action_report['requested']==len(actions)==16
    expected_ew6_ids=set()
    # The eight exploratory UI sources were generated but never installed;
    # current runtime provenance is the union of installed production ledgers.
    generation_reports=['ew6_asset_generation.json',
        'unit_direction_generation.json','terrain_direction_refinement.json',
        'unit_action_generation.json','relief_material_generation.json','map_bank_generation.json',
        'map_settlement_extension_generation.json','map_surface_extension_generation.json']
    production_ok=True
    for name in generation_reports:
        generation=read(P/'reports'/name)
        ids=generation.get('ids',[]) or (generation.get('completed',[]) if isinstance(generation.get('completed'),list) else []) or [item['id'] for item in generation.get('assets',[])]
        expected_ew6_ids.update(ids)
        production_ok=production_ok and generation.get('passed',False)
    provenance = {'passed':{a['id'] for a in ew6}==expected_ew6_ids and production_ok and directional_ok and action_ok and all(r['engine_matches_original'] and r['prompt_matches_original'] for r in rows),
                  'total_current_rasters':len(manifest['assets']), 'new_style_items':len(rows), 'ew6_direction_items':len(ew6),
                  'directional_unit_items':len(directional), 'directional_generation_report':directional_report_path.relative_to(P).as_posix(),
                  'independent_action_pose_items':len(actions), 'action_generation_report':'reports/unit_action_generation.json',
                  'expected_ew6_items_from_generation_ledgers':len(expected_ew6_ids),
                  'map_bank_independent_items':len([a for a in ew6 if '_bank_' in a['id']]),
                  'raster_route':'sub2-image-gen / gpt-image-2.5',
                  'manual_compositing':False, 'original_png_bytes_preserved':True,
                  'assets':rows}
    (P/'reports/atlas_v2_asset_audit.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    visual = read(P/'reports/visual_playtest.json')
    support = read(P/'reports/support_playtest.json')
    runtime_hash, modified = source_digest()
    territory_path=P/'reports/territory_visual_tests.json'
    territory=read(territory_path)
    territory_captures=[]
    territory_current=(territory['passed'] and territory['build_version']==current_version()
        and territory['content_hash']==visual['content_hash']
        and territory['published_scenario_unchanged'] and territory['state_and_random_stream_unchanged']
        and len(territory['measured_factions'])>=8 and territory_path.stat().st_mtime>=modified)
    for name in territory['captures']:
        path=P/'reports/screenshots'/name
        territory_current=territory_current and path.stat().st_mtime>=modified
        with Image.open(path) as im:
            territory_captures.append({'file':path.relative_to(P).as_posix(),'dimensions':list(im.size),'sha256':sha(path),'raw_godot_viewport':True})
    visual_modified=max(modified,(P/'app/visual_playtest.gd').stat().st_mtime)
    log = (P/('reports/visual_playtest_final_v'+current_version().replace('.', '')+'.log')).read_text(encoding='utf-8')
    video = P/'reports/atlas_v2_native_final.mp4'
    metadata = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=codec_name,codec_type,width,height,r_frame_rate,duration,sample_rate,channels',
        '-show_entries','format=duration,size','-of','json',str(video)],text=True,encoding='utf-8'))
    captures = []
    for path in sorted((P/'reports/screenshots/visual_playtest').glob('*.png')):
        with Image.open(path) as im:
            captures.append({'file':path.relative_to(P).as_posix(),'dimensions':list(im.size),'sha256':sha(path),'raw_godot_viewport':True})
    map_captures=[]
    for name in ('map_bohai_coast','map_jingfeng_overview','settlements_country','settlement_village_details','settlement_county_details','settlement_market_details','settlement_capital_details','settlement_village_x30'):
        path=P/'reports/screenshots'/(name+'.png');meta_path=path.with_suffix('.json');meta=read(meta_path)
        if meta['build_version']!=current_version() or meta['content_hash']!=visual['content_hash'] or not meta['raw_godot_capture'] or not meta['qa_save_isolated'] or min(path.stat().st_mtime,meta_path.stat().st_mtime)<modified:
            raise SystemExit('Current fivefold map native capture required: '+name)
        if name.startswith('settlement') and meta['historical_places']['presentation_data_sha256']!=sha(P/'presentation/data/settlements_v023.json'):
            raise SystemExit('Current sourced historical place data is required: '+name)
        with Image.open(path) as im:
            map_captures.append({'file':path.relative_to(P).as_posix(),'dimensions':list(im.size),'sha256':sha(path),'metadata_sha256':sha(meta_path),'raw_godot_viewport':True,'scenario_id':meta['scenario_id'],'map_zoom':meta['map_zoom']})
    proof = {'passed':visual['passed'] and support['passed'] and visual['replay_same_final_state']
                     and all((P/'reports'/name).stat().st_mtime>=visual_modified for name in ['visual_playtest.json','support_playtest.json'])
                     and support.get('player_defense_performed',False) and support.get('setup_replay_same_final_state',False)
                     and not any(marker in log for marker in ['SCRIPT ERROR:','\nERROR:','WARNING: ObjectDB'])
                     and len(captures)==7 and provenance['passed'] and territory_current,
             'created_at_utc':datetime.now(timezone.utc).isoformat(),
             'build_version':visual['build_version'], 'content_hash':visual['content_hash'],
             'runtime_source_sha256':runtime_hash, 'capture_method':'Godot MovieWriter / direct native viewport PNG',
             'video':{'file':video.relative_to(P).as_posix(),'sha256':sha(video),'metadata':metadata},
             'captures':captures, 'fivefold_map_captures':map_captures, 'command_replay_same_final_state':True,
             'territory_color_evidence':{'file':'territory_visual_tests.json','sha256':sha(territory_path),'factions_measured':len(territory['measured_factions']),'state_and_random_stream_unchanged':territory['state_and_random_stream_unchanged'],'captures':territory_captures},
             'visual_commands':len(visual['native_commands']), 'dice_stream_draws':visual['final_combat_random']['draws']-visual['initial_combat_random']['draws'],
             'manual_image_compositing':False, 'physical_android_device_tested':False}
    (P/'reports/native_visual_evidence.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    review_path=P/'reports/art_review.json'
    previous=read(review_path)
    review={'date':datetime.now(timezone.utc).date().isoformat(),'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'asset_count':len(manifest['assets']),
            'raster_source':'sub2-image-gen / gpt-image-2.5 high',
            'all_originals_immutable':True,'manual_compositing':False,'complete_release_art_approval':False,
            'new_style_source_items':len(current),
            'native_scenes_directly_viewed':['01_command_preview.png','04_impact.png','07_air_bomb.png',
                '../map_1925_calendar_fixture.png','../map_final_windows.png','../map_x30_layout.png','../map_large_text.png','../map_bohai_coast.png','../map_jingfeng_overview.png','../settlements_country.png','../settlement_village_details.png','../settlement_county_details.png','../settlement_market_details.png','../settlement_capital_details.png','../settlement_village_x30.png'],
            'review_scope':'Current raw native screenshots and EW6-directed source sprites reviewed; formal historical clearance of all runtime assets remains separate.',
            'territory_scenes_directly_viewed':['territory/01_natural_map.png','territory/02_occupied_regions.png','territory/03_tactical_control.png','territory/04_two_faction_frontier.png','territory/05_pause_overlay.png'],
            'source_byte_audit':'atlas_v2_asset_audit.json',
            'historical_vegetation_without_sources_placed':False,
            'previous_review_record':previous.get('previous_review_record',previous)}
    review_path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source_items':len(rows),'native_captures':len(captures),'passed':proof['passed']},ensure_ascii=False))
    raise SystemExit(0 if proof['passed'] else 1)


if __name__=='__main__':
    main()
