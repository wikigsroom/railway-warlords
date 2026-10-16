"""Record explicitly viewed whole-source native gallery pages, without editing images.

Call only for pages actually inspected in this session. Coverage and source
identity are separate from formal historical or commercial art approval.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from build_release import P, ROOT, current_version
from map_bank_inventory import production_rows, ADDITIONAL_COUNT


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('gallery', nargs='*', help='Already viewed native gallery filename stems')
    parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args()
    target = P/'reports/map_bank_visual_review.json'
    previous = read(target) if target.exists() else {}
    pages = {row['stem']: row for row in previous.get('viewed_pages', [])}
    for stem in args.gallery:
        if not re.fullmatch(r'[A-Za-z0-9_]+', stem):
            raise RuntimeError('Expected a native gallery filename stem')
        png = P/'reports/screenshots/map_bank'/(stem+'.png')
        meta_path = png.with_suffix('.json')
        meta = read(meta_path)
        if not (meta['passed'] and meta['build_version'] == current_version() and
                meta['raw_godot_viewport'] and meta['full_source_textures'] and
                not meta['manual_raster_compositing']):
            raise RuntimeError('Whole-source current native gallery required: '+stem)
        pages[stem] = dict(stem=stem, file=png.relative_to(P).as_posix(),
                           sha256=sha(png), metadata_sha256=sha(meta_path),
                           reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
                           sources=meta['sources'])
    produced, complete = production_rows(require_complete=args.finalize)
    sources = {row['id']: row['source_sha256'] for row in produced}
    viewed = {}
    for row in pages.values():
        path = P/row['file']
        if sha(path) != row['sha256'] or sha(path.with_suffix('.json')) != row['metadata_sha256']:
            raise RuntimeError('Reviewed gallery changed; inspect it again: '+row['stem'])
        for source in row['sources']:
            if sources.get(source['id']) != source['source_sha256'] or sha(ROOT/source['source_file']) != source['source_sha256']:
                raise RuntimeError('Inspected immutable source changed: '+source['id'])
            viewed[source['id']] = source['source_sha256']
    covered = complete and len(viewed) == ADDITIONAL_COUNT and set(viewed) == set(sources)
    if args.finalize and not covered:
        raise RuntimeError(f'Actual viewed-source coverage is incomplete: {len(viewed)}/{ADDITIONAL_COUNT}')
    report = dict(version=current_version(), reviewer='Codex whole-source visual inspection',
                  passed=bool(covered), viewed_independent_sources=len(viewed), expected_sources=ADDITIONAL_COUNT,
                  all_generated_sources_viewed=bool(covered), sources_match_immutable_originals=True,
                  image_files_modified=False, formal_art_approval=False, historical_art_approval=False,
                  ew6_visual_parity_claimed=False, viewed_pages=list(pages.values()),
                  scope='Whole-source palette, lighting, silhouette diversity, transparent edges and geographic suitability; final in-game views and formal release approval remain separate.',
                  selection_findings=[
                      'Flat riverbanks use only inspected low-grass originals 001--006; rock hummocks require existing relief.',
                      'Rocky shore originals require an existing hill/mountain/peak source cell.',
                      'Wetland reed variants 007/014/015/020/022/023 contain prominent rock mounds and are excluded from marsh selection.',
                      'Regional buildings are generic symbols; they are not measured reconstructions of named cities.',
                  ])
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['passed', 'viewed_independent_sources', 'expected_sources', 'formal_art_approval']}))


if __name__ == '__main__':
    main()
