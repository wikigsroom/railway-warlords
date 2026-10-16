"""Build the Asian strategic map from the project's Natural Earth vector sources.

The runtime uses a 48 px hex radius.  This compiler keeps that radius unchanged,
but uses one-degree longitude bands and half-degree staggered latitude bands so
the player receives a continent scale map without turning the strategic grid
into a pixel-art world map.  Political control is scenario data; Natural Earth
is used only for present-day physical land/water geometry and the source record
explicitly says so.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".toolchain/python-libs"))

import shapefile  # type: ignore
from shapely.geometry import Point, box, shape  # type: ignore
from shapely.ops import transform, unary_union  # type: ignore
from shapely.prepared import prep  # type: ignore

MAP_ID = "asia_strategic"
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 20.0, -10.0, 180.0, 80.0
RADIUS = 48.0
# The grid remains the engine's 48px control hex.  A 1.5° strategic band keeps
# the entire continent responsive on Android while retaining city, port, river
# and rail nodes at a readable zoom.  The exact scale is declared in the map.
LON_STEP = 1.5
LAT_STEP = math.sqrt(3.0) / 2.0 * LON_STEP
SOURCES = [
    "natural_earth_land_50m",
    "natural_earth_rivers_10m",
    "asia_city_coordinates",
    "asia_strategic_terrain_method",
]


def world(lon: float, lat: float) -> tuple[float, float]:
    q = (lon - LON_MIN) / LON_STEP
    r = (LAT_MAX - lat) / LAT_STEP - q * 0.5
    return (round(1.5 * RADIUS * q, 2), round(math.sqrt(3.0) * RADIUS * (r + q * 0.5), 2))


def hex_position(lon: float, lat: float) -> tuple[int, int]:
    q = round((lon - LON_MIN) / LON_STEP)
    # Odd columns are offset by half a latitude band.  Keeping the offset in
    # r, rather than changing the engine's hex geometry, preserves the 48 px
    # control grid on every platform.
    band = round((LAT_MAX - lat) / LAT_STEP)
    return q, band - q // 2


def pos(q: int, r: int) -> dict[str, int]:
    return {"q": int(q), "r": int(r)}


def walk_geometries(geo) -> Iterable:
    if geo.is_empty:
        return
    if geo.geom_type == "Polygon":
        yield geo
    elif geo.geom_type in ("MultiPolygon", "GeometryCollection"):
        for child in geo.geoms:
            yield from walk_geometries(child)


def walk_lines(geo) -> Iterable:
    if geo.is_empty:
        return
    if geo.geom_type == "LineString":
        yield geo
    elif geo.geom_type in ("MultiLineString", "GeometryCollection"):
        for child in geo.geoms:
            yield from walk_lines(child)


def rounded_line(coords, precision=2):
    """Preserve open hydrography; rounding must never invent a closing chord."""
    return [[round(float(x), precision), round(float(y), precision)] for x, y in coords]


def rounded_ring(coords, precision=2):
    result = rounded_line(coords, precision)
    if len(result) > 1 and result[0] != result[-1]:
        result.append(result[0])
    return result


def load_land_and_rivers():
    land_path = ROOT / "design/geodata/ne_50m_land/ne_50m_land.shp"
    river_path = ROOT / "design/geodata/ne_10m_rivers_lake_centerlines/ne_10m_rivers_lake_centerlines.shp"
    clip = box(LON_MIN - 1, LAT_MIN - 1, LON_MAX + 1, LAT_MAX + 1)
    land_parts = []
    for record in shapefile.Reader(str(land_path)).iterShapes():
        geo = shape(record.__geo_interface__)
        if geo.intersects(clip):
            land_parts.append(geo.intersection(clip))
    land = unary_union(land_parts)
    rivers = []
    river_names = []
    reader = shapefile.Reader(str(river_path), encoding="utf-8")
    wanted = ("yangtze", "chang jiang", "huang", "yellow", "ganges", "brahmaputra", "indus", "mekong", "amur", "ob", "irtysh", "syr", "amu", "tigris", "euphr")
    for item in reader.iterShapeRecords():
        attrs = item.record.as_dict()
        name = str(attrs.get("name", "") or attrs.get("name_en", ""))
        geo = shape(item.shape.__geo_interface__)
        if not geo.intersects(clip):
            continue
        if int(attrs.get("scalerank", 10) or 10) <= 4 or any(word in name.lower() for word in wanted):
            rivers.append(geo.intersection(clip))
            river_names.append(name)
    return land, rivers, river_names


# Coordinates are longitude/latitude from the named historical or geographic
# gazetteer.  A `bloc` is a scenario deployment category, never a claimed
# continuous military frontier.  The release docs list each timeline's
# control interpretation and source status.
CITY_ROWS = [
    # China and adjacent treaty ports / frontier nodes.
    ("beijing", "北京", "Peking", 116.407, 39.904, 3, "qing_core", "national_capital", False),
    ("tianjin", "天津", "Tientsin", 117.203, 39.084, 3, "qing_core", "capital", True),
    ("baoding", "保定", "Paoting", 115.480, 38.870, 2, "qing_core", "capital", False),
    ("shijiazhuang", "石家庄", "Shihkiachwang", 114.510, 38.040, 2, "qing_core", "city", False),
    ("jinan", "济南", "Tsinan", 117.120, 36.650, 2, "qing_core", "capital", False),
    ("qingdao", "青岛", "Tsingtao", 120.382, 36.067, 2, "treaty_port", "city", True),
    ("shanghai", "上海", "Shanghai", 121.474, 31.230, 3, "treaty_port", "city", True),
    ("nanjing", "南京", "Nanking", 118.796, 32.060, 3, "qing_core", "national_capital", True),
    ("suzhou", "苏州", "Soochow", 120.585, 31.299, 1, "qing_core", "county", False),
    ("hangzhou", "杭州", "Hangchow", 120.155, 30.274, 2, "qing_core", "capital", False),
    ("ningbo", "宁波", "Ningpo", 121.550, 29.874, 1, "treaty_port", "city", True),
    ("xuzhou", "徐州", "Suchow", 117.285, 34.205, 2, "qing_core", "city", False),
    ("bengbu", "蚌埠", "Pengpu", 117.389, 32.917, 1, "qing_core", "county", False),
    ("hankou", "汉口", "Hankow", 114.292, 30.582, 3, "qing_core", "city", True),
    ("wuchang", "武昌", "Wuchang", 114.316, 30.548, 2, "qing_core", "capital", False),
    ("yichang", "宜昌", "Ichang", 111.286, 30.692, 1, "qing_core", "city", True),
    ("changsha", "长沙", "Changsha", 112.938, 28.228, 2, "qing_core", "capital", False),
    ("nanchang", "南昌", "Nanchang", 115.858, 28.683, 2, "qing_core", "capital", False),
    ("fuzhou", "福州", "Foochow", 119.297, 26.074, 2, "qing_core", "capital", True),
    ("guangzhou", "广州", "Canton", 113.264, 23.129, 3, "qing_core", "capital", True),
    ("hong_kong", "香港", "Hong Kong", 114.170, 22.319, 2, "treaty_port", "city", True),
    ("macau", "澳门", "Macao", 113.543, 22.198, 1, "treaty_port", "city", True),
    ("shantou", "汕头", "Swatow", 116.682, 23.354, 1, "qing_core", "market", True),
    ("nanning", "南宁", "Nanning", 108.320, 22.817, 2, "qing_core", "capital", False),
    ("guilin", "桂林", "Kweilin", 110.299, 25.274, 2, "qing_core", "capital", False),
    ("kunming", "昆明", "Yunnan-fu", 102.833, 24.881, 3, "qing_core", "capital", False),
    ("guiyang", "贵阳", "Kweiyang", 106.630, 26.647, 2, "qing_core", "capital", False),
    ("chongqing", "重庆", "Chungking", 106.551, 29.563, 2, "qing_core", "city", False),
    ("chengdu", "成都", "Chengtu", 104.066, 30.573, 3, "qing_core", "capital", False),
    ("xian", "西安", "Sian", 108.940, 34.342, 2, "qing_core", "capital", False),
    ("lanzhou", "兰州", "Lanchow", 103.834, 36.061, 2, "qing_frontier", "capital", False),
    ("xining", "西宁", "Sining", 101.778, 36.617, 1, "qing_frontier", "city", False),
    ("urumqi", "迪化", "Urumchi", 87.617, 43.825, 2, "qing_frontier", "capital", False),
    ("kashgar", "喀什噶尔", "Kashgar", 75.990, 39.470, 1, "qing_frontier", "market", False),
    ("lhasa", "拉萨", "Lhasa", 91.133, 29.650, 2, "qing_frontier", "capital", False),
    ("mukden", "奉天", "Mukden", 123.432, 41.805, 3, "manchuria", "capital", False),
    ("port_arthur", "旅顺", "Port Arthur", 121.640, 38.800, 2, "manchuria", "port", True),
    ("dalian", "大连", "Dairen", 121.615, 38.914, 2, "manchuria", "city", True),
    ("changchun", "长春", "Changchun", 125.324, 43.886, 2, "manchuria", "city", False),
    ("harbin", "哈尔滨", "Harbin", 126.642, 45.757, 3, "manchuria", "city", False),
    ("taipei", "台北", "Taihoku", 121.565, 25.033, 2, "japan", "capital", True),
    ("haiphong", "海防", "Haiphong", 105.844, 20.845, 2, "indochina", "port", True),
    # Japan, Korea, and the Russian Far East.
    ("tokyo", "东京", "Tokyo", 139.692, 35.690, 3, "japan", "national_capital", True),
    ("yokohama", "横滨", "Yokohama", 139.638, 35.444, 2, "japan", "port", True),
    ("osaka", "大阪", "Osaka", 135.502, 34.694, 3, "japan", "city", True),
    ("hiroshima", "广岛", "Hiroshima", 132.455, 34.385, 2, "japan", "city", True),
    ("sapporo", "札幌", "Sapporo", 141.354, 43.062, 2, "japan", "capital", False),
    ("seoul", "汉城", "Keijo/Seoul", 126.978, 37.566, 3, "korea", "capital", False),
    ("pyongyang", "平壤", "Heijo/Pyongyang", 125.753, 39.039, 2, "korea", "capital", False),
    ("busan", "釜山", "Fusan/Busan", 129.075, 35.180, 2, "korea", "port", True),
    ("vladivostok", "海参崴", "Vladivostok", 131.886, 43.116, 2, "russia", "port", True),
    ("khabarovsk", "伯力", "Khabarovsk", 135.070, 48.480, 2, "russia", "city", False),
    ("irkutsk", "伊尔库茨克", "Irkutsk", 104.281, 52.287, 2, "russia", "capital", False),
    ("petrograd", "彼得格勒", "Petrograd", 30.335, 59.934, 3, "russia", "national_capital", True),
    ("moscow", "莫斯科", "Moscow", 37.618, 55.756, 3, "russia", "national_capital", False),
    ("tashkent", "塔什干", "Tashkent", 69.240, 41.299, 2, "russia", "capital", False),
    ("samarkand", "撒马尔罕", "Samarkand", 66.959, 39.654, 1, "russia", "city", False),
    ("baku", "巴库", "Baku", 49.867, 40.409, 2, "russia", "port", True),
    ("tbilisi", "第比利斯", "Tiflis/Tbilisi", 44.783, 41.716, 2, "russia", "capital", False),
    ("ulaanbaatar", "库伦", "Urga/Ulaanbaatar", 106.906, 47.886, 2, "mongolia", "capital", False),
    # Central and South-West Asia.
    ("tehran", "德黑兰", "Tehran", 51.389, 35.689, 3, "persia", "national_capital", False),
    ("tabriz", "大不里士", "Tabriz", 46.292, 38.096, 2, "persia", "city", False),
    ("baghdad", "巴格达", "Baghdad", 44.366, 33.315, 3, "ottoman", "capital", False),
    ("istanbul", "君士坦丁堡", "Constantinople/Istanbul", 28.978, 41.008, 3, "ottoman", "national_capital", True),
    ("jerusalem", "耶路撒冷", "Jerusalem", 35.214, 31.769, 2, "ottoman", "city", False),
    ("kabul", "喀布尔", "Kabul", 69.208, 34.555, 2, "afghanistan", "national_capital", False),
    ("delhi", "德里", "Delhi", 77.209, 28.614, 3, "british_india", "capital", False),
    ("lahore", "拉合尔", "Lahore", 74.358, 31.520, 2, "british_india", "city", False),
    ("bombay", "孟买", "Bombay/Mumbai", 72.878, 19.076, 3, "british_india", "port", True),
    ("calcutta", "加尔各答", "Calcutta/Kolkata", 88.364, 22.572, 3, "british_india", "capital", True),
    ("madras", "马德拉斯", "Madras/Chennai", 80.271, 13.083, 2, "british_india", "port", True),
    ("rangoon", "仰光", "Rangoon/Yangon", 96.173, 16.840, 2, "british_india", "port", True),
    ("mandalay", "曼德勒", "Mandalay", 96.089, 21.958, 2, "british_india", "city", False),
    # South-East Asia and colonial ports.
    ("bangkok", "曼谷", "Bangkok", 100.502, 13.756, 3, "siam", "national_capital", False),
    ("hanoi", "河内", "Hanoi", 105.834, 21.028, 2, "indochina", "capital", False),
    ("saigon", "西贡", "Saigon/Ho Chi Minh City", 106.630, 10.823, 2, "indochina", "port", True),
    ("phnom_penh", "金边", "Phnom Penh", 104.928, 11.556, 2, "indochina", "capital", False),
    ("singapore", "新加坡", "Singapore", 103.820, 1.352, 2, "british_colony", "port", True),
    ("manila", "马尼拉", "Manila", 120.984, 14.599, 3, "philippines", "port", True),
    ("batavia", "巴达维亚", "Batavia/Jakarta", 106.845, -6.208, 2, "dutch", "port", True),
    ("surabaya", "泗水", "Surabaya", 112.752, -7.257, 2, "dutch", "port", True),
]


def rail_path(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    # Cube interpolation gives contiguous axial coordinates for the hand-authored
    # strategic rail corridors.  It is a route abstraction between real stations.
    dq, dr = b[0] - a[0], b[1] - a[1]
    n = max(abs(dq), abs(dr), abs(dq + dr))
    if n == 0:
        return [a]
    result = []
    for i in range(n + 1):
        t = i / n
        x = a[0] + dq * t
        z = a[1] + dr * t
        y = -x - z
        cube = [round(x), round(y), round(z)]
        diffs = [abs(cube[0] - x), abs(cube[1] - y), abs(cube[2] - z)]
        idx = diffs.index(max(diffs))
        cube[idx] = -sum(cube[j] for j in range(3) if j != idx)
        value = (int(cube[0]), int(cube[2]))
        if not result or result[-1] != value:
            result.append(value)
    return result


RAIL_CORRIDORS = [
    ("trans_siberian", "西伯利亚铁路", "1904-01-01", ["moscow", "irkutsk", "khabarovsk", "vladivostok"]),
    ("south_manchuria", "南满铁路走廊", "1903-01-01", ["harbin", "changchun", "mukden", "dalian", "port_arthur"]),
    ("korea_mainline", "京釜铁路走廊", "1905-01-01", ["seoul", "busan"]),
    ("japan_mainline", "东海道铁路走廊", "1889-01-01", ["tokyo", "yokohama", "osaka", "hiroshima"]),
    ("indian_east", "印度东部铁路走廊", "1870-01-01", ["calcutta", "delhi"]),
    ("burma_corridor", "缅甸铁路走廊", "1880-01-01", ["rangoon", "mandalay"]),
    ("persian_corridor", "波斯陆路走廊", "0001-01-01", ["tehran", "tabriz"]),
    ("china_north_south", "中国南北铁路战略走廊", "1906-01-01", ["beijing", "tianjin", "shijiazhuang", "zhengzhou", "hankou"]),
    ("china_east", "中国东部铁路战略走廊", "1908-01-01", ["nanjing", "shanghai", "hangzhou"]),
    ("china_yangtze", "长江航运走廊", "0001-01-01", ["nanjing", "wuchang", "hankou", "yichang"]),
    ("indochina", "印度支那铁路走廊", "1910-01-01", ["hanoi", "saigon"]),
]


def terrain_for(lon: float, lat: float, land_prepared, river_geos) -> tuple[str, str]:
    if not land_prepared.covers(Point(lon, lat)):
        return "sea", "Natural_Earth_land_water"
    # Temporary land class only. Actual relief is applied from the immutable
    # physical DEM cache before the compiler can return or publish this map.
    return "plain", "Natural_Earth_land_water"


def scenario_owner(bloc: str, scenario_id: str, city_id: str) -> str:
    # Scenario-level control is an authored starting deployment, not a claim that
    # every square kilometre was continuously garrisoned by that faction.
    base = {
        "qing_core": "qing", "qing_frontier": "qing", "manchuria": "qing",
        "treaty_port": "qing", "japan": "japan", "korea": "korea",
        "russia": "russian_empire", "mongolia": "qing", "persia": "qajar_persia",
        "ottoman": "ottoman", "afghanistan": "afghanistan", "british_india": "british_india",
        "british_colony": "british_empire", "siam": "siam", "indochina": "nguyen_dynasty",
        "philippines": "spain", "dutch": "netherlands",
    }.get(bloc, "qing")
    if scenario_id == "asia_1840":
        # 1840 predates the British cession of Hong Kong, the opening of
        # treaty ports, the Japanese annexation of Taiwan, and French rule in
        # Indochina.  These nodes therefore remain with the period polity.
        if city_id == "macau": return "portugal"
        if city_id in {"hong_kong", "shanghai", "ningbo", "qingdao", "taipei"}: return "qing"
        if city_id in {"rangoon", "mandalay"}: return "burmese_kingdom"
        if city_id == "lahore": return "sikh_empire"
        if city_id == "phnom_penh": return "siam"
        return base
    if scenario_id == "asia_1860":
        if city_id in {"nanjing", "suzhou", "hangzhou", "wuchang", "hankou", "changsha"}:
            return "taiping"
        if city_id == "macau": return "portugal"
        if city_id in {"hong_kong", "shanghai", "ningbo", "qingdao", "taipei"}: return "qing"
        if city_id == "saigon": return "french_empire"
        if city_id == "phnom_penh": return "siam"
        if city_id == "mandalay": return "burmese_kingdom"
        if city_id == "rangoon": return "british_india"
        if city_id == "lahore": return "british_india"
        return base
    if scenario_id == "asia_1890":
        if city_id == "macau": return "portugal"
        if city_id in {"taipei"}: return "qing"
        if city_id in {"hong_kong"}: return "british_empire"
        if city_id in {"saigon", "hanoi", "haiphong", "phnom_penh"}: return "french_empire"
        if city_id in {"rangoon", "mandalay", "lahore"}: return "british_india"
        return {"qing": "qing"}.get(base, base)
    if scenario_id == "asia_1900":
        if city_id in {"beijing", "tianjin"}:
            return "eight_nation"
        if city_id == "qingdao": return "germany"
        if city_id in {"baoding", "shijiazhuang", "nanjing", "wuchang", "hankou"}:
            return "boxers"
        if city_id == "macau": return "portugal"
        if city_id == "hong_kong": return "british_empire"
        if city_id == "taipei": return "japan"
        if city_id in {"port_arthur", "dalian"}: return "russian_empire"
        if city_id in {"rangoon", "mandalay", "lahore"}: return "british_india"
        if city_id == "manila": return "usa"
        # French Indochina was already an established colonial federation by
        # 1900; the 1890s Tonkin/Annam/Cochinchina/Cambodia nodes must not
        # fall back to the 1840 Nguyen dynasty default.
        if city_id in {"hanoi", "haiphong", "saigon", "phnom_penh"}: return "french_empire"
        if base == "qing":
            return "qing"
        return base
    if scenario_id == "asia_1917":
        if city_id in {"guangzhou", "shantou", "nanning", "kunming"}:
            return "guangzhou_government"
        if city_id == "macau": return "portugal"
        if city_id == "hong_kong": return "british_empire"
        if city_id == "taipei" or bloc == "korea": return "japan"
        if city_id in {"rangoon", "mandalay", "lahore"}: return "british_india"
        if city_id == "manila": return "usa"
        if city_id in {"hanoi", "haiphong", "saigon", "phnom_penh"}: return "french_empire"
        if bloc in {"qing_core", "qing_frontier", "manchuria", "treaty_port"}:
            return "beiyang_gov"
        if bloc == "russia":
            return "russian_provisional" if city_id not in {"tashkent", "samarkand"} else "bolsheviks"
        if bloc == "mongolia":
            return "mongolia"
        return {"qing": "beiyang_gov"}.get(base, base)
    if scenario_id == "asia_1927":
        if city_id in {"guangzhou", "nanjing", "shanghai", "wuchang", "hankou", "changsha", "nanchang", "fuzhou", "hanzhou"}:
            return "kmt"
        if city_id in {"beijing", "tianjin", "mukden", "dalian", "port_arthur", "changchun", "harbin"}:
            return "fengtian"
        if city_id == "qingdao": return "fengtian"
        if city_id == "macau": return "portugal"
        if city_id == "hong_kong": return "british_empire"
        if city_id == "taipei" or bloc == "korea": return "japan"
        if city_id in {"rangoon", "mandalay", "lahore"}: return "british_india"
        if city_id == "manila": return "usa"
        if city_id in {"hanoi", "haiphong", "saigon", "phnom_penh"}: return "french_indochina"
        if city_id in {"taiyuan"}:
            return "shanxi"
        if city_id in {"xian", "lanzhou"}:
            return "guominjun"
        if city_id in {"chengdu", "chongqing"}:
            return "sichuan"
        if city_id in {"kunming", "guiyang"}:
            return "yunnan"
        if bloc == "russia":
            return "soviet"
        if bloc == "korea":
            return "japan"
        return {"qing": "kmt"}.get(base, base)
    if scenario_id == "asia_1940":
        if bloc == "philippines":
            return "usa"
        if city_id == "hong_kong":
            return "british_empire"
        if city_id == "macau":
            return "portugal"
        if city_id == "taipei" or bloc == "korea":
            return "japanese_occupied"
        if city_id in {"beijing", "tianjin", "baoding", "shijiazhuang", "jinan", "qingdao", "xuzhou", "shanghai", "nanjing", "hangzhou", "wuchang", "hankou", "guangzhou", "fuzhou", "haiphong", "hanoi", "saigon"}:
            return "japanese_occupied" if city_id not in {"hanoi", "saigon", "haiphong"} else "vichy_france"
        if city_id == "phnom_penh": return "vichy_france"
        if city_id in {"chengdu", "chongqing", "kunming", "xian", "changsha", "nanchang", "lanzhou"}:
            return "kmt"
        if city_id == "lhasa":
            return "tibet"
        if bloc == "russia":
            return "soviet"
        if bloc == "korea" or bloc == "manchuria":
            return "japanese_occupied"
        if bloc == "siam":
            return "thailand"
        if bloc == "british_india":
            return "british_india"
        if bloc == "british_colony":
            return "british_empire"
        if bloc == "dutch":
            return "netherlands"
        if base == "qing":
            # The Qing dynasty no longer exists in 1940.  Interior cities that
            # are not occupied are represented by the National Government's
            # starting control layer; this is a scenario deployment label.
            return "kmt"
        return base
    return base


def compile_map() -> dict:
    from compile_asia_relief_dem import BASELINE, SAMPLES, apply_samples, read
    if not BASELINE.exists() or not SAMPLES.exists():
        raise RuntimeError("Archived continental water-control baseline and physical DEM samples required; never publish guessed relief")
    reference_water={(cell['lon_e6'],cell['lat_e6']):cell['natural_terrain_id']
                     for cell in read(BASELINE)['cells'] if cell['natural_terrain_id']=='river'}
    samples=read(SAMPLES)
    land, river_geos, river_names = load_land_and_rivers()
    land_prepared = prep(land)
    city_lookup = {row[0]: row for row in CITY_ROWS}
    qmax = round((LON_MAX - LON_MIN) / LON_STEP)
    band_max = math.ceil((LAT_MAX - LAT_MIN) / LAT_STEP)
    cells = []
    grid = {}
    for q in range(qmax + 1):
        for band in range(band_max + 1):
            r = band - q // 2
            lon = LON_MIN + q * LON_STEP
            lat = LAT_MAX - band * LAT_STEP
            terrain, terrain_source = terrain_for(lon, lat, land_prepared, river_geos)
            # Retain the published river control-cell abstraction separately
            # from the actual continuous source river lines below. Relief
            # corrections must not silently add a new set of river rule cells.
            if terrain!='sea' and (round(lon*1e6),round(lat*1e6)) in reference_water:
                terrain='river';terrain_source='Natural_Earth_river_centerline_snap'
            cell = {
                "id": f"c_{q}_{r}", "position": pos(q, r), "terrain_id": terrain,
                "region_id": "theater", "lon_e6": round(lon * 1e6), "lat_e6": round(lat * 1e6),
                "elevation_m": None, "relief_sample_m": None, "natural_terrain_id": terrain,
                "terrain_source": terrain_source, "render_land_covered": terrain != "sea",
            }
            cells.append(cell); grid[(q, r)] = cell

    cities = []
    taken = set()
    for cid, name, modern, lon, lat, level, bloc, kind, port in CITY_ROWS:
        if not (LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX):
            continue
        q, r = hex_position(lon, lat)
        candidate = (q, r)
        # A few close treaty-port / river-city pairs share a one-degree column;
        # choose the nearest neighbouring land cell while retaining real coords.
        choices = [candidate] + [(q + dq, r + dr) for radius in range(1, 4) for dq, dr in [(0, -radius), (radius, 0), (0, radius), (-radius, 0), (radius, -radius), (-radius, radius)]]
        choices.sort(key=lambda p: (p in taken, abs(p[0] - q) + abs(p[1] - r)))
        chosen = next((p for p in choices if p in grid and p not in taken and grid[p]["terrain_id"] != "sea"), None)
        if chosen is None:
            continue
        taken.add(chosen); grid[chosen]["terrain_id"] = "city"
        scenario_owners = {f"asia_{year}": scenario_owner(bloc, f"asia_{year}", cid) for year in (1840, 1860, 1890, 1900, 1917, 1927, 1940)}
        city = {
            "id": cid, "name": name, "modern_reference_name": modern,
            "lon_e6": round(lon * 1e6), "lat_e6": round(lat * 1e6), "position": pos(*chosen),
            "render_position": list(world(lon, lat)), "level": level,
            "reference_owner": scenario_owners["asia_1840"], "reference_bloc": bloc,
            "reference_owner_by_scenario": scenario_owners, "key_city": level >= 2,
            "port": port, "kind": kind, "control_radius_hex": 6 if level >= 3 else 4 if level >= 2 else 3,
            "historical_coordinate_status": "gazetteer_coordinate_for_strategic_map; city_footprint_is_not_a_historic_county_boundary",
            "historical_names": [modern] if modern != name else [],
        }
        if cid in {"qingdao"}:
            city["control_notes"] = "1898–1922 German/Japanese lease and occupation history is handled by scenario owner, not a timeless border."
        if cid in {"hong_kong", "macau"}:
            city["control_notes"] = "Treaty-port/lease status is date-dependent; the city marker is not a claim over the surrounding province."
        cities.append(city)
    city_index = {c["id"]: c for c in cities}

    rails = []
    rail_nodes = []
    rail_node_ids = set()
    for rid, name, active, stops in RAIL_CORRIDORS:
        for a_id, b_id in zip(stops, stops[1:]):
            if a_id not in city_index or b_id not in city_index:
                continue
            a = city_index[a_id]["position"]; b = city_index[b_id]["position"]
            path = rail_path((a["q"], a["r"]), (b["q"], b["r"]))
            path = [p for p in path if p in grid]
            if len(path) < 2:
                continue
            edge_id = f"{rid}_{a_id}_{b_id}"
            rails.append({
                "id": edge_id, "name": name, "node_a": a_id, "node_b": b_id,
                "path_hexes": [pos(*p) for p in path], "active_from": active,
                "damage": "intact", "is_bridge": False, "capacity_max": 3, "capacity_left": 3,
                "source_ids": ["asia_rail_corridors", "asia_city_coordinates"],
                "alignment_status": "authored_hex_abstraction_between_real_stations",
            })
            for node_id in (a_id, b_id):
                if node_id not in rail_node_ids:
                    rail_node_ids.add(node_id); rail_nodes.append({"id": node_id, "city_id": node_id, "position": city_index[node_id]["position"], "kind": "station"})
            for q, r in path:
                if grid[(q, r)]["terrain_id"] not in ("city", "sea", "river"):
                    grid[(q, r)]["terrain_id"] = "road"

    world_land = transform(lambda x, y, z=None: world(x, y) if z is None else (*world(x, y), z), land.intersection(box(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)))
    render_land = []
    render_coast = []
    for polygon in walk_geometries(world_land):
        exterior = rounded_ring(polygon.exterior.coords)
        if len(exterior) < 4:
            continue
        render_land.append({"exterior": exterior, "holes": [rounded_ring(ring.coords) for ring in polygon.interiors]})
        render_coast.append(exterior)
    world_rivers = []
    for geo in river_geos:
        transformed = transform(lambda x, y, z=None: world(x, y) if z is None else (*world(x, y), z), geo)
        for line in walk_lines(transformed):
            coords = rounded_line(line.simplify(0.18).coords)
            if len(coords) >= 2:
                world_rivers.append(coords)

    labels = [
        ("乌拉尔山", 60, 52, "land"), ("天山", 82, 43, "land"), ("喜马拉雅山", 86, 30, "land"),
        ("青藏高原", 90, 34, "land"), ("西伯利亚", 105, 60, "land"), ("中亚", 67, 43, "land"),
        ("波斯湾", 51, 27, "water"), ("孟加拉湾", 89, 13, "water"), ("南海", 115, 12, "water"),
        ("日本海", 136, 40, "water"), ("鄂霍次克海", 150, 52, "water"), ("印度洋", 78, -2, "water"),
    ]
    render_labels = [{"name": name, "kind": kind, "position": list(world(lon, lat))} for name, lon, lat, kind in labels]
    extent = [list(world(LON_MIN, LAT_MAX)), list(world(LON_MAX, LAT_MAX)), list(world(LON_MAX, LAT_MIN)), list(world(LON_MIN, LAT_MIN)), list(world(LON_MIN, LAT_MAX))]

    result = {
        "id": MAP_ID, "name": "亚洲全境战略地图 · 铁道烽烟",
        "projection": "equirectangular_lonlat_hex_axial", "geographic_bounds": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX],
        "hex_radius_m": 150000, "hex_radius_px": 48, "longitude_step_deg": LON_STEP, "latitude_step_deg": LAT_STEP,
        "cells": cells, "cities": cities, "rail_nodes": rail_nodes, "rail_edges": rails, "crossings": [],
        "render_extent": extent, "render_coast": render_coast, "render_rivers": world_rivers,
        "render_land": render_land, "admin_layers": {}, "render_labels": render_labels,
        "strategic_scale": True,
        "geography_status": "real_natural_earth_land_water_geometry_with_real_gazetteer_points_and_declared_hex_abstraction",
        "sources": SOURCES, "river_source_names": sorted({n for n in river_names if n}),
        "administration_notes": [
            "Natural Earth polygons describe physical land and water only. They are not 1840/1860/1890/1900/1917/1927/1940 political borders.",
            "Historical control is scenario data attached to real city coordinates; control radii are a game influence visual and are not county boundaries.",
            "A province-scoped mission can cite the period administration in the timeline record without painting an unsupported historic province polygon over the physical map.",
        ],
        "terrain_classification": {
            "method": "Natural Earth land/water plus named relief corridor bands and Natural Earth major river centerline snaps",
            "historical_vegetation_claimed": False, "historical_political_borders_claimed": False,
            "strategic_abstraction": True, "base_hex_grid_unchanged": True,
        },
        "notices": [
            "This is the continental strategic layer; city influence polygons are presentation zones and never overwrite historical administrative research.",
            "Exact historical garrison locations and formation strengths are stored in content/history and source-status fields, not inferred from the physical map.",
        ],
    }
    return apply_samples(result,samples)[0]


def main():
    result = compile_map()
    output = PROJECT / "content/maps/asia_strategic.json"
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    catalog_path = PROJECT / "content/maps/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if MAP_ID not in catalog["maps"]:
        catalog["maps"].append(MAP_ID)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"map": MAP_ID, "cells": len(result["cells"]), "cities": len(result["cities"]), "rails": len(result["rail_edges"]), "land_shapes": len(result["render_land"]), "rivers": len(result["render_rivers"]), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
