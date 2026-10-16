"""Generate independent cardinal unit views through the required Sub2 route.

Each direction is a separate source request.  This script never rotates,
stitches, crops, paints over, or packs the generated rasters.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

from PIL import Image

from generate_assets import EQUIPMENT

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
SKILL = Path("C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py")
RAW = ROOT / "output/imagegen/warlord/ew6_v025/directional"
MANIFEST = PROJECT / "assets/manifest.json"

STYLE = """Original premium historical strategy game miniature for 1920-1924 Republican China.
Elevated 2.5D hand-painted map art in the visual language of a high-quality European
historical conquest game, entirely original and without logos or copied assets. Rich
olive and meadow green clothing accents, slate-gray steel, warm brass light, clean
readable silhouettes, coherent upper-left light and short lower-right shadow. Near
overhead 60-degree camera, north-up map anchor, convincing volume, restrained dark
contours. Not photorealistic, glossy 3D, anime, fantasy, modern military or WWII.
"""

DIRECTIONS = {
    "n": "due north toward the top edge of the map",
    "e": "due east toward the right edge of the map",
    "s": "due south toward the bottom edge of the map",
    "w": "due west toward the left edge of the map",
}

ELITE_BASE = {
    "elite_assault": "assault",
    "elite_cavalry": "cavalry",
    "elite_artillery": "field_artillery",
}


def jobs(only: set[str] | None = None):
    result = []
    for family in list(EQUIPMENT) + list(ELITE_BASE):
        for direction, phrase in DIRECTIONS.items():
            asset_id = f"unit_{family}_{direction}"
            if only and asset_id not in only:
                continue
            base = ELITE_BASE.get(family, family)
            elite = family.startswith("elite_")
            subject = EQUIPMENT[base]
            prompt = STYLE + f"""
ONE complete independent transparent-background map formation, not a sheet and not a
contact board. Subject: {subject}. The whole formation is oriented {phrase}; bodies,
heads, horses, gun barrel, wheels and weapon stocks all agree with that heading. Keep
the same elevated map camera while turning the formation: feet stay upright on the
ground plane, no sideways leaning, no billboard rotation, no mixed directions. Use at
most three readable figures (or the compact crew appropriate to the equipment), with
clear spacing and a stable low-wide silhouette. {'A disciplined elite formation with slightly cleaner spacing. ' if elite else ''}
Early Republican Chinese khaki or gray-blue high-collar tunics, plain unmarked peaked
caps, leather belts and puttees; period bolt-action rifles, wooden wheels and steel
barrels. No flags, national symbols, rank badges, text, watermark, modern camouflage,
assault rifles, WWII helmets, tanks, aircraft, terrain slab, shadow disc, pedestal or
background scene. Transparent alpha outside the complete subject. Center the subject in
the middle 78 percent of a square canvas; all equipment stays inside generous margins;
readable at 76 display pixels. This is one single direction asset for runtime selection.
"""
            result.append((asset_id, family, direction, prompt))
    return result


def generate(job):
    asset_id, family, direction, prompt = job
    folder = RAW / asset_id / "r001"
    folder.mkdir(parents=True, exist_ok=True)
    prompt_path = folder / "prompt.txt"
    source = folder / "source.png"
    if prompt_path.exists() and prompt_path.read_text(encoding="utf-8") != prompt:
        raise RuntimeError(f"immutable prompt mismatch: {asset_id}")
    if not prompt_path.exists():
        prompt_path.write_text(prompt, encoding="utf-8")
    if not source.exists():
        log_path = folder / "generation.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [sys.executable, str(SKILL), "generate", "--model", "gpt-image-2.5",
                 "--quality", "high", "--size", "1024x1024", "--background",
                 "transparent", "--prompt-file", str(prompt_path), "--out", str(source)],
                stdout=log, stderr=subprocess.STDOUT, timeout=900,
            )
        if result.returncode or not source.exists():
            raise RuntimeError(f"Sub2 generation failed: {asset_id}; see {log_path}")
    with Image.open(source) as image:
        dimensions = list(image.size)
        alpha_min = image.getchannel("A").getextrema()[0] if image.mode == "RGBA" else 255
    if alpha_min == 255:
        raise RuntimeError(f"transparent exterior missing: {asset_id}")
    destination = PROJECT / "assets/unit" / f"{asset_id}.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise RuntimeError(f"runtime destination already differs: {destination}")
    shutil.copyfile(source, destination)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "id": asset_id,
        "category": "unit",
        "subject": family,
        "view": direction,
        "direction_basis": "independent Sub2 source view; no runtime raster rotation",
        "state": "generated_pending_visual_review",
        "game_ready": False,
        "source_kind": "sub2_image_gen",
        "model": "gpt-image-2.5",
        "quality": "high",
        "style_version": "warlord_ew6_v025_directional_r001",
        "era": "1920-1924",
        "source_file": source.relative_to(ROOT).as_posix(),
        "source_sha256": digest(source),
        "prompt_file": prompt_path.relative_to(ROOT).as_posix(),
        "prompt_sha256": digest(prompt_path),
        "actual_dimensions": dimensions,
        "planned_source_request": [1024, 1024],
        "engine_path": "res://" + destination.relative_to(PROJECT).as_posix(),
        "planned_engine_path": "res://" + destination.relative_to(PROJECT).as_posix(),
        "runtime_import_max_dimension": 512,
        "background": "transparent",
        "alpha_min": alpha_min,
        "revision": "directional_r001",
        "image_modified": False,
        "manual_compositing": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="comma-separated asset ids for a pilot")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    only = {value.strip() for value in args.only.split(",") if value.strip()} or None
    selected = jobs(only)
    if not selected:
        raise SystemExit("no direction assets selected")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {row["id"]: row for row in manifest.get("assets", [])}
    completed, failures = [], []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {executor.submit(generate, job): job[0] for job in selected}
        for future in as_completed(future_map):
            asset_id = future_map[future]
            try:
                record = future.result()
                records[asset_id] = record
                completed.append(asset_id)
                print(asset_id + ": original Sub2 PNG installed", flush=True)
            except Exception as error:
                failures.append({"id": asset_id, "reason": str(error)})
                print(json.dumps(failures[-1], ensure_ascii=False), flush=True)
    manifest["assets"] = sorted(records.values(), key=lambda row: row["id"])
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "route": "sub2-image-gen/gpt-image-2.5",
        "manual_compositing": False,
        "source_images_modified": False,
        "requested": len(selected),
        "completed": completed,
        "failures": failures,
        "passed": not failures,
    }
    (PROJECT / "reports/unit_direction_generation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
