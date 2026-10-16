"""Read-only field/name/license inspection for the archived primary sources."""
from pathlib import Path
import sys
import json

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import shapefile
import fitz

source=ROOT/'design/geodata/surface_detail_sources'
for path in source.rglob('*.shp'):
    reader=shapefile.Reader(str(path),encoding='cp1252' if 'Ecoregions' in path.name else 'utf-8')
    print(path.name, 'records', len(reader), 'fields', reader.fields, flush=True)
    if 'Ecoregions' in path.name:
        for record in reader.iterRecords():
            attrs=record.as_dict()
            if attrs['BIOME_NUM'] in [9,13] or any(word in str(attrs) for word in ['Taklimakan','Gobi','North China','Yellow Sea',
                'Manchurian','Alashan','Tarim','Qaidam','Ordos','Kachchh','Mesopotamian','Indus',
                'Ganges','Sundarbans','Huang','Mongolian','Rann','Terai','Yangtze','Plain','Gangetic','Changjiang']):
                print(json.dumps({key:attrs[key] for key in ['ECO_ID','ECO_NAME','BIOME_NUM','LICENSE']},ensure_ascii=True),flush=True)
for path in source.glob('*.pdf'):
    document=fitz.open(path)
    print(path.name, len(document), 'pages',flush=True)
    for index,page in enumerate(document):
        content=page.get_text()
        if any(word in content.lower() for word in ['license','attribution','commercial']):
            print('PAGE',index+1,content.encode('ascii','backslashreplace').decode('ascii'),flush=True)
