"""Publish current map-material status only after verified installation and native evidence.

The original design inventory and archived releases remain unchanged. Current
runtime ledger fields are explicit additions, not a rewrite of the v1 plan.
"""
from collections import Counter
import json
from build_release import P, ROOT, current_version, source_digest
from map_bank_inventory import ADDITIONAL_COUNT, MAP_COUNT, production_rows
from run_validation import CHECKS


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def replace_paragraph(path, prefix, replacement):
    source = path.read_text(encoding='utf-8')
    if path.name == 'README.md' and '<!-- repository-readme: maintained in Chinese and English -->' in source:
        return  # Preserve the detailed bilingual repository entry points.
    paragraphs = source.split('\n\n')
    if prefix == '当前继续以':
        prefix = ('当前继续以', '当前以')
    matches = [i for i, paragraph in enumerate(paragraphs) if paragraph.lstrip().startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one current-status paragraph: {path.name}: {prefix}')
    paragraphs[matches[0]] = replacement
    path.write_text('\n\n'.join(paragraphs), encoding='utf-8')


def main():
    version = current_version()
    runtime = source_digest()[0]
    originals, complete = production_rows(require_complete=True)
    assets = read(P/'assets/manifest.json')['assets']
    counts = Counter(row['category'] for row in assets)
    installation = read(P/'reports/map_bank_installation.json')
    evidence = read(P/'reports/map_bank_native_evidence.json')
    summary = read(P/'reports/visual_update_verification_summary.json')
    exports = read(P/'reports/export_results.json')
    if not (complete and len(originals) == ADDITIONAL_COUNT and
            installation['passed'] and installation['total_map_assets'] == MAP_COUNT and
            evidence['passed'] and evidence['runtime_source_sha256'] == runtime and
            evidence['version'] == version and summary['version'] == version and
            summary['all_groups_passed'] and summary['current_native_capacity_profiles_passed'] and
            len(summary['groups']) == len(CHECKS) and
            {row['target'] for row in exports} == {'windows', 'android'} and
            all(row['export_verified'] and row['runtime_source_sha256'] == runtime for row in exports)):
        raise SystemExit('Current installation, tests, native views, capacity and both exports are required.')
    native_links = '\n'.join(f'- [{row["label"]}](../{row["file"]})' for row in evidence['captures'])
    text = f'''# 当前完成度评估 · {version}

当前为 Godot 4.7.2 可玩测试版，schema 2 / ruleset 9。本轮重点是逐格地表贴图、真实区域选材、细支流与原图重复问题。已安装新增 **{ADDITIONAL_COUNT} 张独立地图原图**，地图素材从 74 张扩为 **{MAP_COUNT} 张，约 11.76 倍**；当前全部运行栅格为 **{len(assets)} 张**。数量不代表已达到 EW6 的商业美术水准。

| 范围 | 当前落实 | 仍需完成 |
| --- | --- | --- |
| 基础地表 | 新增 176 张草土、旱草、岩土、林下土、湿土、水面、细沙、砾土与冲积土材质；原生柔边网格；源生态区和高程门控 | 完整季节、土壤/土地利用调查与跨地区边缘套件；潜在生态区不等于逐年历史覆盖 |
| 地景与立体感 | 新增 144 张林地、240 张丘陵/山脊/高峰、96 张岸线/露岩/芦苇原图；按高程坡向、完整脚点与空间排重放置 | 全域历史森林覆盖、地点专属地貌、全部远近尺度的人工精修 |
| 真实地形 | 亚洲战略层从 54 张原始 GeoTIFF、33,696 个注册采样点修正旧矩形地形；归档来源可重建验证 | 大陆规则格名义半径 150 千米，DEM 采样支持范围 100 千米，不能当作村级地形；战术地图另有来源精度 |
| 水系 | 保留原始主河与 694 条亚洲来源支流；新增 24,268 条细河段和 31 条主河显示替代段，按等级/尺度分层；显示圆角保持源端点 | 全量小溪、完整河网拓扑、1840—1940 逐年改道/人工渠调查；细河层不增加规则障碍 |
| 城镇与交通 | 新增 140 张地区化建筑，华北村落池 26 个、华南 10 个；地点文化绑定、占领不换建筑文化；原聚落与铁路来源保留 | 具名城市实测街区、更多专属关隘、桥梁与港区套件；通用符号不等于地点复原 |
| 单位与 HUD | 原有 64 张四向单位图、16 张普通步兵动作图、长期朝向与钢灰 HUD 保留；地格详情显示实际材质与来源地形 | 其他兵种完整动作周期、八向、装填/阵亡与全设备人工体验 |
| 核心玩法 | 战役、自由世界、征服、军团、经济、补给、外交、将领与命令驱动战斗继续运行 | 全关卡人工策略平衡、逐条军事起局审核；尚无欧陆风云级系统深度结论 |
| 双端 | 当前 Windows EXE、签名 Android APK、完整 Godot 工程；22 组回归及桌面双布局最大负载复测 | Motorola X30 实机安装、触控、GPU、温度、续航；本轮完整 AI 长局未重跑 |

原图、提示词、字节与导入核验、空间排重和实际 EXE 视口分别记录。地理独立审计从原始生态区多边形、GeoTIFF 像元和实际源河段核验，不用编译结果互相印证。新增现代潜在生态区只指导代表性地表材质，不回填历史森林、沼泽、行政边界或军事控制线。

本轮亚洲规则地形分类有意变化，内容指纹也随之改变；旧进行中战局应使用对应旧版本继续，新版重新开局。城市、政治归属、铁路、原始水体几何和 48 像素基础蜂窝保持，真实地理订正不会被包装为纯显示变化。

当前通过范围见 [测试与验收](05_测试与验收.md)，素材来源与排重见 [28](28_地图素材扩充与去重.md)，地区贴图和细水系精度见 [29](29_地表材质与细水系.md)。0.2.9 及更早长局报告保留在原交付，不冒充本版新测结果。全部素材正式美术/史实批准与完整商业发行仍未闭环。

## 当前导出 EXE 的原生地图

{native_links}
'''
    (P/'docs/23_当前完成度评估.md').write_text(text, encoding='utf-8')
    comparison = f'''# 欧陆战争6地图资源差距评估 · {version}

对照依据延续归档的 EasyTech 官方手册与商店画面记录 `output/research/european_war_6/sources.json`。只比较可观察的画面，不推测其内部图块数量或实现。UI 见 [26](26_欧陆战争6_UI结构与视觉对标.md)。

本轮针对“地格没贴图、素材重复、河流单薄”的问题，增加独立地表/地景/建筑并接入实际地图。**地图素材 74 → 870 张**，每张来自指定 Sub2 路线，换色、镜像、导入缓存和副本均不计数。画面改善必须以当前导出 EXE 的完整视口判断，数量与自动检查不构成质量等价结论。

| 比较项 | 当前实现 | 与成熟商业地图的差距 |
| --- | --- | --- |
| 基础地格 | 新增 176 张完整地表原图，覆盖草土、旱草、砂、砾、冲积土、湿土、林下土、岩土与水面；柔边显示并保留势力半透明覆盖 | 完整海拔/季节/土地利用族、连续拼接边缘和全区域人工调色仍不足 |
| 地理选材 | 真实生态区多边形、高程与现有地形共同门控；塔克拉玛干沙地、戈壁砾地、华北平原土、天津附近湿土分开 | 现代潜在生态区并非逐年历史地表调查，不能据此补造森林或湿地 |
| 树林 | 新增 144 张独立疏密针阔叶林、林缘图，空间排重和脚点排序 | 战略层森林仍限于 8–9 处年代门控来源节点；全亚洲历史覆盖资料缺口保留 |
| 山体 | 新增 240 张丘陵、山脊和高峰，横向/纵深轮廓按高程坡向选择；亚洲旧矩形山地改为真实 DEM | 山口、峡谷与专属连绵山系、更多 LOD 手工精修仍有差距 |
| 河流 | 原始主河、694 条战略来源支流与 24,268 条战术细河段分层；另有 31 条长江主河显示替代段；原始几何保留，显示圆角偏差受限 | 原始数据约 500 米支持尺度，不能声称全量溪流、实测河宽、历史改道或完整规则化河网 |
| 岸线与露岩 | 新增 96 张独立原图，候选来自实际岸线/河线；完整纹理避让水体、海岸与铁路 | 地点专属河滩、河口、港池与渡口套件不足；装饰不作为历史岸宽调查 |
| 城镇 | 新增 140 张地区化建筑；华北村落 26 个轮廓、华南 10 个；源地点控制出现与文化类型 | 通用图符仍非具名城市复原，专属城墙/地标/桥梁密度不足 |
| 势力色层 | 保留战略 0.21、战术 0.26 透明覆盖，地表与地物可透出 | 当前据点控制表现仍是游戏状态，不冒充历史实际战线 |
| 单位与动作 | 64 张独立四向图、16 张普通步兵动作图、事件驱动移动/攻击/受击与方向存档 | 其余兵种的完整动作、连续八向、装填/阵亡和帧间一致性仍需补足 |
| 多尺度与性能 | 按需纹理、空间索引、缩放分层，当前 Windows 导出在两个布局完成最大负载及各 60 秒复测 | 桌面 X30 尺寸不等于手机；跨设备美术和 GPU/触控实测未完成 |

实际图见 [当前原生地图](23_当前完成度评估.md#当前导出-exe-的原生地图)。生产/安装/来源字节/近似图筛查/原生视口的证据独立保存，见 [28](28_地图素材扩充与去重.md)；地理数据、代表性材质和历史精度见 [29](29_地表材质与细水系.md)。后续继续完善有来源的地貌、边缘与季节族、历史植被以及全兵种动作，不以无依据随机装饰填补资料缺口。
'''
    (P/'docs/25_欧陆战争6地图资源差距评估.md').write_text(comparison, encoding='utf-8')
    art = f'''# 美术来源与审核 · {version}

全部栅格经用户指定的 `C:/Users/carzy/.codex/skills/sub2-image-gen/SKILL.md` 所属 CLI、Sub2 网关及 `gpt-image-2.5/high` 生成。原始概念图、每次独立原图和提示词不可变；本轮没有裁图、叠字、拼接、补绘、镜像或用换色副本增加数量。

当前运行栅格 **{len(assets)} 张**：{counts['unit']} 单位方向/动作、{counts['portrait']} 肖像、{counts['building']} 建筑、{counts['tile']} 地表、{counts['scenery']} 地景、{counts['ui']} UI 材质、{counts['icon']} 图标、{counts['fx']} 特效和 {counts['background']} 背景。地图三类合计 {MAP_COUNT} 张，本轮新增独立原图 {ADDITIONAL_COUNT} 张。另有 17 段原生程序音频和两个 OFL 中文字体。实际尺寸与源 SHA 见 `assets/manifest.json` 和 `reports/resource_validation.json`。

欧陆战争6方向的当前源图为 {sum('/ew6_v025/' in row['source_file'] for row in assets)} 张，包含四向单位、普通步兵动作、地表、地景、建筑和系统材质；生成路线不等于已获正式美术批准。64 张四向单位与 16 张步兵动作的历史修订继续保留。此前带虚构姓名或全场景海面初稿的拒收记录不删除，也不作为运行素材。

原有生产历史位于 `output/imagegen/warlord/raw`、`atlas_v2`、`settlements_v023`、`ew6_v025`；本轮原图位于 `ew6_v025/map_bank_v0212`。各计划、生产、安装、原图字节/透明边界和整幅近似图筛查分别记录。生成器调用指定 CLI 保存结果；引擎副本逐字节复制；Godot 的导入压缩、mipmap、原生网格、完整素材脚点及显示尺寸不修改源 PNG。

源图目视检查关注轮廓变化、统一左上光、透明边缘、底材粒度、建筑比例和错误的地貌暗示。已对平原河岸、岩岸与沼泽图分别约束候选池；带明显石丘的湿地输出不放到沼泽格。原图不因筛选而重绘或删除。源图检查和游戏视口检查分开，自动 SHA/近似图检查不代替商业美术与装备史批准。

全部源图继续保留待正式审核状态。当前 EXE 的地图、HUD、四向行军、战斗和完整视口记录见 `native_visual_evidence.json`、`map_bank_native_evidence.json`、`hud_native_tests.json`；素材字节与生成账本见 `atlas_v2_asset_audit.json` 和 `map_bank_asset_audit.json`。完整概念图一次直接生成，仅作风格参考，不作历史地理与肖像审核结论。

地图采用归档海岸、主/支流、高程、生态区选材、年代行政层、城市坐标与铁路资料；生态区不是逐年土地利用调查。独立符号受源地形与完整显示范围约束，不据生成图新增地名、山谷、桥梁、湖泊或军队。来源与精度见 [地表与细水系](29_地表材质与细水系.md)。

新地表/地景导入最长边 256 像素、建筑 384，启用 mipmap；旧单位等资源各有独立上限，当前实值见 `reports/import_budgets.json`。原图完整保存，导入尺寸不计作新素材。字体许可位于 `assets/font/OFL*.txt`，地理资料的署名、完整 HydroSHEDS 许可与引擎许可位于 `assets/legal`，随双端包交付。

正式美术/历史审核、全部关卡人工平衡和 Motorola X30 物理验收仍单列，见 [当前完成度](23_当前完成度评估.md)。
'''
    (P/'docs/04_美术来源与审核.md').write_text(art, encoding='utf-8')
    ui = P/'docs/26_欧陆战争6_UI结构与视觉对标.md'
    ui_text = ui.read_text(encoding='utf-8')
    ui_text = ui_text.replace(ui_text.splitlines()[0], '# 欧陆战争6 UI结构与视觉对标 · '+version, 1)
    ui_note = '当前修订说明：地格检查器使用实际选中的地表原图和简短材质名称；HUD 三视口证据见 [测试与验收](05_测试与验收.md)。下文保留 0.2.9 的 UI 架构重构说明及其旧证据出处，当前导出状态以新报告为准。'
    if ui_note not in ui_text:
        ui_text = ui_text.replace('\n\n', '\n\n'+ui_note+'\n\n', 1)
    ui.write_text(ui_text, encoding='utf-8')
    actions = P/'docs/27_动作关键帧与地格详情.md'
    action_text = actions.read_text(encoding='utf-8')
    action_note = '本章保留 0.2.11 的动作与 HUD 修订记录；其中素材总数、截图及验收范围属于该版。当前地图素材、地表与细水系以及本版测试状态分别见 [28](28_地图素材扩充与去重.md)、[29](29_地表材质与细水系.md)和[测试与验收](05_测试与验收.md)。'
    if action_note not in action_text:
        action_text = action_text.replace('\n\n', '\n\n'+action_note+'\n\n', 1)
    actions.write_text(action_text, encoding='utf-8')
    index = P/'docs/00_程序文档索引.md'
    replace_paragraph(index, '实施版本：', f'实施版本：{version} 地表材质、独立素材扩充与细水系测试版，Godot 4.7.2，运行态 schema 2，ruleset 9。当前交付范围见 [23](23_当前完成度评估.md)，地图素材与去重见 [28](28_地图素材扩充与去重.md)，实际区域贴图、真实高程和细河网见 [29](29_地表材质与细水系.md)。设计基线及五方向备选快照保留。')
    s = index.read_text(encoding='utf-8').replace('796 张新增原图计划、实际生产/安装状态', '796 张新增独立原图、870 张地图素材、生产/安装证据').replace('0.2.11 当前实现', version+' 当前实现')
    index.write_text(s, encoding='utf-8')
    game_readme = P/'README.md'
    replace_paragraph(game_readme, ('0.2.11 增加', version+' 扩充'), f'{version} 扩充地图素材并补足逐格地表：草土、沙地、砾地、湿土与冲积土按真实区域选材；山体、林地、聚落以独立原图和空间排重增加变化；细支流按真实来源与地图尺度显示。见 [当前完成度](docs/23_当前完成度评估.md)、[地图素材](docs/28_地图素材扩充与去重.md)和[地表与细水系](docs/29_地表材质与细水系.md)。')
    replace_paragraph(game_readme, '当前继续以', f'当前以《欧陆战争6》为主要美术和动效对照；{len(assets)} 张当前栅格保留 Sub2 原图/提示词，其中地图 {MAP_COUNT} 张、四向单位图 64 张。本轮 22 组回归、实际 EXE 地图画面和桌面双布局最大负载复测已完成；完整 AI 长局、正式美术批准及物理 Motorola X30 验收单列。')
    replace_paragraph(game_readme, '当前版本 **', f'当前版本 **{version}，地图材质与素材扩充测试版**。使用 Godot 4.7.2 / GDScript，Windows 和 Android 共用规则层，离线单机运行。原设计与旧版本交付保持。')
    replace_paragraph(game_readme, ('256 张 PNG', f'{len(assets)} 张 PNG'), f'{len(assets)} 张 PNG 均通过指定 `sub2-image-gen / gpt-image-2.5` 独立生成；引擎副本保持原始字节，源文件未裁图、重绘、拼接或手工缩放。原图和提示词保留在 `output/imagegen/warlord/`，本轮新增位于 `ew6_v025/map_bank_v0212/`；运行时由 Godot 导入与显示。另有 14 个程序音效、3 段程序音乐和 2 个 OFL 中文字体。')
    replace_paragraph(game_readme, '地图采用', '地图采用 Natural Earth 海岸和主河、HydroRIVERS 细河段、Tilezen/SRTM 数值高程、来源生态区地表选材、年代区划、真实城市坐标与铁路节点；现有京津、京奉、中国东部征服、汉口江段、南京—浦口五张区域图及亚洲战略层。城市和路线量化到六边格；战区编队、数值和战术目标属于游戏编排，不宣称档案级复原。')
    replace_paragraph(game_readme, '完整程序索引见', f'完整程序索引见 [docs/00_程序文档索引.md](docs/00_程序文档索引.md)。测试报告、真实 Godot 截图与导出校验在 `reports`；本轮交付在工作区 `output/releases/railway-warlords-{version}`。有限范围交付使用 `tools/package_visual_update.py`，完整发行门槛仍由原 `package_delivery.py` 保留。')
    root_readme = ROOT/'README.md'
    replace_paragraph(root_readme, '当前更新：', f'当前更新：**{version} 地表材质、独立素材与细水系测试版**。[双端交付](output/releases/railway-warlords-{version}/) / [地图素材与原生画面](game/railway_warlords/docs/28_地图素材扩充与去重.md) / [地表贴图与细河网](game/railway_warlords/docs/29_地表材质与细水系.md) / [完成度](game/railway_warlords/docs/23_当前完成度评估.md)。地图素材 74 → 870 张，按真实区域区分草土、沙地、砾土、湿土与冲积土，增加有来源细河段与真实 DEM 地形。')
    root_text = root_readme.read_text(encoding='utf-8').replace('railway-warlords-0.2.11/', f'railway-warlords-{version}/').replace('当前256项运行栅格', f'当前{len(assets)}项运行栅格')
    root_readme.write_text(root_text, encoding='utf-8')
    design_index = ROOT/'design/铁道烽烟/00_总纲与文档索引.md'
    replace_paragraph(design_index, '当前程序修订入口：', f'当前程序修订入口：[{version} 地图素材扩充与去重](../../game/railway_warlords/docs/28_地图素材扩充与去重.md) / [地表贴图与细水系](../../game/railway_warlords/docs/29_地表材质与细水系.md) / [实际完成度](../../game/railway_warlords/docs/23_当前完成度评估.md)。下述设计基线和早期交付记录保留；当前执行内容、素材登记和验收范围以程序报告为准。')
    design_index.write_text(design_index.read_text(encoding='utf-8').replace('166 张已登记栅格素材', f'{len(assets)} 张已登记运行栅格素材'), encoding='utf-8')
    design_catalog = ROOT/'design/铁道烽烟/assets/asset_catalog.json'
    catalog = read(design_catalog)
    catalog.update(current_runtime_raster_count=len(assets),
                   ew6_current_replaced_or_added_rasters=sum('/ew6_v025/' in row['source_file'] for row in assets),
                   current_map_raster_count=MAP_COUNT, current_map_added_independent_sources=ADDITIONAL_COUNT,
                   current_runtime_version=version, complete_formal_art_approval=False,
                   current_runtime_categories=dict(counts))
    design_catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(version=version, map_assets=MAP_COUNT, rasters=len(assets), docs_updated=True), ensure_ascii=False))


if __name__ == '__main__':
    main()
