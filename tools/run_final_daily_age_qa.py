"""Run final native release checks sequentially so GPU/layout evidence stays isolated."""
import subprocess,sys
from build_release import P

def main():
 for name in ['verify_exports','capture_general_portraits','capture_terrain_update','capture_control_land','verify_map_symbols','verify_music_playback']:
  print('FINAL_NATIVE_BEGIN '+name,flush=True)
  result=subprocess.run([sys.executable,'-X','utf8',str(P/'tools'/(name+'.py'))],cwd=P)
  if result.returncode:raise SystemExit(result.returncode)
  print('FINAL_NATIVE_PASS '+name,flush=True)

if __name__=='__main__':main()
