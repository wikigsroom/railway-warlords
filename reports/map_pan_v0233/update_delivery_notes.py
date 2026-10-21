"""Refresh current acceptance entries after the actual final captures are reviewed."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

P = Path(__file__).resolve().parents[2]
R = P / 'reports/map_pan_v0233'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def replace_once(path, old, new):
    data = path.read_bytes()
    assert data.count(old.encode('utf-8')) == 1, (path, old)
    eol = b'\r\n' if b'\r\n' in data else b'\n'
    path.write_bytes(data.replace(old.encode('utf-8'), new.encode('utf-8').replace(b'\n', eol), 1))


def main():
    view = read(R / 'visual_review.json')
    assert len(view['actually_viewed_complete_images']) == 10
    components = read(R / 'final_components_02/runs.json')
    checks = sum(o['checks'] for row in components['runs'] for o in row['outputs'])
    assert checks == 625 and components['passed']
    note = '当前0.2.33为地图拖动优化测试版。16组625项组件、正式EXE的48项地表GPU和58项地图布局检查通过，共731项专项；10张最终整幅画面已实际完整查看。三个固定镜头的旧新绘制逐像素一致，四轮交替开发复测另行记录。完整30组回归、长期AI及物理Motorola X30本轮未重跑，不将旧结果标成本版重新验收。范围、剩余问题和原始证据见[51章](51_地图拖动预取与源线段缓存.md)。'
    replace_once(P / 'docs/05_测试与验收.md', '# 测试与验收 · 0.2.29', '# 测试与验收 · 0.2.33\n\n' + note + '\n\n## 0.2.29历史验收记录')
    replace_once(P / 'docs/06_双端构建与发布.md', '当前源码0.2.29为地图模型比例与统一标注测试版，', '当前源码0.2.33已导出同一源码身份的Windows与签名Android/code38。归档完成后清单写入`reports/map_pan_preview_v0233.json`，验收范围见[51章](51_地图拖动预取与源线段缓存.md)。本轮保留旧发布目录，物理X30尚未验收。\n\n0.2.29历史交付：地图模型比例与统一标注测试版，')
    replace_once(P / 'docs/06_双端构建与发布.md', 'versionCode34、versionName0.2.29', 'versionCode38、versionName0.2.33')
    root_index = P.parents[1] / 'design/铁道烽烟/00_总纲与文档索引.md'
    replace_once(root_index, '当前程序修订入口：[0.2.21 源陆地补纹与林底选材]', '当前程序修订入口：[0.2.33 地图拖动优化](../../game/railway_warlords/docs/51_地图拖动预取与源线段缓存.md) / [0.2.21 源陆地补纹与林底选材]')
    receipt = read(R / 'audit_receipt.json')
    for row in receipt['reports']:
        path = P / row['report']
        row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        row['modified_at_utc'] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    (R / 'audit_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('CURRENT_ACCEPTANCE_AND_BUILD_NOTES_UPDATED', flush=True)


if __name__ == '__main__':
    main()
