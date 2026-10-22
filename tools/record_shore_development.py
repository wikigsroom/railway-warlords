"""Retain actual whole-frame observations separately from technical acceptance."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json

from PIL import Image

P = Path(__file__).resolve().parents[1]
R = P / 'reports/shore_presentation_v0236'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['visual', 'summary'])
    parser.add_argument('--confirm-eight-whole-views', action='store_true')
    args = parser.parse_args()
    common = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), controller_sha256=sha(Path(__file__)),
                  development_only=True, shipping_binary_rebuilt=False, formal_art_approval=False,
                  physical_android_device_tested=False, overall_EW6_quality_goal_complete=False)
    if args.phase == 'visual':
        assert args.confirm_eight_whole_views
        assert not (R / 'visual_review01.json').exists() and not (R / 'official_reference_review01.json').exists()
        observations = {
            'shanhaiguan': '岸缘过渡较轻，水线与战场布局保持；来源台阶、岸边色块楔形和重复山体仍可见。',
            'tianjin': '较淡岸边与水面衔接保持；大面积相似地表、南侧泛白材质和上部控制色折角仍需处理。',
            'qingdao': '半岛、港湾和小岛有较克制的水侧淡洗；海岸折点、空旷地面与重复地貌仍明显。',
            'osaka': '相较被否决的osaka05，大范围碎岛光晕明显减轻；政治六边块、大面积相似地表及远景细节仍未达标。',
        }
        records = []
        for case, observation in observations.items():
            for phase, attempt in [('baseline', '01'), ('revised', '06')]:
                folder = R / phase / (case + attempt)
                result = read(folder / 'result.json'); metadata = read(folder / 'viewport.json')
                path = folder / 'viewport.png'
                assert result['passed'] and result['sha256'] == sha(path)
                assert metadata['raw_godot_capture'] and metadata['qa_save_isolated']
                with Image.open(path) as picture:
                    assert picture.size == (1920, 1080)
                records.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path),
                                    metadata_sha256=sha(folder / 'viewport.json'), phase=phase,
                                    whole_frame_actually_viewed=True, cropped_or_composited=False,
                                    observation=observation if phase == 'revised' else '已完整查看同相机基线，用于和本轮最终开发画面对照。'))
        save(R / 'visual_review01.json', dict(**common, final_whole_views=4, baseline_whole_views=4,
                                             images=records, rejected_broad_halo_view='revised/osaka05/viewport.png'))
        research = P.parents[1] / 'output/research/european_war_6'
        sources = [row for row in read(research / 'sources.json') if row['file'] in
                   {'manual_17.jpg', 'manual_18.jpg', 'manual_21.jpg', 'manual_27.jpg'}]
        assert len(sources) == 4 and all(sha(research / row['file']) == row['sha256'] for row in sources)
        save(R / 'official_reference_review01.json', dict(**common, sources=sources,
             reference_images_actually_viewed_whole=True, official_images_installed_as_game_assets=False,
             observation='参考暖色岸线与水侧柔和层次；本轮自有画面的地表、地貌、控制层及总体精细度仍有明显差距。'))
        print(json.dumps(dict(phase='visual', final_whole_views=4, baseline_whole_views=4, official_reference_images=4)))
        return
    target = R / 'development_summary01.json'
    assert not target.exists()
    native = read(R / 'revised/shore_rules06/validation.json')
    independent = read(R / 'shore_side_audit06.json')
    scope = read(R / 'protected_scope06.json')
    documents = read(R / 'repository_documentation01.json')
    visual = read(R / 'visual_review01.json')
    assert all(row['passed'] for row in [native, independent, scope, documents])
    maps = native['maps']
    save(target, dict(**common, passed=True,
         scope='Shore display development and evidence; packages remain 0.2.35/code40.',
         native_checks=len(native['checks']), independent_report_checks=len(independent['checks']),
         independent_checks_are_not_gameplay_coverage=True,
         exact_centerline_vertices_checked=sum(row['native_source_vertices_checked'] for row in maps),
         source_classified_lines=sum(row['source_land_classified_lines'] for row in maps),
         neutral_source_fragments=sum(row['neutral_fallback_lines'] for row in maps),
         protected_unchanged_files=scope['protected_unchanged_files'], unchanged_png_files=scope['unchanged_png_files'],
         changed_production_files=[row['file'] for row in scope['changed_production_files']],
         visual_review_sha256=sha(R / 'visual_review01.json'), final_whole_views=visual['final_whole_views'],
         native_content_hash=native['native_content_hash'], new_raster_assets=False, new_music=False,
         full_thirty_group_regression_repeated=False,
         remaining=['来源海岸台阶与岸边色块楔形', '地表及山体重复', '政治块与地图细节', '全兵种完整动作', '历史起局与将领具体部署', '物理X30验收']))
    print(json.dumps(dict(phase='summary', passed=True, native_checks=len(native['checks']),
                         source_classified_lines=sum(row['source_land_classified_lines'] for row in maps))))


if __name__ == '__main__':
    main()
