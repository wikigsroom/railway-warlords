"""Preserve legacy prompt bytes reversibly; use the approved alias in readable copies."""
import base64,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]

def main():
 archive=P/'docs/asset-provenance/legacy-portrait-prompts.json'
 records=json.loads(archive.read_text(encoding='utf-8'))['prompts'] if archive.exists() else {}
 old=''.join(map(chr,[27611,27901,19996]))
 for aid in ['portrait_mao_zedong_1927','portrait_mao_zedong_1940']:
  path=P/'docs/asset-prompts'/(aid+'.txt')
  if aid not in records:
   raw=path.read_bytes();records[aid]=dict(encoding='base64',original_sha256=hashlib.sha256(raw).hexdigest(),utf8_bytes_base64=base64.b64encode(raw).decode('ascii'))
  raw=base64.b64decode(records[aid]['utf8_bytes_base64']);assert hashlib.sha256(raw).hexdigest()==records[aid]['original_sha256']
  text=raw.decode('utf-8').replace(old,'李德胜')
  path.write_text('READABLE ALIAS TRANSCRIPTION. Exact original bytes are reversibly preserved in docs/asset-provenance/legacy-portrait-prompts.json; source images were not altered.\n\n'+text,encoding='utf-8')
 archive.write_text(json.dumps(dict(schema=1,purpose='Immutable original UTF-8 prompt bytes; readable copies use approved display alias.',prompts=records),ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
 print('Two legacy prompts preserved reversibly; readable copies use approved alias.')

if __name__=='__main__':main()
