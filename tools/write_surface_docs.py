"""Document actual physical-source, material and river implementation states."""
from pathlib import Path
from datetime import datetime, timezone
from build_release import P, ROOT, current_version
from map_bank_inventory import read


def optional(path):return read(path) if path.exists() else {}


def main():
    import fitz
    license_document=fitz.open(ROOT/'design/geodata/surface_detail_sources/HydroSHEDS_TechDoc_v1_4.pdf')
    license_text='\n'.join(license_document[index].get_text() for index in range(23,len(license_document)))
    if 'LICENSE GRANTS' not in license_text or 'REQUIRED ATTRIBUTIONS' not in license_text:
        raise RuntimeError('Complete original HydroSHEDS license appendix required')
    license_path=P/'assets/legal/HYDROSHEDS-V1-LICENSE.txt'
    if not license_path.exists() or license_path.read_text(encoding='utf-8')!=license_text:
        license_path.write_text(license_text,encoding='utf-8')
    license_document.close()
    ground=read(P/'reports/surface_geography_compilation.json')
    dem=read(P/'reports/asia_relief_dem_revision.json')
    hydro=optional(P/'reports/hydrography_fine_compilation.json')
    production=optional(P/'reports/map_surface_extension_generation.json')
    installation=optional(P/'reports/map_bank_installation.json')
    text=f'''# 地表材质与细水系 · {current_version()}

本轮针对基础地块缺少纹理、选材不符合地理、细支流不足的问题实施。地表图像沿用指定 Sub2 路线独立生成，地理分类使用可追溯的矢量与数值高程数据。**区域底材不等于逐年的历史土地利用测绘**；河线的精度与年代限制见下文。

## 实施状态

| 内容 | 当前状态 |
| --- | --- |
| 基础地表选材 | 已改为来源区域决定材质；同材质内部使用独立原图变体 |
| 地表原图 | 基础库包含草地 36、干草 24、岩土 16、林下土 16、湿土 16、水面 12；追加沙土 24、砾土 16、冲积土 16，目前追加原图 {production.get('completed',0)}/56 |
| 完整库安装 | {'已安装 796 张新增原图' if installation.get('passed') and installation.get('installed')==796 else '等待全部原图生成及统一安装；不将计划数作为已安装数'} |
| 亚洲地形分类 | 已用 {dem['source_tiles']} 张原始 GeoTIFF、{dem['source_points']:,} 个样本修正 {dem['changed_terrain_cells']} 格；城市、政治、铁路和水体几何逐项保持 |
| 较细河网 | {'已编译，具体覆盖见下表' if hydro.get('passed') else '正在下载并编译原始水系；尚不记作已完成'} |
| 实机与历史审核 | 以当前报告和导出为准；Motorola X30 物理设备、完整历史河道与土地利用审核未闭环 |

## 地表选材规则

| 实际地理参考 | 底材 | 约束 |
| --- | --- | --- |
| 塔克拉玛干、阿拉伯沙漠、雷吉斯坦—北巴基斯坦沙漠生态区 | 浅赭细沙、微弱风纹 | 不把全部戈壁画成黄沙，不生成地形起伏或沙丘群 |
| 戈壁荒漠草原、阿拉善、柴达木及其他已登记干旱荒漠区 | 灰褐矿质土、细砾与稀疏地表颗粒 | 属区域代表性材质，不是精确的砂砾粒径调查 |
| 蒙古等温带草原、山地草甸区域 | 枯草、草土纤维 | 图形变化不能改变草原边界或地格移动规则 |
| 黄河平原、长江平原、东北平原、恒河平原与塔里木河谷来源区的低起伏地格 | 粉砂／土壤与稀疏草质纹理 | 同时检查来源高程与起伏；高海拔河谷不因高于 250 米而被一概排除 |
| 渤海、黄海盐生草甸及已登记洪泛生态区 | 灰绿湿土与微小草茬 | 只表示区域底材参考，不画成新的湖泊、积水或 1924 年沼泽边界 |
| 已有来源山地、林地、水面 | 岩质、林下、细水纹底材 | 树林仍受独立历史林地证据约束；不将现代潜在森林生态区直接种满树 |

底材使用 RESOLVE Ecoregions 2017 的地理区域作为美术选材参考，逐格保存 `ECO_ID`、区域名称、源文件 SHA 和材质族。该数据描述潜在生物地理区，不能据此宣称某个具体年份仍有原生森林、湿地或某种农业经营方式。没有进一步证据的地区采用中性草土底材，不虚构农田边界、作物或灌渠。

| 地图 | 来源区域底材格数 | 分材质数量 |
| --- | ---: | --- |
'''
    for map_id,counts in ground['assignments_by_map'].items():
        text+=f'| {map_id} | {sum(counts.values())} | '+', '.join(f'{key}: {value}' for key,value in counts.items())+' |\n'
    text+='''
这些是控制格中心落入来源区后获得的区域材质参考数量，不是精确生态区面积。亚洲控制格约 150 公里尺度，不能提供村级地表精度；战役地图使用其各自真实投影与更细的采样网格。

地表覆盖内区提高至可辨识的材质强度，并在外缘柔和衰减；政治控制色仍是独立半透明覆盖。靠近精确海岸或湖边、完整纹理显示范围会越过边界的格子，交给连续陆地／水面底层显示，避免六边形纹理改写海岸。原图保持字节与长宽，不生成拼接底图或换色副本。

岸边装饰也有地形约束。原图逐张目视检查发现部分河岸、海岸图含岩石隆起，因此平原河岸只用六张低矮草丛；岩质岸线图仅在原有丘陵、山地或高峰格允许。不能因为一条来源河线经过，就把平坦冲积地画成石质河谷。图符本身不作为精细地质测绘。

## 亚洲地形修正

旧大陆图通过经纬度矩形标记山地区域，导致塔克拉玛干盆地也被误判为山地。本轮将其替换为 Mapzen／Tilezen 原始数值高程数据：缩放级别 4，按每格中心及九点 100 公里支持范围的真实样本计算高程和起伏。平原／丘陵／山地／高峰依据起伏阈值分级；高海拔平坦盆地不会单凭海拔自动变成山地。

阈值是大陆级玩法分类：起伏小于 400 米为低起伏地；400 米起为丘陵；1,200 米起为山地；2,800 米起且中心高于 2,000 米为高峰。它们不是地质学通用分级，也不适用于 1 公里战役格。海岸、主河流、真实城市、铁路拓扑、行政与政治数据没有随此修正重画。

这一修正有意改变亚洲规则地形及当前内容指纹，旧指纹存档可能需要新开对局；战术战役原有 DEM 分类和基础操作格半径保持。原大陆地图已单独保存，源 GeoTIFF 未改写。大陆明暗使用物理高程与经纬度换算的米制梯度，继续省略跨 150 公里格插值的战术等高线，避免暗示不存在的细部测绘。

## 河流与溪流

主要水系及此前的次要命名河流使用已归档 Natural Earth 线数据；不从相邻“河流格”拼出水道。本轮补充 HydroRIVERS v1 的实际源河段，记录源河段 ID、级序、几何和缩放门槛，不将不相连的端点强行接起来，也不把开放河线闭合为多边形。

HydroRIVERS 基于约 15 角秒的高程水文资料，通常从上游汇水面积约 10 平方公里或长期估计流量约 0.1 立方米／秒的阈值提取河道，因此**不包含每一条溪沟**。它是现代物理水系推算，不能作为 1840—1940 各年的逐条河道、实测宽度、桥梁、通航能力或军事渡河点证明；未核实的现代水利与平原人工河渠不能回填为历史设施。显示的线宽是图符层级，不能解读成实测河宽。

细水系保留分级可见性，主河、支流与更小河段分别呈现水色、暗岸及窄亮线。溪流名称不足时不编造地名；美术层不自动产生桥梁、渡口、水运或新的战斗通行规则。具体覆盖、排除范围和原始文件以 `hydrography_fine_compilation.json` 为准。

1 公里战役格保留来源 1—4 级支流，并按缩放逐级显现；5.4 公里征服格仅保留来源 3—4 级、上游汇水面积至少 400 平方公里的可读河段。大陆概览保持原有 Natural Earth 河网。不同显示层级不是新增的实测水文精度。

原始推算河网的栅格折角通过原生二次曲线作局部圆角：切线距离按真实地图比例换算，显示偏差上限 60 米。原始折线、首尾端点、分叉、源河段 ID 和规则水系保持；不插入随机曲流或连接断开的河段。显示线仍是图符，不是实测河岸。
'''
    if hydro.get('passed'):
        text+='\n| 地图 | 新增源河段 | 几何线段 |\n| --- | ---: | ---: |\n'
        for map_id,row in hydro['maps'].items():
            text+=f'| {map_id} | {row["reaches"]} | {row["segments"]} |\n'
        text+='\n本轮额外河段范围：'+hydro.get('eligible_scope','见编译报告')+'。\n'
    text+='''
## 来源与核验

- [RESOLVE Ecoregions 2017 数据与 CC BY 4.0](https://ecoregions.world/)；Dinerstein 等（2017），[BioScience 论文](https://doi.org/10.1093/biosci/bix014)。改编用途为游戏区域底材参考，不代表来源方认可本游戏。
- [HydroRIVERS 官方说明及原始数据](https://www.hydrosheds.org/products/hydrorivers)；Lehner 与 Grill（2013），[Hydrological Processes 论文](https://doi.org/10.1002/hyp.9740)。HydroSHEDS 许可与技术说明随源数据保存。
- [Terrain Tiles 官方开放数据登记](https://registry.opendata.aws/terrain-tiles/)及[数据归属说明](https://github.com/tilezen/joerd/blob/master/docs/attribution.md)。高程数据用于物理地貌，不作历史地表调查。

地理原始数据、许可与哈希位于 `design/geodata/surface_detail_sources/`、`design/geodata/asia_relief_dem/` 和 `design/geodata/terrain_tiles/`；运行时参考位于 `presentation/data/surface_regions.json` 与细河网目录。地理编译、原始矢量逐项核查、原生规则隔离、材质库数量与最终 EXE 画面分开验收。生成中、已安装和正式批准分别记录，不将自动测试通过视作 EW6 商业美术达标。
'''
    (P/'docs/29_地表材质与细水系.md').write_text(text,encoding='utf-8')
    legal=P/'assets/legal/GEOGRAPHIC-DATA-NOTICES.txt'
    legal.write_text('''Geographic presentation data notices

RESOLVE Ecoregions 2017 — Dinerstein et al. (2017).
Source: https://ecoregions.world/
Publication: https://doi.org/10.1093/biosci/bix014
License: Creative Commons Attribution 4.0 International.
License text: https://creativecommons.org/licenses/by/4.0/legalcode
Changes: selected source region membership is converted into representative
ground-material references for game control cells. This is not dated land-use,
soil, actual forest or historical wetland mapping. No endorsement is implied.

HydroRIVERS v1 — Lehner, B.; Grill, G. (2013).
Global river hydrography and network routing: baseline data and new approaches
to study the world's large river systems. Hydrological Processes 27:2171-2186.
https://doi.org/10.1002/hyp.9740
Data and license: https://www.hydrosheds.org/products/hydrorivers
Underlying HydroSHEDS license applies; see HYDROSHEDS-V1-LICENSE.txt.
The original technical documents are retained in the Godot source package.
The geographic data remain subject to that license. Use of this included data
is governed by its terms; no separate right to redistribute it as a standalone
product, sublicense it, decompile, reverse engineer or disassemble it is granted
except as expressly authorized by the source license or applicable law.
Changes: selected clipped and simplified source river reaches are displayed as
physical geographic reference lines, not historically surveyed channel widths,
complete creeks, artificial canals or historical military crossing points.

Required HydroSHEDS attribution:
This product Railway Warlords incorporates data from the HydroSHEDS version 1
database which is © World Wildlife Fund, Inc. (2006-2022) and has been used herein
under license. WWF has not evaluated the data as altered and incorporated within
Railway Warlords, and therefore gives no warranty regarding its accuracy,
completeness, currency or suitability for any particular purpose. Portions of the
HydroSHEDS v1 database incorporate data which are the intellectual property rights
of © USGS (2006-2008), NASA (2000-2005), ESRI (1992-1998), CIAT (2004-2006),
UNEP-WCMC (1993), WWF (2004), Commonwealth of Australia (2007), and Her Royal
Majesty and the British Crown and are used under license. The HydroSHEDS v1
database and more information are available at https://www.hydrosheds.org.
Lehner, B., Verdin, K., Jarvis, A. (2008): New global hydrography derived from
spaceborne elevation data. Eos, Transactions, AGU, 89(10): 93-94.

Elevation: Mapzen / Tilezen Terrain Tiles.
https://registry.opendata.aws/terrain-tiles/
https://github.com/tilezen/joerd/blob/master/docs/attribution.md
Underlying global sources include USGS SRTM, GMTED2010 and NOAA ETOPO1.
Changes: nine registered elevation samples over a 100 km square per continental
control cell; bilinear interpolation; derived coarse physical relief categories.
Original scientific GeoTIFF bytes are preserved. They are not game-art textures.

Natural Earth land and river geometry: public domain.
https://www.naturalearthdata.com/about/terms-of-use/
''',encoding='utf-8')
    print('Surface-material documentation and geographic notices updated from current ledgers',flush=True)


if __name__=='__main__':main()
