"""Package current QA evidence without rebuilding the release binaries."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile

from build_release import P, current_version


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def collect(root: Path, files: list[Path]) -> list[Path]:
    for path in root.rglob('*'):
        if path.is_file() and path not in files:
            files.append(path)
    return files


def main() -> None:
    endurance = json.loads((P / 'reports/endurance_evidence.json').read_text(encoding='utf-8'))
    accessibility = json.loads((P / 'reports/accessibility_evidence.json').read_text(encoding='utf-8'))
    if not endurance.get('passed'):
        raise SystemExit('A passing endurance evidence report is required.')
    package_name = f'railway-warlords-{current_version()}-supplement-2026-10-12.zip'
    output = P.parent.parent / 'output/verification' / package_name
    output.parent.mkdir(parents=True, exist_ok=True)
    files: list[Path] = [
        P / 'reports/endurance_evidence.json',
        P / 'reports/accessibility_evidence.json',
        P / 'tests/endurance_soak_test.gd',
        P / 'tests/accessibility_native_test.gd',
        P / 'tests/immutable_state_fingerprint.gd',
        P / 'tools/run_endurance_validation.py',
        P / 'tools/run_accessibility_validation.py',
        P / 'tools/developer_tools.py',
        P / 'tools/package_verification_supplement.py',
        P / 'tools/preflight_delivery.py',
        P / 'tools/review_delivery.py',
        P / 'tools/verify_exports.py',
        P / 'tools/verify_standalone.py',
        P / 'docs/17_当前补充验收.md',
        P / 'docs/03_设计落实与差异.md',
        P / 'docs/05_测试与验收.md',
        P / 'docs/06_双端构建与发布.md',
        P / 'docs/08_养成与事务回归.md',
        P / 'docs/10_地图绘制与可读性.md',
        P / 'docs/11_系列对标与实机修复.md',
        P / 'docs/14_地图比例与五倍格网.md',
        P / 'docs/15_历史聚落与势力地图.md',
        P / 'docs/18_开发工具与发行检查.md',
        P / 'reports/developer_scenario_conq_1924.json',
        P / 'reports/developer_hex_first_cell.json',
        P / 'reports/developer_command_log_attack.json',
        P / 'reports/developer_balance_matrix.json',
        P / 'reports/developer_asset_validation.json',
        P / 'reports/developer_historical_release_check.json',
        P / 'reports/developer_tools_smoke.json',
        P / 'reports/delivery_preflight.json',
        P / 'reports/apk_content_validation.json',
        P / 'reports/android_devices.log',
        P / 'reports/export_results.json',
    ]
    files = [path for path in files if path.is_file()]
    endurance_dir = P / endurance['run_directory']
    accessibility_dir = P / accessibility['run_directory']
    collect(endurance_dir, files)
    collect(accessibility_dir, files)
    records = []
    for path in sorted(files):
        records.append({'file': path.relative_to(P).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size})
    manifest = {
        'package': package_name,
        'version': current_version(),
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'files': records,
        'endurance': {'passed': endurance['passed'], 'completed_rounds': endurance['completed_rounds'], 'commands': endurance['commands'], 'checkpoints': endurance['checkpoint_count'], 'replayed_commands': endurance['replayed_commands'], 'source_run': endurance['run_directory']},
        'accessibility': {'passed': accessibility['passed'], 'profiles': accessibility['profiles'], 'source_run': accessibility['run_directory']},
        'binaries_included': False,
        'scope': 'Supplemental QA evidence only. Existing Windows/Android/source release archives are not rebuilt or modified. The 4K profile remains a truthful hardware-limited failure on the 2560x1440 host; physical Android and historical/manual acceptance remain pending.'
    }
    readme = f'''# 《铁道烽烟：军阀时代》{current_version()} 补充审计包\n\n本包只封存 2026-10-12 的当前 QA 运行、原始 Godot 截图、日志、测试源、运行器和对应文档。它不含 Windows/Android 发布二进制；双端安装包和 Godot 工程另见 {current_version()} 发布目录。\n\n- 100 回合原生 AI 长局：{endurance['commands']} 条命令、20 个随机阶段存档、{endurance['replayed_commands']} 条回放命令，发布剧本仍为 80 回合。\n- 1280×720 标准字号和 150% 大字通过；当前 2560×1440 显示器无法提供真实 3840×2160 窗口，4K 失败记录完整保留。\n- Android 物理设备、Motorola X30、历史军事起局、全素材正式审核和人工策略平衡仍未宣称完成。\n\n目录内 `manifest.json` 对每个文件列出 SHA256 和字节数。\n'''
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr('README.md', readme)
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for path in sorted(files):
            archive.write(path, 'project/' + path.relative_to(P).as_posix())
    print(json.dumps({'package': output.relative_to(P.parent.parent).as_posix(), 'sha256': sha(output), 'bytes': output.stat().st_size, 'files': len(records), 'endurance_passed': endurance['passed'], 'accessibility_passed': accessibility['passed']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
