"""Fetch primary-source vector geography using native Python, without a browser.

Downloaded originals are immutable. ZIP members are checked before extraction.
No raster generation, image processing, virtualization or historical claims.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'design/geodata/surface_detail_sources'
PAGES = {
    'ecoregions': 'https://ecoregions.world/',
    'hydrorivers': 'https://www.hydrosheds.org/products/hydrorivers',
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)


def request(url, timeout=40):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'RailwayWarlordsGeographicSourceAudit/0.2.12'}), timeout=timeout)


def source_links(only=''):
    result = {}
    for key, url in PAGES.items():
        if only and key!=only:continue
        with request(url) as response:
            content = response.read().decode('utf-8')
        parser = Links(); parser.feed(content)
        links = [urllib.parse.urljoin(url, link) for link in parser.links]
        result[key] = dict(page=url, links=sorted(set(link for link in links if
            any(word in link.lower() for word in ['.zip', '.pdf', 'creativecommons']))))
    return result


def download(url):
    target = DEST / urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/', 1)[-1])
    if not target.exists():
        temp = target.with_suffix(target.suffix + '.part')
        total = 0; last = time.monotonic()
        with request(url) as response, temp.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk); total += len(chunk)
                if time.monotonic() - last >= 15:
                    print(f'{target.name}: {total // (1024*1024)} MiB received', flush=True)
                    last = time.monotonic()
        temp.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if target.suffix.lower() == '.zip':
        folder = DEST / target.stem
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(target) as archive:
            for info in archive.infolist():
                resolved = (folder / info.filename).resolve()
                if not resolved.is_relative_to(folder.resolve()):
                    raise RuntimeError('ZIP path leaves source directory')
                if info.is_dir():
                    resolved.mkdir(parents=True, exist_ok=True); continue
                data = archive.read(info)
                if resolved.exists():
                    if resolved.read_bytes() != data:
                        raise RuntimeError('Refuse to overwrite an immutable source')
                else:
                    resolved.parent.mkdir(parents=True, exist_ok=True)
                    resolved.write_bytes(data)
    print(f'{target.name}: complete, {target.stat().st_size} bytes, SHA256 {digest}', flush=True)
    return dict(url=url, file=target.relative_to(ROOT).as_posix(), sha256=digest,
                size_bytes=target.stat().st_size)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--download', action='store_true')
    parser.add_argument('--direct', action='store_true', help='Use exact primary-host links already identified in the source research')
    parser.add_argument('--page', choices=['ecoregions','hydrorivers'])
    args = parser.parse_args(); DEST.mkdir(parents=True, exist_ok=True)
    links = ({
        'ecoregions': dict(page=PAGES['ecoregions'], links=[
            'https://storage.googleapis.com/teow2016/Ecoregions2017.zip',
            'https://creativecommons.org/licenses/by/4.0/']),
        'hydrorivers': dict(page=PAGES['hydrorivers'], links=[
            'https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip',
            'https://data.hydrosheds.org/file/technical-documentation/HydroRIVERS_TechDoc_v10.pdf',
            'https://data.hydrosheds.org/file/technical-documentation/HydroSHEDS_TechDoc_v1_4.pdf'])
    } if args.direct else source_links(args.page or ''))
    (DEST / 'primary_source_links.json').write_text(json.dumps(links, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(links, indent=2), flush=True)
    if not args.download:
        return
    urls = []
    urls.extend(url for url in links['ecoregions']['links'] if url.endswith('Ecoregions2017.zip'))
    urls.extend(url for url in links['hydrorivers']['links'] if
                'v10_as_shp.zip' in url or ('technical' in url.lower() and url.lower().endswith('.pdf')))
    if len([url for url in urls if url.endswith('.zip')]) != 2:
        raise RuntimeError('Expected exact ecoregions and Asia river download links on primary sites')
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(download, sorted(set(urls))))
    (DEST / 'sources.json').write_text(json.dumps(dict(
        primary_pages=PAGES, native_download=True, original_sources_modified=False,
        records=records), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
