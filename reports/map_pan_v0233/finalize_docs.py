"""Update current bilingual entries after viewing all ten shipping captures."""
from pathlib import Path
import hashlib
import json
import shutil

P=Path(__file__).resolve().parents[2]
R=P/'reports/map_pan_v0233'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def replace_line(name,prefix,new):
    new=benchmark_text(new)
    p=P/name;lines=p.read_bytes().splitlines(keepends=True);found=0
    for i,line in enumerate(lines):
        if line.decode('utf-8').startswith(prefix):
            eol=b'\r\n' if line.endswith(b'\r\n') else b'\n'
            lines[i]=new.encode('utf-8').replace(b'\n',eol)+eol;found+=1
    assert found==1,(name,prefix,found)
    p.write_bytes(b''.join(lines))
def insert(name,marker,note):
    note=benchmark_text(note)
    p=P/name;raw=p.read_bytes();a=marker.encode('utf-8');assert raw.count(a)==1
    eol=b'\r\n' if b'\r\n' in raw else b'\n'
    p.write_bytes(raw.replace(a,note.encode('utf-8').replace(b'\n',eol)+a,1))

def benchmark_text(value):
    pan=read(R/'abba_summary.json');old=[r for r in pan['stages'] if r['legacy_methods']];new=[r for r in pan['stages'] if not r['legacy_methods']]
    def band(rows,key,separator):return ('%.1f'+separator+'%.1f')%(min(r[key] for r in rows),max(r[key] for r in rows))
    for before,after in [('101—134',band(old,'p95_ms','—')),('26—27',band(new,'p95_ms','—')),('44—48',band(new,'max_ms','—')),('101–134ms',band(old,'p95_ms','–')+'ms'),('26–27ms',band(new,'p95_ms','–')+'ms'),('44–48ms',band(new,'max_ms','–')+'ms')]:value=value.replace(before,after)
    return value

def main():
    runtime=read(P/'reports/export_results.json')[0]['runtime_source_sha256']
    maps_root=P/'reports/screenshots/map_composition_native/v0233/verified_export_01'
    maps=read(maps_root/'validation.json');shipping=read(R/'shipping_01/validation.json')
    assert maps['passed'] and shipping['passed'] and maps['runtime_source_sha256']==shipping['runtime_source_sha256']==runtime
    frames=maps['captures']+shipping['captures'];assert len(frames)==10
    viewed=[]
    for frame in frames:
        path=Path(frame.get('image',frame.get('path')));path=path if path.is_absolute() else P/path
        assert sha(path)==frame['sha256']
        viewed.append(dict(path=path.relative_to(P).as_posix(),sha256=frame['sha256'],viewed_complete_image=True))
    write(R/'visual_review.json',dict(runtime_source_sha256=runtime,actually_viewed_complete_images=viewed,formal_art_approval=False,ew6_parity_claimed=False,remaining_visible_gaps=['repeated mountain miniatures','angular waterways','Wuhan map-edge margins','broad homogeneous alluvial ground','incomplete unit actions']))
    media=read(P/'docs/media/manifest.json')
    selections=[(R/'shipping_01/home','menu-v0233'),(R/'shipping_01/mountains','map-pan-mountains-v0233')]+[(maps_root/name,'map-pan-'+name+'-v0233') for name in ['wuhan','beijing','coast']]
    for source,name in selections:
        target=P/'docs/media'/name
        for ext in ['.png','.json']:
            dst=target.with_suffix(ext);assert not dst.exists();shutil.copyfile(source.with_suffix(ext),dst)
        media['screenshots'].append(dict(file=target.with_suffix('.png').relative_to(P).as_posix(),version='0.2.33',native_source=source.with_suffix('.png').relative_to(P).as_posix(),sha256=sha(target.with_suffix('.png')),metadata=target.with_suffix('.json').relative_to(P).as_posix(),byte_identical_to_native_capture=True,physical_android_device_tested=False))
    media['version']='0.2.33';write(P/'docs/media/manifest.json',media)
    components=read(R/'final_components_02/runs.json')
    count=sum(o['checks'] for r in components['runs'] for o in r['outputs']);total=count+106
    summary=f'{count}项组件、48项正式EXE地表GPU和58项地图布局检查通过，共{total}项专项；10张最终程序整幅画面已完整查看。'
    english=f'{count} component checks, 48 shipping-EXE ground GPU checks and 58 map-layout checks pass: {total} targeted checks. Ten whole final-application frames were viewed.'
    replace_line('README.md','本项目以中国军阀战争为核心，','本项目以中国军阀战争为核心，扩展到 **1840—1940年亚洲时间锚点**。使用 **Godot 4.7.2 / GDScript**，面向 **Windows x86_64与Android ARM64 / ARMv7**。当前源码为 **0.2.33 地图拖动优化测试版**，见[51章](docs/51_地图拖动预取与源线段缓存.md)。本轮预取地形原图并缓存源线段、铁路和地块细节网格；整体美术、完整动作与物理X30验收仍未完成。离线单机；游戏界面为简体中文，README提供中英双语，游戏内英文界面尚未实现。')
    replace_line('README.en.md',"The game centers on China's warlord period", "The game centers on China's warlord period and extends to **Asian starting points from 1840 to 1940**. Built with **Godot 4.7.2 / GDScript**, it targets **Windows x86_64 and Android ARM64 / ARMv7**. Current sources are the **0.2.33 map-panning beta**; see the [scope notes](docs/51_地图拖动预取与源线段缓存.md). Whole terrain originals are prefetched; source lines, rail geometry and ground-detail meshes are cached. Overall art parity, complete unit actions and physical X30 acceptance remain unfinished. It is an offline, single-player game. The game UI uses Simplified Chinese; these READMEs are bilingual, but English game localization is not implemented.")
    replace_line('README.md','![0.2.32正式Windows程序的原生主菜单]','![0.2.33正式Windows程序的原生主菜单](docs/media/menu-v0233.png)')
    replace_line('README.en.md','![Native main menu from the version 0.2.32','![Native main menu from the version 0.2.33 shipping Windows application](docs/media/menu-v0233.png)')
    insert('README.md','0.2.32改善绿色山体与灰岩地面的衔接，','0.2.33减少地图拖动时同步读取原图和重复生成网格的停顿。RTX3060、1920×1080、同一路径的四轮开发引擎旧新方法交替复测中，95分位帧耗时从101—134毫秒降到26—27毫秒；新方法最大帧耗时仍为44—48毫秒。后台负载未全部控制，此结果不代表Android性能。三个固定镜头的新旧整幅截图逐像素一致，地理和全部原图保留。\n\n![0.2.33正式Windows程序：保留山体与地格细节的拖动优化](docs/media/map-pan-mountains-v0233.png)\n\n'+summary+'另见[武汉](docs/media/map-pan-wuhan-v0233.png)、[北京](docs/media/map-pan-beijing-v0233.png)和[山海关](docs/media/map-pan-coast-v0233.png)。本轮未新增栅格素材；旧GIF保留0.2.29身份。\n\n')
    insert('README.en.md','Version 0.2.32 improves the transition','Version 0.2.33 reduces synchronous image reads and repeated mesh generation during panning. Four alternating old/new-method development-engine runs on an RTX 3060 at 1920×1080 measured p95 frame times of 101–134ms versus 26–27ms; optimized maxima remain 44–48ms. Other application load was not fully controlled, and these are not Android results. Three fixed whole-view comparisons are pixel-identical. Geography and all original artwork are preserved.\n\n![Version 0.2.33 shipping Windows: panning optimization with terrain detail retained](docs/media/map-pan-mountains-v0233.png)\n\n'+english+' See [Wuhan](docs/media/map-pan-wuhan-v0233.png), [Beijing](docs/media/map-pan-beijing-v0233.png) and [Shanhaiguan](docs/media/map-pan-coast-v0233.png). No raster originals were added; retained GIFs keep their 0.2.29 identity.\n\n')
    replace_line('README.md','应用 ID 为','应用 ID 为 `org.railwaywarlords.game`，0.2.33预设versionCode38。覆盖更新必须使用相同签名；自行签名不能覆盖原签名安装。仓库的release凭据字段为空。')
    replace_line('README.en.md','App ID is','App ID is `org.railwaywarlords.game`; version 0.2.33 uses versionCode 38. Updating an installed app requires the same signature; a differently signed build cannot replace the original. Tracked release-credential fields are empty.')
    replace_line('README.md','历史章节保留版本语境；当前状态以本README','历史章节保留版本语境；当前状态以本README、[0.2.33地图拖动优化范围](docs/51_地图拖动预取与源线段缓存.md)、完成度和对应报告为准。将领登记与未覆盖范围见[师旅级名册](docs/46_师旅级将领池与战役名册.md)。')
    replace_line('README.en.md','Older chapters preserve their version context.','Older chapters preserve their version context. Use these READMEs, the [0.2.33 map-panning scope](docs/51_地图拖动预取与源线段缓存.md), completion assessment and matching reports for current status. Commander registration and remaining coverage are documented in the [roster chapter](docs/46_师旅级将领池与战役名册.md).')
    replace_line('docs/00_程序文档索引.md','当前实施入口：','当前实施入口：[0.2.33地图拖动预取与源线段缓存](51_地图拖动预取与源线段缓存.md)。双端/code38已构建；'+summary+'未新增或加工PNG，整体欧陆战争6美术与物理X30验收仍未完成。')
    insert('docs/00_程序文档索引.md','| [声音设计]','| [51 地图拖动优化](51_地图拖动预取与源线段缓存.md) | 原图预取、源边界/铁路与细节网格缓存、逐像素保持、四轮开发复测与双端证据 |\n')
    assessment='\n\n'.join(['# 当前完成度评估 · 0.2.33','当前[地图拖动优化](51_地图拖动预取与源线段缓存.md)预取相机周边的完整地形原图，并缓存省界、控制区边缘、铁路几何和地块细节网格。158份规则与地理数据、全部2,509张原图和三首既有配乐保留原字节。','Windows与签名Android/code38已构建。'+summary+'三个固定镜头的新旧绘制逐像素一致；四轮开发引擎交替复测的95分位从101—134毫秒降到26—27毫秒，最大帧耗时仍为44—48毫秒。后台负载未全部控制，不构成手机性能证据。','重复山体、武汉外框留白、粗折线河道、大片相似冲积土、全兵种动作、亚洲历史起局与具体将领部署仍未完成。物理Motorola X30未连接，APK静态检查不能代替实机验收。后续配乐继续使用远程YuE2纯器乐，本轮没有生成或替换音乐。','## 0.2.32归档范围'])
    replace_line('docs/23_当前完成度评估.md','# 当前完成度评估',assessment)
    insert('docs/MEDIA.md','0.2.32新增五张','0.2.33新增五张正式Windows整幅截图：[菜单](media/menu-v0233.png)、[山地](media/map-pan-mountains-v0233.png)、[武汉](media/map-pan-wuhan-v0233.png)、[北京](media/map-pan-beijing-v0233.png)和[山海关](media/map-pan-coast-v0233.png)。10张最终画面已完整查看，见[查看记录](../reports/map_pan_v0233/visual_review.json)。图片按原字节复制；旧GIF身份不变。\n\n')
    replace_line('docs/51_地图拖动预取与源线段缓存.md','最终复测、双端构建与归档证据在完成后补入本章。',summary+'Windows和签名Android/code38绑定同一冻结源码身份；APK的v2/v3签名、双ARM架构、141份数据/说明、2,509张贴图及3首配乐载荷均已核对。物理X30验收仍未完成，既有历史内容、全兵种动作和整体美术仍有缺口。')
    with (P/'docs/51_地图拖动预取与源线段缓存.md').open('a',encoding='utf-8',newline='\n') as stream:
        pan=read(R/'abba_summary.json');stages=pan['stages']
        measured='、'.join(('旧' if r['legacy_methods'] else '新')+('%.3f'%r['p95_ms']) for r in stages)
        misses='、'.join(('旧' if r['legacy_methods'] else '新')+str(r['synchronous_misses_during_pan']) for r in stages)
        stream.write('\n四轮开发复测依次为'+measured+'毫秒（95分位），每轮180帧且全部保持窗口焦点；同步读取次数依次为'+misses+'。后台其他应用负载未全部控制，不属于两份发布二进制的严格实验室对照，也不证明手机流畅度。\n\n正式EXE的[七地图布局](../reports/screenshots/map_composition_native/v0233/verified_export_01/validation.json)、[GPU与界面](../reports/map_pan_v0233/shipping_01/validation.json)、[源码范围](../reports/map_pan_v0233/scope.json)与[四轮开发复测](../reports/map_pan_v0233/abba_summary.json)分别记录。\n')
    print('CURRENT_DOCS_AND_TEN_WHOLE_SHIPPING_IMAGE_REVIEWS_RECORDED',flush=True)

if __name__=='__main__':main()
