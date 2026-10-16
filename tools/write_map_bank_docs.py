"""Write production and installation states from their actual independent ledgers."""
from collections import Counter
import json
from build_release import P, ROOT, current_version
from map_bank_inventory import planned_rows, production_rows, ADDITIONAL_COUNT, MAP_COUNT


def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else (default or {})


def main():
    baseline = read(P/'reports/map_bank_baseline.json')
    production = read(P/'reports/map_bank_generation.json')
    extension = read(P/'reports/map_settlement_extension_generation.json')
    surface_extension = read(P/'reports/map_surface_extension_generation.json')
    manifest = read(P/'assets/manifest.json')['assets']
    current = [row for row in manifest if row['category'] in ['tile','scenery','building']]
    originals, all_produced = production_rows()
    planned = planned_rows()
    generated_counts = Counter(row['category'] for row in originals)
    installed_counts = Counter(row['category'] for row in current)
    old_counts = Counter(row['category'] for row in baseline['assets'])
    target_counts = old_counts + Counter(row['category'] for row in planned)
    installed_new = [row for row in current if '_bank_' in row['id']]
    complete = len(installed_new)==ADDITIONAL_COUNT and all_produced
    status = '已安装，当前地图素材 870 张' if complete else f'制作中：新增原图 {len(originals)}/796，已安装新增 {len(installed_new)}/796'
    text = f'''# 地图素材扩充与去重 · {current_version()}

状态：**{status}**。本轮用可追溯的独立原图扩充地图资源，并改善同一区域的选材重复；完整商业美术、全部历史内容和物理手机验收仍分别记录。

## 数量与范围

扩充前的基线为 **74 张地图素材**，包括地表贴图、地景和建筑，不含单位、人物、UI、特效。基础生产计划增加 666 张，随后追加 74 张中国村镇/交通建筑及 56 张沙土、砾土、冲积土材质，计划最终 **870 张，为基线的约 11.76 倍**。每张新增图均通过指定 Sub2 路线独立生成，副本、换色、镜像和导入缓存不计作新增。

| 类别 | 本轮基线 | 已生成新增原图 | 当前已安装总数 | 完成计划总数 |
| --- | ---: | ---: | ---: | ---: |
'''
    for category, label in [('tile','地表材质'),('scenery','地景'),('building','建筑')]:
        text += f'| {label} | {old_counts[category]} | {generated_counts[category]} | {installed_counts[category]} | {target_counts[category]} |\n'
    text += f'| 合计 | 74 | {len(originals)} | {len(current)} | 870 |\n'
    text += '''
新增计划具体包括：176 张草地、干草、岩质地、林下土、湿土、水面、沙土、砾土和冲积土材质；144 张疏密针阔叶林与林缘；240 张具有横向/纵深轮廓的丘陵、山脊和高峰；96 张露岩、芦苇、河岸、海岸细节；140 张地区化村镇、县城、省城符号、车站和码头。华北村落池达到 26 个轮廓，华南村落池达到 10 个，优先改善现有中国战役的建筑重复。

素材库不等于同屏密度。图库中有 870 张，不表示一个地格叠放多张图，也不表示没有资料的地区可以增加森林、村庄或水道。

## 画面与选材

美术对照延续 [EW6 地图差距评估](25_欧陆战争6地图资源差距评估.md) 保存的官方画面依据。素材采用低饱和鼠尾草绿/灰石色、统一左上光照和 55 度俯视，轮廓内包含明确的亮面、背光面、树冠层次和屋面高度。地表材质通过原生网格以中心至边缘渐隐显示；连续陆地底面、河道和半透明控制层继续可见，操作格保持 48 像素半径。

地景按全部源候选的稳定空间顺序选图，附近使用过的同一原图会被避开。山体约束半径 270 世界单位，树林/岸边细节 250，地表 180，聚落 450。它们用于减少同一轮廓在附近重复，不构成地理距离或历史覆盖率声明。平移、缩放和阵营占领不会重新随机洗牌，也不会消费战斗随机数。

丘陵、山地和高峰由来源地形分类决定；山脊横向/纵向选择使用源邻格高程的最小曲率方向。连续明暗来自米制高程梯度；亚洲战略图已用真实 DEM 修正旧矩形山地区域，仍不绘制暗示村级精度的大陆等高线。每个独立地景保持原图长宽比与测得的脚点，按脚点深度排序；完整原图显示范围需要避开真实海岸、主支流和铁路。地表选材按地理来源决定，具体变化见 [地表材质与细水系](29_地表材质与细水系.md)。

## 史实与地理边界

本轮没有修改行政边界、政治归属、城市坐标、海岸、原始主河流、铁路拓扑或基础格网。亚洲规则地形有意修正为真实 DEM 分类，内容指纹随之变化；战役地图保留原 DEM 分类。新增细河网是单独的有来源显示层，其现代推算精度与历史限制单列。沿河/沿海装饰只从已归档向量线生成候选，岸上偏移用于图符留白，不表示实测河宽、海滩宽度或历史河岸位置。新图形不能据此新增桥梁、湖泊或地名。

森林继续限于原始森林格与 8–9 处随年代生效的来源林地节点，不把现代潜在生态区回填为 1840—1940 年的全域森林。盐生草甸／洪泛生态区可引用湿土底材作为区域地表参考，但不因此生成积水或断言某年的沼泽范围；缺少具体覆盖证据时，不用芦苇图符随机种满沼泽。平原河岸仅选已目视检查过的六张低草丛，带岩石隆起的河岸和海岸图限定已有山丘地形，不向天津等平坦冲积区添加岩岸地貌。低草丛不等于历史湿地范围。

建筑地区由真实地点与文化绑定决定，占领后不变成占领方建筑；角色、港口和车站仍由已有地点及玩法状态决定。八组地区建筑属于 1940 年以前的通用建筑符号，不能当作北京、首尔、东京等地点的实测街区复原。拉萨、乌兰巴托等需要独立核实的特殊地点保留既有回退，不硬套不适合的建筑族；真实关隘专属图符继续保留。

## 原图、导入与验证

原图、提示词、每次生成日志和 SHA 逐张保留于 `output/imagegen/warlord/ew6_v025/map_bank_v0212/`。`map_bank_plan.json`、`map_settlement_extension_plan.json` 和 `map_surface_extension_plan.json` 分别封存基础、建筑追加和地表追加计划，不改写已经生成的提示词或 PNG。全部新增图使用 `sub2-image-gen / gpt-image-2.5 / high`；不裁图、重绘、拼装或把复制图计数。Godot 使用独立原图引用、原生纹理导入、控件与网格绘制。

新地景/地表导入最长边 256 像素，建筑 384 像素，启用 mipmap；原始 PNG 保持字节。透明边界核验允许角点至多 1/255 的 alpha 量化噪声，逐图记录实值，保留原始字节而不擦除边缘。地图纹理按需加载，资源引用缓存最多保留 384 项；当前绘制网格和纹理另保留必要引用，因此这不是 GPU 总内存硬上限，仍需实测当前导出。细节使用空间索引与缩放门槛，保持近景可读和远景层次。

独立证据分别为：`map_bank_generation.json`、`map_settlement_extension_generation.json`、`map_surface_extension_generation.json`（生产）；`map_bank_installation.json`（安装）；`map_bank_asset_audit.json`（源图、提示词、尺寸、透明边缘与导入）；`map_bank_similarity_review.json`（内存内整幅指纹与近似图对筛查）；`map_bank_visual_review.json`（实际看过的完整原图与原生图库页面，和正式美术批准分开）；`map_bank_tests.json`、`relief_surface_tests.json`、`surface_geography_tests.json`（规则隔离、地理约束与选材）；`map_bank_native_evidence.json`（当前 EXE 的真实地图视口）。

原生素材检查界面只用来查看完整单张原图，其截图不是新生成概念图或最终实机地图。最终外观需要直接检查游戏视口；自动指纹与数量检查不替代人工美术批准，也不证明达到 EW6 商业质量。具体测试状态以 [测试与验收](05_测试与验收.md) 和本轮交付清单为准，Motorola X30 物理设备状态单列。
'''
    evidence=read(P/'reports/map_bank_native_evidence.json')
    if evidence.get('passed') and evidence.get('version')==current_version():
        text+='\n## 当前原生地图画面\n\n'
        for row in evidence['captures']:
            text+=f'- [{row["label"]}](../{row["file"]})\n'
    (P/'docs/28_地图素材扩充与去重.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(complete_installed=bool(complete), generated=len(originals), installed_map_assets=len(current)), ensure_ascii=False))


if __name__=='__main__':
    main()
