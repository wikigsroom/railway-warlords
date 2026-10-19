"""Fetch immutable primary-source GSHHG vectors with the publisher's checksum.

Native Windows/Python only. No map, image, rule or historical record is edited.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import urllib.request
import zipfile

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
DEST = ROOT / 'design/geodata/gshhg_2_3_7'
URL = 'https://github.com/GenericMappingTools/gshhg-gmt/releases/download/2.3.7/gshhg-shp-2.3.7.zip'
EXPECTED = '8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / 'gshhg-shp-2.3.7.zip'
    if not target.exists():
        temporary = target.with_suffix('.zip.part')
        request = urllib.request.Request(URL, headers={'User-Agent': 'RailwayWarlordsGeography/0.2.26'})
        with urllib.request.urlopen(request, timeout=45) as response, temporary.open('wb') as output:
            total = 0
            previous = time.monotonic()
            while block := response.read(1024 * 1024):
                output.write(block)
                total += len(block)
                if time.monotonic() - previous > 15:
                    print(json.dumps({'downloaded_bytes': total}), flush=True)
                    previous = time.monotonic()
        if sha(temporary) != EXPECTED:
            raise RuntimeError('Publisher SHA256 differs; leave candidate uninstalled')
        temporary.replace(target)
    if sha(target) != EXPECTED:
        raise RuntimeError('Immutable archive differs from publisher SHA256')
    extracted = []
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Original archive CRC check failed')
        for info in archive.infolist():
            member = Path(info.filename)
            vector = member.suffix.lower() in {'.shp', '.shx', '.dbf', '.prj'} and any(
                member.stem == f'GSHHS_{resolution}_L{level}'
                for resolution in ['f', 'h', 'i'] for level in [1, 2, 3, 4])
            documentation = member.name.lower() in {'readme.txt', 'shapefiles.txt', 'copying', 'copyingv3',
                                                     'copying.lesser', 'copying.lesserv3', 'license', 'license.txt'}
            if info.is_dir() or not (vector or documentation):
                continue
            output = (DEST / member).resolve()
            if not output.is_relative_to(DEST.resolve()):
                raise RuntimeError('Archive path escapes source directory')
            data = archive.read(info)
            if output.exists():
                if output.read_bytes() != data:
                    raise RuntimeError('Refuse to overwrite original member: ' + str(member))
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
            extracted.append({'file': output.relative_to(ROOT).as_posix(), 'bytes': len(data),
                              'sha256': hashlib.sha256(data).hexdigest()})
    record = {'passed': True, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
              'source_id': 'gshhg_2_3_7', 'url': URL,
              'publisher_release': 'https://github.com/GenericMappingTools/gshhg-gmt/releases/tag/2.3.7',
              'primary_description': 'https://www.ngdc.noaa.gov/mgg/shorelines/shorelines.html',
              'file': target.relative_to(ROOT).as_posix(), 'sha256': EXPECTED,
              'publisher_sha256_matches': True, 'original_archive_crc_verified': True,
              'extracted': extracted, 'historical_coast_survey_claimed': False,
              'raw_sources_modified': False}
    (DEST / 'download_verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'archive_bytes': target.stat().st_size, 'extracted_members': len(extracted)}), flush=True)


if __name__ == '__main__':
    main()
