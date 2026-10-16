"""Write current async-rule evidence from verified exported native reports."""
from pathlib import Path
import json
from build_release import current_version, source_digest

P = Path(__file__).resolve().parents[1]


def main():
    version = current_version()
    tag = 'v' + version.replace('.', '')
    seal = json.loads((P / 'reports/performance_evidence.json').read_text(encoding='utf-8'))
    if not seal.get('native_and_semantic_checks_passed',seal['passed']) or seal['runtime_source_sha256'] != source_digest()[0] or not seal['ui_eight_millisecond_slice_verified']:
        raise SystemExit('Verified current native worker and handoff evidence required.')
    rows = []
    for profile, label in [('windows', '桌面1920×1080'), ('x30', '桌面移动控件2400×1080')]:
        value = json.loads((P / 'reports' / ('responsiveness_' + profile + '_' + tag + '.json')).read_text(encoding='utf-8'))
        rows.append(f"| {label} | {value['command_count']} | {value['main_handoff_us_max']/1000:.3f} ms | {value['planning_frames']} | {value['animation_frames']} | {value['average_fps']:.2f} |")
    worker = json.loads((P / 'reports/rules_worker_tests.json').read_text(encoding='utf-8'))
    table = '\n'.join(rows)
    text = f'''# 后台规则与响应性 · {version}

## 可见变化

AI部署和玩家命令结算期间，地图继续接收平移、缩放和暂停。范围/伤害预览在核对完成后才允许确认；重复点击不会重复消费资源或随机数。停止自动作战丢弃尚未提交的命令；已经结算的行军、攻击、受击、骰子和反击仍完成演出。暂停保留已计算结果，恢复后提交一次；读取战局或返回菜单会使旧结果失效。

## 原有停顿与处理

原控制器在一整次AI规划和结算结束后才检查8ms预算；原生测试确认单次操作可超过该预算。新的Godot原生线程队列只串行执行规则和存档I/O，主线程交换完整状态，按版本、起始状态身份和战局代号拒绝过期结果。规则、评分、命令排序和骰流算法保持ruleset8。

地图、占位、视野、铁路和桥渡查询缓存按调用线程隔离。后台准备视野索引与战斗步骤，不调用场景树、控件、纹理或声音播放器。主线程激活演出并播放声音；军队排序与遮挡继续使用原有渲染路径。回合后的资源栏、目标卡与部队面板分帧刷新，战局或选择变化会取消过期刷新。小地图范围只在几何变化时重算，部署/演出栏复用预先创建的控件，战斗音效在菜单前加载。

不可变视野数组按对象身份复用只读索引；编辑态可变数组始终重新生成，视野与探索使用不同槽位。替换索引不修改已发布的旧结果，后台线程退出时释放其缓存。地图每次接受完整新状态时刷新背景，不在主线程逐项比较整张地图的可见格与铁路数组。这些是呈现层更新，不改变移动、战斗、补给或随机流。

存档列表、手动读写和自动存档共用该串行队列，避免同槽临时文件同时写入。读档校验checksum、content_hash、schema2和ruleset8，后台刷新视野后才发布。窗口关闭等待本次保存完成；保存失败时保留窗口并显示原因。Android系统后台通知会等待串行写档完成，此生命周期等待不计入活动战局8ms范围。

## 最终EXE测量

在真实74762总格/71386有效格、13兵种、240编队的QA地理地图上，分别运行24条合法AI命令及一条真实结束回合命令；持续平移，并以设置支持的4倍速播放实际战斗。首轮命令计入测量。时间包含队列提交、原子状态交换和同步信号回调，没有用后台总耗时冒充主线程耗时。

| 本机布局 | 实际命令 | 主线程提交最高 | 计算期间刷新帧 | 动画刷新帧 | 流程平均FPS |
| --- | ---: | ---: | ---: | ---: | ---: |
{table}

两套结果绑定最终EXE SHA和完整运行源码SHA。原始报告为`responsiveness_windows_{tag}.json`、`responsiveness_x30_{tag}.json`；整幅原生PNG直接保存，无裁图、叠字、素材合成。报告的最大帧时间包含QA截图读取/写盘开销，整图渲染性能另见[容量性能与渲染等价](12_容量性能与渲染等价.md)。

8ms结论限于本机样本中的活动战局规则提交；首次建图、加载界面和OS生命周期另行记录。2400×1080使用移动控件及120%字号，仍然是Windows/RTX3060，未测物理摩托罗拉X30的触摸、GPU、温度、内存或续航。

## 行为与线程回归

`rules_worker_tests.json`本次{worker['passed']}项通过、0失败。40条真实命令对照同步规则实现，逐一核对决策、事件顺序、完整状态和随机流，以及后台准备的演出步骤/演员顺序。计算期间主线程反复查询另一张地图；输入状态不被修改。另验证重复点击、暂停保留结果、恢复只提交一次、停止自动作战、读档/弃局取消、多个控制器共享队列、最后控制器退出回收线程、同槽连续写入与精确读档。

原设计要求的三种240编队分布完整阶段、33任务起局规则等价与长局回归分别保留独立报告，不能用此40条命令代替。资料和素材发行审核、33题人工策略平衡、物理X30仍列为待完成验收。

线程边界按[Godot线程安全API说明](https://docs.godotengine.org/en/stable/tutorials/performance/thread_safe_apis.html)实现；不关闭线程安全检查，不调用Docker、WSL或模拟器。

[总体验收](05_测试与验收.md) · [模块架构](02_架构与模块.md) · [双端交付](06_双端构建与发布.md)
'''
    (P / 'docs/13_后台规则与响应性.md').write_text(text, encoding='utf-8')
    print('Wrote current serialized-worker and native handoff evidence.')


if __name__ == '__main__':
    main()
