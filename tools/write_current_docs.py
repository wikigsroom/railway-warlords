"""Publish release evidence from actual current-version verification reports."""
from pathlib import Path
import json
from build_release import current_version, android_version_code

P=Path(__file__).resolve().parents[1]
PROFILE_NAMES={'windows':'桌面1920×1080','x30':'桌面移动布局2400×1080'}
STAGE_NAMES={'atlas_static':'全图静止','atlas_pan':'全图平移','tactical_select':'战术点选','sustained_pan_zoom':'60秒持续平移缩放','battle_active':'实际攻击'}
DISTRIBUTION_NAMES={'balanced':'120 / 120编队','concentrated':'216 / 24编队','single_faction':'单势力240编队'}
def read(name):return json.loads((P/'reports'/name).read_text(encoding='utf-8'))
def write_performance_document(performance,pixels,equivalence,capacity_rows,render_rows):
    snapshots=read('snapshot_optimization_tests.json')
    retained_attempts=[]
    for name in ('capacity_domain_v024_under_concurrent_soak.json','capacity_domain_v024_isolated_attempt.json'):
        path=P/'reports'/name
        if path.exists():
            attempt=read(name)
            maximum=max(row['timings']['ai_phase_ms_max'] for row in attempt['results'])
            retained_attempts.append(f'`{name}`：最慢完整阶段{maximum:.2f}ms。')
    attempt_note=' '.join(retained_attempts)
    pixel_rows='\n'.join(f'| {r["name"]} | {r["mean_channel_difference_0_255"]:.6f} / 255 | {r["maximum_channel_difference"]} / 255 |' for r in pixels['cases'])
    domain_status='完整阶段5秒、预览P95 50ms、读写1秒的桌面容量门槛通过。' if performance.get('domain_performance_targets_passed',performance['passed']) else '规则层性能目标尚未全部达到：完整阶段目标5秒、预览P95目标50ms、读写目标1秒。表中保留实际最慢阶段；performance_evidence.json的passed保持false。此包为明确记录该限制的可玩测试版，正式发行仍需达标。'
    detail=f'''# 容量性能与渲染等价 · {current_version()}

本章记录最终源码和导出EXE的实际测试。最大负载是一张按实际东部中国征服图的完整QA地理，74762总格、71386有效格、13兵种/240活跃编队；测试编队位置只用于负载测试，不作为1924年军事部署发布。固定QA随机种子保证重复测量，正常新战局仍随机初始化骰流。

## 原有瓶颈与修复

保留的0.2.0导出EXE在240编队全图平移样本仅30.60FPS；其中静止样本因测量前相机焦点延后覆盖，仅14编队处于视野，不能当作240编队静止基线。源工程的CPU剖析用于定位，和最终EXE帧率分列：部队逐帧排序、阴影/图像提交及无效候选搜索占用了主要时间。旧容量测量使用各次真实初始化的不同随机种子，因此不将不同版本的累计击杀或命令数量差异解释为算法行为变化；本版另按相同状态对照旧实现完整阶段。

渲染沿用原生GPU SubViewport缓存地形和静态部队。活动单位按原先绘制顺序插入各静态段，原生行军、射击、命中、反击与骰子继续逐帧绘制；前景标签和效果独立更新。透明纹理使用预乘Alpha混合，修复缓存阴影边缘偏暗。阴影几何直接复用Godot网格，不修改任何素材PNG。全图缩放下限按各图实际范围计算，五图均验证四角能收入视野。

AI按实际射程索引候选目标，保留敌军/城防顺序与评分；小目标集合直接检查占用格，空集合立即返回。桥渡静态邻接按不可变地理缓存，桥损和日期继续逐次校验；编辑态可变几何会重建。没有减少寻路预算、跳过行动或强制结束阶段。

0.2.4将完整加载后的定义表逐层设为只读；移动查询缓存共享这些不可变定义，编辑态可变定义仍逐次复制。铁路路径和资料编号逐层只读共享，桥损、容量和其他可变状态继续独立复制。全可见场景省去无效视野源计算，移动撤销判断直接比较探索格数量。地图和占位索引直接以Vector2i坐标为键，省去每次查询的字符串格式化；存档与对外格号保持原格式。寻路缓存只复制实际影响通行的当前视野，不复制探索记录与敌军历史影子；同版本下的敌军显隐变化有单独回归。以上改变不调整规则数值、地图格数、AI行动数或寻路预算。

既有性能优化阶段的超时实测保留：{attempt_note} 这些失败结果没有替换为达标数字，最终样本与之分列。

## 最终原生渲染

两套布局在同一Windows本机EXE/RTX3060依次测试，关闭垂直同步并解除帧上限。持续平移缩放每套至少60秒，整个阶段保留240活跃部队、240可见并实际绘制的部队。实际战斗使用合法Attack命令和真实骰流。平均FPS和P95帧时间分别列出，平均60FPS通过不代表每一帧都小于16.67ms。

| 桌面布局 | 场景 | 平均FPS | 帧时间P95 | 最少可绘部队 |
| --- | --- | ---: | ---: | ---: |
{render_rows}

X30布局指桌面2400×1080、120%字号和移动端控件；它没有测量手机GPU、触摸、温度或续航。原始帧时间、原生截图、GPU信息、测试时间和实际攻击命令在`capacity_windows_v{current_version().replace(".", "")}.json`、`capacity_x30_v{current_version().replace(".", "")}.json`及同名日志内。

## 规则层与存档

三种分布为两势力各120编队、216/24编队、单势力240编队。每种以同一起始状态分别运行3个完整AI阶段，所有命令经过正式CommandKernel；测量包括规划、提交和不变量检查，没有动画等待。每种另执行10次存档完整往返；只读地图、生命、资源、占位和随机状态均检查。

| 分布 | 预览P95 | 完整AI阶段最慢 | 写档P95 | 读档P95 |
| --- | ---: | ---: | ---: | ---: |
{capacity_rows}

{domain_status}AI与玩家命令的规则计算移至一个串行原生线程，主线程只提交完整结果；两套最终EXE布局各测25条实际命令，包含24条自动命令、一条真实结束回合命令、首轮及同步信号回调，提交最大值均不超过8ms。暂停、取消、读档和线程隔离见[后台规则与响应性](13_后台规则与响应性.md)。该证据不覆盖首次建图、OS生命周期通知或物理Android帧时间。

## 规则等价与缓存像素检查

旧AI、移动规则来自不可变0.2.0源码包，旧可视性规则来自0.1.3源码包，保留来源SHA，参考文件仅改独立类名。对33个发布场景的实际起局及后续命令、海运/临时揭雾、桥渡修改、13兵种路径与240编队三种分布完整阶段做有序对比。本次{equivalence['passed']}项通过，{equivalence['trace_commands']}条命令一致，0失败；状态、事件和随机流也按完整指纹核对。它是程序等价证明，不能代替战役军事史或人工难度审核。

另与已交付0.2.3源码包的原始快照访问和命令内核比较，本次{snapshots['passed']}项通过、{snapshots['trace_commands']}条命令一致。覆盖有迷雾的发布关卡及三种240编队分布的完整阶段、输入隔离、铁路编辑态、定义重载和可变数据变化。参考文件只改独立类名、对应访问类引用及派生查询缓存的命名空间；新旧内部索引使用不同键格式，不能共用同一个私有缓存。原有规则和快照操作逐字保留，实际旧ZIP、原成员SHA及上述机械替换亦独立核验。每一步保留全部状态字段、事件、预览和随机数；只有逐层只读的几何与视野数组可以复用其原始序列化SHA，浅只读且含可变子项的容器不得复用。各条轨迹起止另核对原始完整状态指纹。

完整视口对比使用同一暂停原生场景分别直接绘制与缓存绘制，不裁图、不生成拼图、不调整图片。每组同时校验绘制顺序和状态/随机数不变。

| 原生场景 | 平均通道差异 | 最大通道差异 |
| --- | ---: | ---: |
{pixel_rows}

本次通过检查的8张整幅原始PNG均保留，微小差异来自透明RGBA8纹理和抗锯齿取整。0.2.5初次远景检查曾出现57/255的局部差异，现以像素对齐的不透明编队标记修复，正常战术视图继续使用完整军阵，检查阈值未放宽。初次失败的数字报告全部保留，失败轮原图仅有2张能与原SHA核对，其余6张已被重测覆盖；不能据此宣称保留了完整失败原图集。封存文件`performance_evidence.json`记录最终完整运行源码SHA、逐报告SHA和导出产物对应关系；包装工具拒绝修改后的报告和旧源码构建。规则层耗时未达标时，默认拒绝包装；显式的`--allow-domain-timing-limited-beta`仅允许功能、语义、像素、原生渲染及8ms提交检查全部通过的测试版，性能结果仍记录false，限制写入交付清单。此前各次未达标实测报告一并保留。

仍需逐关人工策略/难度、人物与装备及军事起局历史核对、全部运行素材正式审核、物理X30验收。本版采用ruleset8与新地图坐标；旧版战局使用对应旧包继续，养成档案独立保留。此前九套交付包和设计归档保持原字节。

[当前总体验收](05_测试与验收.md) · [地图样式](10_地图绘制与可读性.md) · [系列玩法与动画核对](11_系列对标与实机修复.md)
'''
    (P/'docs/12_容量性能与渲染等价.md').write_text(detail,encoding='utf-8')

def main():
    names=[('规则','rule_tests.json'),('验收','acceptance_tests.json'),('输入','input_tests.json'),
           ('历史地理','geography_tests.json'),('养成与军团','progression_tests.json'),
           ('地图事务','transaction_tests.json'),('历史事件与结算','strategic_history_tests.json'),
           ('地图绘制','atlas_render_tests.json'),('战斗、骰子与演出','combat_presentation_tests.json'),
           ('自动作战','automation_tests.json'),('后台规则与保存','rules_worker_tests.json'),('五倍格网与读档','map_scale_tests.json'),('补给算法等价','scaled_logistics_tests.json'),('移动查询缓存等价','movement_cache_tests.json'),('历史聚落交互','historical_places_tests.json'),('旧版事务与只读共享等价','snapshot_optimization_tests.json')]
    fixture=read('sample_state_v2.json');rows=[];total=0
    for label,name in names:
        result=read(name)
        if result.get('content_hash',fixture['content_hash'])!=fixture['content_hash'] or result.get('failed',0) or result.get('failures',[]):raise SystemExit('Current passing report required: '+name)
        count=result.get('passed',len(result.get('checks',[])))
        if isinstance(count,bool):count=len(result.get('checks',[]))
        total+=count
        rows.append(f'| {label} | {count}项通过，0失败 | `{name}` |')
    resources=read('resource_validation.json');soak=read('ai_soak.json');full=read('ai_full_conquest.json')
    endurance_path=P/'reports/endurance_evidence.json'
    endurance=read('endurance_evidence.json') if endurance_path.exists() else None
    accessibility_path=P/'reports/accessibility_evidence.json'
    accessibility=read('accessibility_evidence.json') if accessibility_path.exists() else None
    endurance_section=''
    if endurance:
        endurance_section=f'''\n## 长期状态、存档回放与可读性\n\n独立QA运行 `{endurance['run_directory']}` 完成{endurance['completed_rounds']}回合、{endurance['commands']}条正式AI命令；20个随机阶段写入并重新加载完整状态，每个阶段回放3条真实命令，累计{endurance['replayed_commands']}条，随后继续从加载后的状态运行。发布征服剧本仍保持80回合，QA局只增加截止预算；非QA定义、规则依赖和内容文件运行前后SHA一致。此证据证明长期状态与存档随机流稳定，不替代33题人工策略/历史审核。\n\n'''
    accessibility_section=''
    if accessibility:
        profiles='；'.join(f"{row['name']}={row['passed']}（{row['resolution']}，{row['ui_scale']:.1f}×）" for row in accessibility.get('profiles',[]))
        accessibility_section=f'''\n## 尺寸、字号、弹窗与静音\n\n原生Godot窗口通过实际鼠标分发、控件边界、暂停遮罩、音效/音乐开关和完整状态哈希检查：{profiles}。1280×720的标准字号和150%大字均通过；另外的3840×2160逻辑画布大字配置通过了布局、输入与状态检查，但不生成伪造的栅格截图。当前显示器为2560×1440，真实3840×2160桌面窗口仍被系统限制为约2564×1421，4K原生像素记录保留为硬件限制，不能把缩小窗口冒充4K验收。连接支持该分辨率的显示设备后复核原生4K。原始整幅PNG、逻辑画布记录、控件坐标和日志在 `{accessibility['run_directory']}`。\n\n'''
    for result in [soak,full]:
        if result['content_hash']!=fixture['content_hash'] or not result['invariants_passed']:raise SystemExit('Fresh current AI report required.')
    movie=read('visual_playtest.json');support=read('support_playtest.json');benchmark=read('desktop_benchmark.json')
    if not movie['passed'] or not support['passed'] or benchmark['content_hash']!=fixture['content_hash']:raise SystemExit('Fresh native evidence required.')
    performance=read('performance_evidence.json');pixels=read('unit_layer_pixel_validation.json');equivalence=read('performance_equivalence.json')
    if not performance.get('native_and_semantic_checks_passed',performance['passed']) or performance['version']!=current_version():raise SystemExit('Current maximum-map evidence is required.')
    domain_status='规则层容量耗时目标通过。' if performance.get('domain_performance_targets_passed',performance['passed']) else '规则层容量耗时目标尚未全部通过；表中列出实际值，正式发行仍需满足完整AI阶段5秒等门槛。当前交付为记录该限制的可玩测试版。'
    capacity_rows='\n'.join(f'| {DISTRIBUTION_NAMES[r["distribution"]]} | {r["timings"]["preview_ms_p95"]:.2f} ms | {r["timings"]["ai_phase_ms_max"]:.2f} ms | {r["timings"]["save_write_ms_p95"]:.2f} ms | {r["timings"]["save_read_ms_p95"]:.2f} ms |' for r in performance['domain_results'])
    render_rows='\n'.join(f'| {PROFILE_NAMES[profile["file"].split("_")[1]]} | {STAGE_NAMES[stage["stage"]]} | {stage["average_fps"]:.2f} | {stage["frame_ms_p95"]:.2f} ms | {stage["minimum_drawable_units"]} |' for profile in performance['render_profiles'] for stage in profile['stages'])
    rejects=sum(c['rejects'] for c in soak['results']);full_rejects=sum(c['rejects'] for c in full['results'])
    table='\n'.join(rows)
    conquest='\n'.join(f'| {r["id"]} | {r["player"]} | {r["completed_rounds"]} | {r["commands"]} | {r["status"]} |' for r in full['results'])
    text=f'''# 测试与验收 · {current_version()}

本版使用Godot4.7.2、schema2、ruleset8；下列数字来自当前内容报告。程序规则、原生画面、资料来源与物理设备验证分别记录。

| 检查 | 实际结果 | 报告 |
| --- | --- | --- |
{table}

共{total}项通过，0失败。资源检查另验证{resources['raster_count']}张PNG的来源SHA/透明度、{resources['audio_count']}段非静音WAV、{resources['font_count']}个OFL字体、21张原始定义表及五图/33任务的引用。源图与工程副本逐字节一致，没有手工拼接或改绘。

## 原生游玩与导出

Windows导出的EXE实际启动并操作征募、建设、外交、暂停、两层精锐军团编组和部署。桌面、X30尺寸、150%字体、历史全图、军团桌面/移动布局均直接截取原生视口，附内容指纹与版本元数据。

`visual_playtest.json`记录山海关防守关卡实际执行{len(movie['native_commands'])}条双方命令，{movie['moves']}次行军、{movie['attacks']}次主攻、{movie['counterattacks']}次反击、{movie['dice_rolls']}组掷骰。按完整命令重放与实际最终状态相同；炮兵、行军、开火和命中均出现在实际时间线。

`support_playtest.json`使用发布的山海关防御剧本，通过合法建设命令及正常敌我回合完成机场，再执行航空侦察和轰炸；建设全过程可重放，未调整初始部队、血量或地图。玩家新建设施不宣称为历史机场部署。MP4由Godot原生MovieWriter输出编码，没有叠加截图、设计稿、字卡或模拟伤害；离线录像渲染速度不当作运行帧率。

{endurance_section}{accessibility_section}

`map_1925_calendar_fixture`仅校验1925年名称，明确标记日历测试状态，不证明实际游玩至该日期。

{current_version()}按《欧陆战争6》方向接入53项独立Sub2素材，强化连续势力分色、自然地表、立体军阵、钢灰HUD和真实事件战斗小窗；领土的实际像素检查及对照范围见[欧陆战争6对标与美术改版](16_欧陆战争6对标与美术改版.md)。

新增67处历史聚落、村镇分级查询和按年代省级轮廓裁切的当前战局色块，来源几何另有202项独立检查。导出EXE保留全图、省城、县城、集镇、村落及X30尺寸查询截图，详见[历史聚落与势力地图](15_历史聚落与势力地图.md)。

Android APK核验Code{android_version_code()}/Name{current_version()}、ARM64/ARMv7、minSDK24/target36、v2/v3签名、无申请权限、{len(read('apk_content_validation.json')['files'])}份源码数据/许可及当前导入纹理字节，其中包含聚落JSON。ADB设备状态见`android_devices.log`；桌面X30尺寸检查不代表手机触摸、GPU、发热或续航实测。没有使用Docker、WSL或模拟器。

## AI对局回归

短局覆盖18战役×3难度、3征服日期包各含默认/弱势玩家、12训练，共{soak['cases']}例、累计{soak['completed_rounds']}回合、{soak['commands']}条命令、{rejects}拒绝。生命、弹药、资源、占位不变量通过；不是33题人工通关或策略平衡证明。

完整征服按实际80回合期限，正常胜负或期限终止。强/弱标签仅为游戏挑战配置。

| 日期包 | 玩家 | 完成回合 | 命令 | AI结果 |
| --- | --- | ---: | ---: | --- |
{conquest}

合计{full['completed_rounds']}回合、{full['commands']}条命令、{full_rejects}拒绝。跨场累计不等于单局100回合；本次是否存在单局100回合：{full['single_match_100_rounds']}。两类已完成测试最初写入同一默认路径，完整征服覆盖短局汇总；按完整原生日志的72条记录恢复短局字段，并保存6局完整原报告原字节，出处与SHA见ai_log_reconciliation.json。没有模拟或改写单局数据。

## 性能与资料范围

最终Windows EXE已用74762总格/71386有效格、240编队在1920×1080桌面与2400×1080/120%移动布局进行测试；两套布局均覆盖全图静止、平移、战术点选、60秒持续平移缩放和真实合法攻击，各阶段均达到平均60FPS。原始逐帧时间和完整测试部署随工程提供。

| 规则分布 | 预览P95 | 完整AI阶段最慢 | 写档P95 | 读档P95 |
| --- | ---: | ---: | ---: | ---: |
{capacity_rows}

{domain_status}

另有{performance['semantic_checks']}项原实现等价检查、{performance['pixel_comparisons']}组同一暂停场景完整视口像素对比；单位绘制顺序、命令、状态、事件与随机流均核对。详见[容量性能与渲染等价](12_容量性能与渲染等价.md)。这些是本机RTX3060桌面结果；最终EXE的活动战局规则提交满足样本中的8ms上限，数据范围见[后台规则与响应性](13_后台规则与响应性.md)；手机GPU/触摸/发热仍需物理X30。

精度、历史与风格修复见[历史地理](07_历史地理与地图美术.md)、[地图绘制](10_地图绘制与可读性.md)和[系列对标与实机修复](11_系列对标与实机修复.md)。剩余正式发行验收为33题人工平衡、军事起局/装备/县界及全部素材发行审核及物理X30。原设计和0.1.0–0.2.4的九套既有发布包保持原字节。

当前内容指纹：`{fixture['content_hash']}`。AI短/长局报告另绑定规则依赖SHA及原报告字节，只有规则未变才保留已完成对局证据；本版{len(names)}组检查、原生画面与双端构建均按最终源码重新验证。双端导出记录完整运行源码SHA与产物SHA；打包拒绝版本不符、依赖或报告改变、源码改变后的旧构建和错误日志。
'''
    (P/'docs/05_测试与验收.md').write_text(text,encoding='utf-8')
    write_performance_document(performance,pixels,equivalence,capacity_rows,render_rows)
    print(f'Wrote current evidence: {total} checks, {soak["cases"]} AI cases.')
if __name__=='__main__':
    import sys
    if '--performance-only' in sys.argv:
        performance=read('performance_evidence.json');pixels=read('unit_layer_pixel_validation.json');equivalence=read('performance_equivalence.json')
        if not performance.get('native_and_semantic_checks_passed',performance['passed']) or performance['version']!=current_version():raise SystemExit('Current maximum-map evidence is required.')
        capacity_rows='\n'.join(f'| {DISTRIBUTION_NAMES[r["distribution"]]} | {r["timings"]["preview_ms_p95"]:.2f} ms | {r["timings"]["ai_phase_ms_max"]:.2f} ms | {r["timings"]["save_write_ms_p95"]:.2f} ms | {r["timings"]["save_read_ms_p95"]:.2f} ms |' for r in performance['domain_results'])
        render_rows='\n'.join(f'| {PROFILE_NAMES[profile["file"].split("_")[1]]} | {STAGE_NAMES[stage["stage"]]} | {stage["average_fps"]:.2f} | {stage["frame_ms_p95"]:.2f} ms | {stage["minimum_drawable_units"]} |' for profile in performance['render_profiles'] for stage in profile['stages'])
        write_performance_document(performance,pixels,equivalence,capacity_rows,render_rows)
        print('Wrote current native maximum-map evidence.')
    else:main()
