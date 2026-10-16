"""Refine physical coast rendering from surveyed vectors without changing rules.

Natural Earth is a geographic approximation, not a 1924 harbor survey. Period
administrative layers, cities, crossings, grid classification and rails stay intact.
"""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(ROOT / ".toolchain/python-libs"))
import shapefile
from shapely.geometry import shape, box
from shapely.ops import transform, unary_union
from pyproj import Transformer

SOURCE = ROOT / "design/geodata/ne_10m_land"


def parts(geometry, kind):
    if geometry.is_empty:
        return []
    if geometry.geom_type == kind:
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for item in geometry.geoms for part in parts(item, kind)]
    return []


def main():
    with zipfile.ZipFile(SOURCE / "source.zip") as archive:
        for name in archive.namelist():
            target = (SOURCE / name).resolve()
            if not target.is_relative_to(SOURCE.resolve()):
                raise ValueError("Unsafe archive member")
            archive.extract(name, SOURCE)
    reader = shapefile.Reader(str(SOURCE / "ne_10m_land.shp"))
    geometries = [shape(item.__geo_interface__) for item in reader.shapes()]
    reports = []
    for path in sorted((PROJECT / "content/maps").glob("*.json")):
        if path.name == "catalog.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        authoritative = {key: value for key, value in data.items() if key not in ["render_land", "render_coast", "physical_detail_source"]}
        region = box(*data["geographic_bounds"])
        expanded = region.buffer(.10)
        physical = unary_union([geometry.intersection(expanded) for geometry in geometries if geometry.intersects(expanded)])
        forward = Transformer.from_crs("EPSG:4326", data["projection"], always_xy=True)
        extent = transform(forward.transform, region)
        minx, _, _, maxy = extent.bounds
        radius = data["hex_radius_m"]

        def coordinates(line):
            projected = transform(forward.transform, line).simplify(radius * .008)
            return [[round((x-minx)/radius*48, 2), round((maxy-y)/radius*48, 2)] for x, y in projected.coords]

        clipped = physical.intersection(region)
        coast = physical.boundary.intersection(region)
        old_vertices = sum(len(line) for line in data["render_coast"])
        data["render_land"] = [{"exterior": coordinates(polygon.exterior), "holes": [coordinates(ring) for ring in polygon.interiors]} for polygon in parts(clipped, "Polygon")]
        data["render_coast"] = [coordinates(line) for line in parts(coast, "LineString")]
        data["physical_detail_source"] = "natural_earth_land_10m_v5_1_1"
        unchanged = authoritative == {key: value for key, value in data.items() if key not in ["render_land", "render_coast", "physical_detail_source"]}
        if not unchanged:
            raise AssertionError("Authoritative fields changed: " + data["id"])
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        reports.append({"map_id": data["id"], "old_coast_vertices": old_vertices, "new_coast_vertices": sum(len(line) for line in data["render_coast"]), "rule_fields_unchanged": unchanged, "historical_administration_unchanged": True})
    file = SOURCE / "ne_10m_land.shp"
    source = {"id": "natural_earth_land_10m_v5_1_1", "title": "Natural Earth 1:10m Land v5.1.1", "url": "https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/", "download_url": "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_land.zip", "license": "Public domain", "use": "自然海岸的更细绘制；不宣称1924港池、填海或逐日海岸测绘精度。历史行政区仍采用对应年代研究矢量。", "access_date": "2026-10-11", "files": [file.relative_to(ROOT).as_posix()], "file_hashes": {file.relative_to(ROOT).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()}}
    manifest = PROJECT / "content/geography_sources.json"
    sources = json.loads(manifest.read_text(encoding="utf-8"))
    sources["sources"] = [item for item in sources["sources"] if item["id"] != source["id"]] + [source]
    manifest.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"passed": all(item["rule_fields_unchanged"] for item in reports), "source": source, "maps": reports, "manually_drawn_geography": False}
    (PROJECT / "reports/atlas_detail_geography.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "maps": reports}, ensure_ascii=True))


if __name__ == "__main__":
    main()
