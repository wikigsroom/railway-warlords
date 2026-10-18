"""Run final exported UI, calendar-portrait, map and audio evidence sequentially."""
import subprocess
import sys
from build_release import P


def main():
    for name in ['capture_dossier_ui', 'verify_exports', 'capture_general_portraits', 'capture_terrain_update',
                 'capture_control_land', 'verify_map_symbols', 'verify_music_playback']:
        print('FINAL_NATIVE_BEGIN ' + name, flush=True)
        result = subprocess.run([sys.executable, '-X', 'utf8', str(P / 'tools' / (name + '.py'))], cwd=P)
        if result.returncode:
            raise SystemExit(result.returncode)
        print('FINAL_NATIVE_PASS ' + name, flush=True)


if __name__ == '__main__':
    main()
