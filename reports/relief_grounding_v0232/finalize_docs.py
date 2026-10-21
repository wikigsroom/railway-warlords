"""Record actually viewed whole shipping images and preserve older media identities."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

P = Path(__file__).resolve().parents[2]
REPORTS = P / 'reports/relief_grounding_v0232'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def replace_line(relative, starts, replacement):
    path = P / relative; lines = path.read_bytes().splitlines(keepends=True); found = 0
    for i, line in enumerate(lines):
        if line.decode('utf-8').startswith(starts):
            ending = '\r\n' if line.endswith(b'\r\n') else '\n'
            lines[i] = (replacement.replace('\n', ending) + ending).encode('utf-8'); found += 1
    assert found == 1, (relative, starts, found)
    path.write_bytes(b''.join(lines))


def main():
    maps = read(P / 'reports/screenshots/map_composition_native/v0232/verified_export_01/validation.json')
    shipping = read(REPORTS / 'shipping_01/validation.json')
    assert maps['passed'] and shipping['passed']
    assert len(maps['checks']) == 58 and shipping['gpu_checks'] == 48
    runtime = maps['runtime_source_sha256']; assert runtime == shipping['runtime_source_sha256']
    frames = []
    for row in maps['captures'] + shipping['captures']:
        raw = Path(row.get('image', row.get('path'))); path = raw if raw.is_absolute() else P / raw
        meta = path.with_suffix('.json'); facts = read(meta)
        assert facts['build_version'] == '0.2.32' and facts['raw_godot_capture']
        assert facts['qa_save_isolated'] and not facts['physical_android_device_tested']
        assert sha(path) == row['sha256'] and sha(meta) == row['metadata_sha256']
        frames.append(dict(path=path.relative_to(P).as_posix(), sha256=sha(path),
            metadata=meta.relative_to(P).as_posix(), metadata_sha256=sha(meta), viewed_complete_image=True))
    assert len(frames) == 10
    review = dict(version='0.2.32', recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        runtime_source_sha256=runtime, windows_exe_sha256=shipping['windows_exe_sha256'],
        actually_viewed_complete_images=frames, unique_viewed_image_sha256s=len({f['sha256'] for f in frames}),
        observed_improvements=['Representative local ground reduces broad gray slabs beneath green mountain sprites.',
            'Full mountain-source sprites remain recognizable with softer lower edges.'],
        remaining_issues=['Scattered mountain symbols and repeated source forms remain visible.',
            'Wuhan has large blank frame margins and a tiny map at regional zoom.',
            'Broad alluvial ground and angular source river bends remain visible.',
            'Shore geometry remains visibly angular; full unit direction/action cycles remain incomplete.'],
        formal_art_approval=False, ew6_parity_claimed=False, manual_image_compositing=False,
        physical_android_device_tested=False, panning_spikes_resolved=False)
    write(REPORTS / 'visual_review.json', review)
    media = read(P / 'docs/media/manifest.json')
    for name in ['wuhan', 'beijing', 'coast']:
        source = P / 'reports/screenshots/map_composition_native/v0232/verified_export_01' / name
        target = P / 'docs/media' / ('map-relief-' + name + '-v0232')
        for ext in ['.png', '.json']:
            dest = target.with_suffix(ext); assert not dest.exists(); shutil.copyfile(source.with_suffix(ext), dest)
        media['screenshots'].append(dict(file=target.with_suffix('.png').relative_to(P).as_posix(),
            version='0.2.32', native_source=source.with_suffix('.png').relative_to(P).as_posix(),
            sha256=sha(target.with_suffix('.png')), metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            byte_identical_to_native_capture=True, physical_android_device_tested=False))
    media['version'] = '0.2.32'; write(P / 'docs/media/manifest.json', media)

    zh = ('0.2.32改善绿色山体与灰岩地面的衔接，复用已有整幅原图，并批处理地形阴影和等高线。'
        '下图为正式Windows程序；另见[北京](docs/media/map-relief-beijing-v0232.png)、'
        '[山海关](docs/media/map-relief-coast-v0232.png)与[武汉](docs/media/map-relief-wuhan-v0232.png)。'
        '未新增栅格素材；生态区只约束代表性底色，不作为历史植被调查。\n\n'
        '![0.2.32正式Windows程序：山地底材与山脚衔接](docs/media/map-relief-mountains-v0232.png)\n\n'
        '507项组件、48项正式EXE地表GPU及58项地图布局检查通过，合计613项；10张最终程序画面已完整查看。'
        '开发拖动测试仍有约100毫秒尖峰，整体画质与物理X30验收尚未达标。旧GIF保留0.2.29身份。\n\n')
    en = ('Version 0.2.32 improves the transition between green mountain sprites and gray mineral ground, using existing complete originals, '
        'and batches terrain washes and contour lines. This is the shipping Windows application; see also '
        '[Beijing](docs/media/map-relief-beijing-v0232.png), [Shanhaiguan](docs/media/map-relief-coast-v0232.png) and '
        '[Wuhan](docs/media/map-relief-wuhan-v0232.png). No raster originals were added. Ecoregions constrain representative ground color, not historical vegetation claims.\n\n'
        '![Version 0.2.32 shipping Windows: mountain ground and sprite-foot transitions](docs/media/map-relief-mountains-v0232.png)\n\n'
        '507 component checks, 48 shipping-EXE ground GPU checks and 58 map-layout checks pass: 613 targeted checks. '
        'Ten final-application images were viewed in full. Development panning still shows roughly 100ms spikes; overall art parity and physical X30 acceptance remain unfinished. '
        'Retained GIFs keep their 0.2.29 identity.\n\n')
    for relative, marker, insert in [('README.md', '0.2.31使用两张新的独立原图', zh), ('README.en.md', 'Version 0.2.31 uses two new independent originals', en)]:
        path=P/relative;raw=path.read_bytes();eol='\r\n' if b'\r\n' in raw else '\n';text=raw.decode('utf-8')
        assert text.count(marker)==1 and 'map-relief-mountains-v0232.png' not in text
        path.write_bytes(text.replace(marker,insert.replace('\n',eol)+marker,1).encode('utf-8'))
    replace_line('README.md','历史章节保留版本语境；当前状态以本README',
        '历史章节保留版本语境；当前状态以本README、[0.2.32山地与批处理范围](docs/50_山地底材衔接与地形绘制批处理.md)、完成度和对应报告为准。[师旅级名册章节](docs/46_师旅级将领池与战役名册.md)说明完整登记、来源、筛选、任命与未覆盖范围。')
    replace_line('README.en.md','Older chapters preserve their version context.',
        'Older chapters preserve their version context. Use these READMEs, the [0.2.32 relief and batching scope](docs/50_山地底材衔接与地形绘制批处理.md), completion assessment and corresponding reports for current status. The [commander chapter](docs/46_师旅级将领池与战役名册.md) documents the registered pool, sources, filters, appointments and remaining coverage.')
    replace_line('docs/00_程序文档索引.md','当前实施入口：',
        '当前实施入口：[0.2.32山地底材衔接与地形绘制批处理](50_山地底材衔接与地形绘制批处理.md)。双端/code37已构建，613项专项通过，10张最终程序完整画面已查看；没有新增或加工PNG。拖动尖峰、整体美术和物理X30验收仍未完成。此前版本范围与回执保留原身份。')
    replace_line('docs/23_当前完成度评估.md','# 当前完成度评估',
        '# 当前完成度评估 · 0.2.32\n\n'
        '当前[0.2.32山地底材与地形绘制批处理](50_山地底材衔接与地形绘制批处理.md)依据既有地形及生态区参考改善山地下层底色，扩大山脚柔和区，并缓存地形淡色、阴影与等高线。20类地表、80张细节和2,509张原图沿用，158份受保护规则与数据保持原字节。\n\n'
        'Windows与签名Android/code37均已构建。9组507项组件、正式EXE的48项GPU与七地图58项检查通过，合计613项；10张最终程序整幅画面已完整查看。APK签名、双架构、141份数据/说明、2,509张贴图及3首既有配乐载荷核对通过。无连接设备，仍无物理X30验收。\n\n'
        '山体与灰岩底的割裂减轻，但重复图符、武汉边缘留白、大片冲积土和折线河道仍然明显。开发拖动测量的95分位仍约102—107毫秒，不能宣布流畅达标；整体欧陆战争6品质、全兵种动作与起局史实仍未完成。后续配乐使用远程YuE2纯器乐，本轮未生成新音乐。\n\n'
        '## 0.2.31归档范围')
    path=P/'docs/MEDIA.md';raw=path.read_bytes();eol=b'\r\n' if b'\r\n' in raw else b'\n'
    marker='0.2.31新增四张'.encode('utf-8')
    note=('0.2.32新增五张正式Windows整幅画面：[菜单](media/menu-v0232.png)、[山地](media/map-relief-mountains-v0232.png)、'
        '[武汉](media/map-relief-wuhan-v0232.png)、[北京](media/map-relief-beijing-v0232.png)和[山海关](media/map-relief-coast-v0232.png)。'
        '七地图及菜单/冒烟/山地共10张最终画面已完整查看，见[实际查看记录](../reports/relief_grounding_v0232/visual_review.json)。原字节复制，旧GIF身份不变。\n\n'
        'Version 0.2.32 adds five whole shipping-Windows selections: menu, mountains, Wuhan, Beijing and Shanhaiguan. '
        'Ten final-application images were viewed in full. Copies retain original bytes; older GIF identities are unchanged.\n\n')
    assert raw.count(marker)==1;path.write_bytes(raw.replace(marker,note.encode('utf-8').replace(b'\n',eol)+marker,1))
    with (P/'docs/50_山地底材衔接与地形绘制批处理.md').open('a',encoding='utf-8',newline='\n') as stream:
        stream.write('\n## 最终双端与正式程序复验\n\n'
            'Windows与签名Android/code37绑定同一冻结源码身份。正式EXE的[七地图布局检查](../reports/screenshots/map_composition_native/v0232/verified_export_01/validation.json)58项通过，'
            '[GPU与界面专项](../reports/relief_grounding_v0232/shipping_01/validation.json)包含48项GPU检查、真实界面冒烟、菜单及额外山地实机画面。'
            '七地图和三张专项画面共10张已实际完整查看，见[逐文件记录](../reports/relief_grounding_v0232/visual_review.json)。507项组件加48项GPU和58项布局合计613项，未重跑旧版30组全量套件。\n\n'
            'APK已核对v2/v3签名、ARM64/ARMv7、无申请权限、141份数据/说明、2,509张贴图及3首既有配乐载荷。ADB无连接设备，物理X30验收保持未完成。'
            '本轮五张README精选图按原字节复制，未剪裁、拼接或叠字；旧GIF保留版本身份。素材数量和通过检查不代表整体美术批准。'
            '交付为专项可玩测试包，完整源码通过Git仓库提供，旧版归档不改写。\n')
    print('DOCS_AND_TEN_ACTUAL_WHOLE_IMAGE_REVIEWS_RECORDED',flush=True)


if __name__ == '__main__':
    main()
