"""Record raw Godot scenes and directly encode MovieWriter output, with no montage."""
import argparse
import subprocess
from build_release import P, ENGINE, current_version


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['all', 'layers', 'movie', 'support', 'calendar'], default='all')
    selected = parser.parse_args().only
    tag = 'v' + current_version().replace('.', '')
    jobs = [
        ('layers', 'unit_layer_native', ['--resolution', '1920x1080', '--', '--qa-session', '--unit-layer-test']),
        ('movie', 'visual_playtest_final_' + tag,
         ['--resolution', '1440x810', '--write-movie', str(P / 'reports/atlas_v2_native_final.avi'),
          '--fixed-fps', '30', '--', '--qa-session', '--visual-playtest']),
        ('support', 'support_playtest_' + tag, ['--resolution', '1440x810', '--', '--qa-session', '--support-playtest']),
        ('calendar', 'calendar_capture_' + tag,
         ['--resolution', '1920x1080', '--script', 'tests/historical_map_capture.gd']),
    ]
    for kind, name, args in jobs:
        if selected not in ('all', kind):
            continue
        log = P / 'reports' / (name + '.log')
        with (P / 'reports' / (name + '_stdout.log')).open('w', encoding='utf-8') as stream:
            result = subprocess.run([str(ENGINE), '--path', str(P), '--log-file', str(log), *args],
                                    cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        if result.returncode or any(marker in diagnostic for marker in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')):
            raise SystemExit('Native scene failed: ' + name)
        if kind == 'movie':
            with (P / 'reports' / ('movie_encode_' + tag + '.log')).open('w', encoding='utf-8') as stream:
                encoded = subprocess.run(['ffmpeg', '-y', '-i', str(P / 'reports/atlas_v2_native_final.avi'),
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
                    '-movflags', '+faststart', str(P / 'reports/atlas_v2_native_final.mp4')],
                    stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            if encoded.returncode:
                raise SystemExit('Native movie encoding failed.')
        print(name + ': passed', flush=True)


if __name__ == '__main__':
    main()
