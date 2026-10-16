"""Capture whole Sub2 originals in the native internal Godot gallery."""
import argparse
import json
import subprocess
from build_release import P, ENGINE
from map_bank_inventory import production_rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--all-pages',action='store_true')
    parser.add_argument('--category',default='scenery')
    parser.add_argument('--family',default='')
    args=parser.parse_args()
    all_rows,_=production_rows()
    rows=[r for r in all_rows if (not args.category or r['category']==args.category) and (not args.family or r['family']==args.family)]
    if not rows:
        raise SystemExit('No generated originals match this gallery category/family.')
    pages=(len(rows)+17)//18 if args.all_pages else 1
    scope=args.family or args.category or 'all'
    for page in range(pages):
        target=P/'reports/screenshots/map_bank'/f'{scope}_{page:02d}.png'
        target.parent.mkdir(parents=True,exist_ok=True)
        cmd=[str(ENGINE),'--path',str(P),'--rendering-method','gl_compatibility','--resolution','1920x1200',
             '--position','-4000,-3000','--script','tests/map_bank_gallery.gd','--',
             '--page',str(page),'--capture-path',str(target)]
        if args.category:cmd+=['--category',args.category]
        if args.family:cmd+=['--family',args.family]
        with (P/'reports'/f'map_bank_gallery_{scope}_{page:02d}.log').open('w',encoding='utf-8') as stream:
            result=subprocess.run(cmd,cwd=P,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
        if result.returncode:raise SystemExit('Native map bank gallery failed: '+scope)
        print(str(target),flush=True)


if __name__=='__main__':main()
