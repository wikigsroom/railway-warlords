"""Set Godot import budgets. Original generated PNG bytes are never altered."""
from pathlib import Path
import re,json
P=Path(__file__).resolve().parents[1]
budgets={'unit':512,'portrait':512,'building':384,'scenery':512,'tile':512,'ui':768,'icon':128,'fx':256,'background':1920}
manifest=json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'))
individual={row['id']:int(row.get('runtime_import_max_dimension',budgets.get(row['category'],512))) for row in manifest['assets']}
count=0
for f in (P/'assets').rglob('*.png.import'):
    limit=min(budgets.get(f.parent.name,512),individual.get(f.stem.removesuffix('.png'),512));s=f.read_text(encoding='utf-8')
    s=re.sub(r'process/size_limit=\d+',f'process/size_limit={limit}',s)
    s=s.replace('mipmaps/generate=false','mipmaps/generate=true')
    f.write_text(s,encoding='utf-8');count+=1
(P/'reports/import_budgets.json').write_text(json.dumps({'import_files':count,'max_side_px':budgets,'individual_max_side_px':individual,'source_images_modified':False},indent=2),encoding='utf-8')
print(f'Configured {count} engine imports; generated source bytes preserved.')
