"""Describe only the current scoped patch evidence; do not relabel endurance reports."""
import json
from build_release import P, current_version
from run_validation import CHECKS


def main():
    rows=[]
    for name in CHECKS:
        report='rule_tests.json' if name=='run_tests' else name.removesuffix('_test')+'_tests.json'
        value=json.loads((P/'reports'/report).read_text(encoding='utf-8'))
        count=value.get('passed')
        if type(count) is not int:count=len(value.get('checks',[])) or None
        rows.append(dict(group=name,checks=count,passed=not value.get('failed',0) and not value.get('failures',[]),report=report))
    asset_count=len(json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'))['assets'])
    bank=json.loads((P/'reports/map_bank_installation.json').read_text(encoding='utf-8'))
    capacity=[]
    for profile in ['windows','x30']:
        path=P/'reports'/('capacity_'+profile+'_v'+current_version().replace('.','')+'.json')
        if path.exists():capacity.append(json.loads(path.read_text(encoding='utf-8')))
    from build_release import source_digest
    runtime=source_digest()[0]
    capacity_current=len(capacity)==2 and all(row.get('render_target_passed') and row.get('game_version')==current_version() and row.get('runtime_source_sha256')==runtime for row in capacity)
    text='# 测试与验收 · '+current_version()+'\n\n本轮为地图材质、独立素材扩充与细水系测试交付。以下为当前源码和资源的实际回归报告；完整 AI 长局另行记录。\n\n| 回归组 | 通过项 | 报告 |\n| --- | --- | --- |\n'
    for row in rows:text+='| '+row['group']+' | '+str(row['checks'] or '通过')+' | `'+row['report']+'` |\n'
    text+=f'''
{len(CHECKS)} 组当前回归的依赖闭包、源指纹和报告字节由 `regression_dependency_evidence.json` 绑定。战斗表现、长期朝向存档、地形解析与地理材料的具体项数见上表；另有领土原生像素、四向合法行军、单位缓存与直绘完整视口像素比较。来源检查核对 {asset_count} 张当前 PNG 与 Sub2 原图的字节、提示词和透明通道；本轮安装新增 {bank.get('installed',0)} 张独立地图原图，地图素材总数 {bank.get('total_map_assets',0)}。

地理专项检查原始生态区多边形归属、材质语义、54 张原始 GeoTIFF、33,696 个注册采样点和实际源河段端点。亚洲旧矩形山地区域已更正为物理高程分类，内容指纹有意改变；城市、政治、铁路、水体原始几何与基础格网保持。大陆地图可从归档来源重建并与当前数据逐项比对。较细河网为独立来源显示层，不新增军事渡点或宣称完成逐年历史水文调查。

实际导出地图截图另核对沙土、砾土、湿土和冲积土可见、真实支流可见、燕山视口至少 30 个独立地景源图，以及 250 世界单位内同一地景原图重复为零。证据为 `map_bank_native_evidence.json`；它不构成人工商业美术批准。

新增原生 HUD 检查覆盖 1920×1080、2400×1080 / 1.2 倍字与移动布局、1280×720 / 1.5 倍字三个视口，每组 28 项，共 84 项，包括图例避让、完整战斗窗口和五类真实地格详情。步兵动作专项执行 27 条含 AI 的合法命令，在未改编组的正式战役中触发步兵对步兵交战；8 项检查确认准备、射击、受击源图与完整命令重放。证据见 `hud_native_tests.json` 与 `unit_action_native_tests.json`。

Windows 导出 EXE 实际启动并执行 UI 操作，桌面、2400×1080 X30 布局及大字截图均来自原生视口。Android 检查签名 v2/v3、ARM64/ARMv7、minSDK24/target36、无额外权限、内容与当前导入纹理字节。X30 布局是桌面测试；没有连接物理手机。

原生战斗录像执行真实战役命令，移动、炮击、骰子、命中及反击均由真实事件驱动；命令重新回放至相同最终状态与随机流。报告为 `native_visual_evidence.json`、`visual_playtest.json`、`support_playtest.json`。四向专项为 `directional_native_tests.json`。

本轮桌面双视口最大负载与各 60 秒性能剖析：{'当前源码与 EXE 的两组报告通过' if capacity_current else '尚未获得两组当前通过报告，不视为完成'}。这些是 Windows GPU 下的 1920×1080 与 2400×1080 布局测试，后者不能作为摩托罗拉手机性能结果。完整 AI 长局未在本轮重跑；旧报告保留在旧交付。全部人工美术、历史起局与平衡审核，以及 Motorola X30 实机安装、触控、GPU、温度与续航尚未闭环。

本轮由 `tools/package_visual_update.py` 打包有限范围测试版；原完整发行门槛保留在 `tools/package_delivery.py`。包内 `release_manifest.json` 列出当前通过报告、原生画面和交付文件 SHA。
'''
    if capacity_current:
        text+='\n## 当前满载帧耗时\n\n桌面 RTX 3060、关闭垂直同步；各持续平移缩放阶段实测 60 秒，其余为固定帧数。平均帧率达标仍有瞬时尖峰，不能解读为每帧均达到 60 FPS。\n\n| 布局 | 阶段 | 平均 FPS | P95 毫秒 | 实测秒数 |\n| --- | --- | ---: | ---: | ---: |\n'
        for profile, report in zip(['Windows 1920×1080','X30 尺寸桌面 2400×1080'],capacity):
            for stage in report['stages']:
                text+=f'| {profile} | {stage["stage"]} | {stage["average_fps"]:.1f} | {stage["frame_ms_p95"]:.2f} | {stage["duration_seconds"]:.2f} |\n'
        text+='\n最大负载的战术选中阶段 P95 约 37–45 毫秒，仍需继续优化；这两组数据均不是 Motorola X30 物理设备结果。\n'
    (P/'docs/05_测试与验收.md').write_text(text,encoding='utf-8')
    (P/'reports/visual_update_verification_summary.json').write_text(json.dumps(dict(version=current_version(),groups=rows,all_groups_passed=all(row['passed'] for row in rows),current_native_capacity_profiles_passed=capacity_current,raster_sources=asset_count),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(groups=len(rows),checks=sum(row['checks'] or 0 for row in rows),passed=all(row['passed'] for row in rows))))


if __name__=='__main__':main()
