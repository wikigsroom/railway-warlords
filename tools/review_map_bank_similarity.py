"""Analyze source similarity in memory; never write or modify a raster.

Independent generation and different PNG bytes alone do not prove variety.
This reports visually close pairs for native full-source review. Materials
deliberately share a quiet palette; silhouette tests apply to scenery/buildings.
"""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from PIL import Image
from build_release import P, ROOT
from map_bank_inventory import production_rows, ADDITIONAL_COUNT


def main():
    rows, complete = production_rows()
    families = defaultdict(list); hashes = set(); thumbnails = set()
    for row in rows:
        path = ROOT / row['source_file']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row['source_sha256']:
            raise RuntimeError('Immutable source changed: ' + row['id'])
        hashes.add(digest)
        with Image.open(path) as source:
            tiny = source.convert('RGBA').resize((24, 24))
            raw = tiny.tobytes(); thumbnails.add(hashlib.sha256(raw).hexdigest())
            pixels = list(tiny.get_flattened_data() if hasattr(tiny,'get_flattened_data') else tiny.getdata())
            occupancy = sum((1 << index) for index, rgba in enumerate(pixels) if rgba[3] >= 64)
            # A fixed olive backdrop is a numerical analysis reference, not a
            # saved composition. Premultiplication ignores invisible RGB noise.
            reference = []
            for red, green, blue, alpha in pixels:
                strength = alpha / 255
                reference.extend((red*strength + 146*(1-strength),
                                  green*strength + 157*(1-strength),
                                  blue*strength + 114*(1-strength)))
        families[row['family']].append(dict(id=row['id'], category=row['category'],
                                          occupancy=occupancy, reference=reference))
    candidates = []; nearest = []; pairs = 0
    for family, items in families.items():
        closest = None
        for index, a in enumerate(items):
            for b in items[index+1:]:
                pairs += 1
                union = (a['occupancy'] | b['occupancy']).bit_count()
                iou = ((a['occupancy'] & b['occupancy']).bit_count() / union) if union else 1.0
                mae = sum(abs(x-y) for x, y in zip(a['reference'], b['reference'])) / len(a['reference'])
                row = dict(family=family, first=a['id'], second=b['id'],
                           alpha_silhouette_iou=round(iou, 6), olive_backdrop_rgb_mae_0_255=round(mae, 6))
                if closest is None or mae < closest['olive_backdrop_rgb_mae_0_255']:
                    closest = row
                if a['category'] != 'tile' and iou >= .94 and mae <= 1.75:
                    candidates.append(row)
        if closest:
            nearest.append(closest)
    result = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), complete_catalog=complete,
                  passed=complete and len(rows)==ADDITIONAL_COUNT and len(hashes)==ADDITIONAL_COUNT and len(thumbnails)==ADDITIONAL_COUNT,
                  source_count=len(rows), independent_source_hashes=len(hashes),
                  independent_whole_canvas_rgba_24_fingerprints=len(thumbnails), analyzed_pairs=pairs,
                  source_files_modified=False, raster_files_written=False,
                  method='In-memory whole-canvas 24x24 RGBA fingerprint, alpha silhouette IoU and premultiplied RGB distance; no crop, mirror, source edit or stored composite',
                  near_duplicate_candidates=sorted(candidates, key=lambda row: row['olive_backdrop_rgb_mae_0_255']),
                  nearest_pair_per_family=nearest, formal_art_approval=False,
                  limitation='Similarity heuristics identify pairs for native full-original review. They do not measure EW6 parity, historical accuracy or final artistic approval.')
    (P / 'reports/map_bank_similarity_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ['passed','complete_catalog','source_count',
        'independent_source_hashes','independent_whole_canvas_rgba_24_fingerprints','analyzed_pairs']}
        | dict(near_duplicate_candidates=len(candidates)), ensure_ascii=False), flush=True)
    if complete and not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
