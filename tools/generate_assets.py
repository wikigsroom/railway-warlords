"""Generate independent, immutable PNGs using the user's Sub2 skill; never compose images."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
SKILL = Path("C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py")
BASELINE = ROOT / "design/铁道烽烟/assets/asset_catalog.json"
RAW = ROOT / "output/imagegen/warlord/raw"
MANIFEST = PROJECT / "assets/manifest.json"
STYLE = ("1920s Chinese military atlas illustration, restrained hand-painted woodcut contours, "
         "muted military green, charcoal, warm parchment, dusty brass and steel blue. "
         "Near overhead light isometric view, consistent upper-left light and short lower-right shadow. "
         "Clean confident silhouettes, not photorealistic, not glossy 3D, not anime, no fantasy. "
         "All caps and uniforms are PLAIN UNMARKED: absolutely no blue-white sun, KMT sun badge, "
         "red star, army emblem, national flag or modern rank insignia.")
EQUIPMENT = {
    "militia": "three local militia wearing simple early Republican tunics carrying bolt-action rifles",
    "rifle": "three compact Republican Chinese infantrymen in khaki high-collar tunics and peaked caps, bolt-action rifles",
    "assault": "three elite assault infantrymen, early 1920s khaki uniforms, grenades and bolt-action rifles",
    "machine_gun": "one period tripod-mounted Maxim machine gun with a compact two-man crew and ammunition box",
    "cavalry": "three mounted early Republican Chinese cavalrymen with dark brown horses, rifles and sabres",
    "engineer": "two early Republican military engineers with shovels, timber and a small tool chest",
    "field_artillery": "one early twentieth-century wheeled field gun with a compact three-man khaki crew",
    "heavy_artillery": "one heavy early twentieth-century siege howitzer, wooden-spoked wheels and two khaki crew",
    "armored_car": "one rare riveted early 1920s four-wheel armored car with a small turret, no tracked chassis",
    "armored_train": "one compact armored steam locomotive and one short riveted gun carriage, all wheels visible, no rails beneath",
    "river_gunboat": "one small early twentieth-century Chinese river gunboat with one funnel and period deck gun",
    "transport_ship": "one modest early twentieth-century coastal transport steamer, one funnel, no heavy guns",
    "coastal_gunship": "one compact early twentieth-century coastal gunboat with period deck guns and one funnel",
}


def prompt_for(asset):
    category, subject = asset["category"], asset["subject"]
    common = f"{STYLE} Create ONE complete independent game asset directly. No collage, contact sheet, labels, text, grid, UI or watermark. "
    if category == "unit":
        key = asset["id"][5:].rsplit("_", 1)[0]
        elite = key.startswith("elite_")
        key = {"elite_assault": "assault", "elite_cavalry": "cavalry",
               "elite_artillery": "field_artillery"}.get(key, key)
        facing = "southeast toward bottom-right" if asset["view"] == "se" else "southwest toward bottom-left"
        return common + f"Subject: {EQUIPMENT[key]}. Facing {facing}. " + (
            "A disciplined compact elite formation; same period equipment, slightly more orderly silhouette. " if elite else ""
        ) + "Transparent alpha background, no ground patch, no plinth, no checkerboard. Center entire formation within middle 72% of canvas, base anchor near 80% height, all weapons and silhouettes inside margins. Clear at 64 display pixels. No modern camouflage, assault rifles, tanks or jets."
    if category == "portrait":
        return common + f"ONE chest-up stylized historical game portrait representing {subject}, early 1920s China. Sober mature expression, historically plausible early Republican high-collar khaki tunic and peaked military cap. Frontal three-quarter view. Warm paper facial shading and charcoal ink, dignified distinct individual face. Transparent exterior, head and both shoulders entirely inside margin. No later-era uniform, invented medals, ornate fantasy armor or nameplate."
    if category == "building":
        condition = "intact and operational" if asset["view"] in ["intact", "normal"] or asset["id"].endswith("_intact") else "lightly battle-damaged, same footprint, roof partly damaged"
        return common + f"ONE period Chinese {subject} building, {condition}, circa 1920–1924. Compact light-isometric city icon, brick and timber construction, tiled roof, no surrounding terrain. Transparent alpha background, entire base inside central 78%, consistent ground anchor, readable at 90 pixels. No modern towers, bridges or highways."
    if category == "tile":
        return common + f"ONE quiet seamless top-down terrain material: {subject}, variation {asset['view']}. Warm low-contrast military-map paper texture. Readable at 96 pixels, sparse restrained strokes, continuous edges, uniform flat overhead camera. No cities, units, coastlines, rivers defining geography, roads, rails or hex borders. Texture only, no scene collage."
    if category == "icon":
        return common + f"ONE simple military-atlas pictogram symbol for {subject}. Strong clear silhouette using muted brass and charcoal, readable at 32 pixels, centered within middle 70%, transparent alpha background. Period military objects only, no words or number."
    if category == "fx":
        return common + f"ONE independent restrained 2D strategy-map effect sprite: {subject}. Short compact painted effect with transparent alpha exterior, readable small silhouette, period battlefield character, generous margins. No underlying terrain, units or text. Not a spritesheet."
    if category == "background":
        return common + f"ONE coherent landscape backdrop for a {subject} menu. Northern China in the 1920s, a quiet authentic military map table, distant period railway locomotive and field-gun silhouette at the far right. Warm paper, coal-black railway lines, muted mountains and restrained steel-blue water. Left two thirds low detail and dark charcoal for readable interface overlays. No existing game UI, no text, no fabricated labelled geography."
    if category == "ui":
        return common + f"ONE flat quiet UI surface material: {subject}, rectangular surface with restrained paper/charcoal steel grain and a fine dusty-brass edge. Very low detail center for readable text. No buttons baked inside, no words, no elaborate rivets or filigree. Flat front view."
    raise ValueError(category)


def generate_one(asset, revision="r001"):
    asset_id = asset["id"]
    folder = RAW / asset_id / revision
    folder.mkdir(parents=True, exist_ok=True)
    prompt_path = folder / "prompt.txt"
    out = folder / "source.png"
    prompt = prompt_for(asset)
    if not prompt_path.exists():
        prompt_path.write_text(prompt, encoding="utf-8")
    if not out.exists():
        command = [sys.executable, str(SKILL), "generate", "--model", "gpt-image-2.5",
                   "--quality", "high", "--size", "1024x1024", "--prompt-file", str(prompt_path),
                   "--out", str(out), "--background",
                   "transparent" if asset["background"] == "transparent" else "opaque"]
        result = subprocess.run(command, capture_output=True, timeout=360)
        if result.returncode != 0 or not out.exists():
            # Gateway details can be inspected interactively; do not put credentials or raw responses in the project.
            return {"id": asset_id, "state": "generation_failed", "exit_code": result.returncode}
    with Image.open(out) as im:
        dimensions = list(im.size)
        alpha_min = im.getchannel("A").getextrema()[0] if im.mode == "RGBA" else 255
    if asset["background"] == "transparent" and alpha_min == 255:
        return {"id": asset_id, "state": "review_rejected", "reason": "transparent_alpha_missing",
                "actual_dimensions": dimensions}
    destination = PROJECT / asset["planned_engine_path"].removeprefix("res://")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out, destination)
    record = dict(asset)
    record.update({"state": "generated_pending_visual_review", "game_ready": False,
                   "source_file": out.relative_to(ROOT).as_posix(),
                   "source_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                   "prompt_file": prompt_path.relative_to(ROOT).as_posix(),
                   "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
                   "actual_dimensions": dimensions, "engine_path": asset["planned_engine_path"],
                   "alpha_min": alpha_min, "revision": revision, "image_modified": False})
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--category", default="")
    args = parser.parse_args()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    records = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {
        "design_version": "1.0", "manual_compositing": False, "assets": []}
    current = {a["id"]: a for a in records["assets"]}
    candidates = [a for a in baseline["assets"] if a["category"] not in ["reference", "sfx", "music", "font"]]
    priority = ["unit_rifle_se", "unit_machine_gun_se", "unit_field_artillery_se",
                "unit_engineer_se", "tile_plain_a", "background_campaign", "portrait_wu_peifu",
                "unit_cavalry_se"]
    candidates.sort(key=lambda a: priority.index(a["id"]) if a["id"] in priority else 100)
    candidates = [a for a in candidates if a["id"] not in current or
                  current[a["id"]]["state"] in ["generation_failed", "review_rejected"]]
    if args.category:
        candidates = [a for a in candidates if a["category"] == args.category]
    if args.limit:
        candidates = candidates[:args.limit]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {}
        for a in candidates:
            existing = sorted((RAW / a["id"]).glob("r[0-9][0-9][0-9]"))
            revision = "r%03d" % (len(existing) + 1) if a["id"] in current else "r001"
            future_map[executor.submit(generate_one, a, revision)] = a["id"]
        for future in as_completed(future_map):
            try:
                record = future.result()
            except Exception as exc:
                record = {"id": future_map[future], "state": "generation_failed",
                          "reason": type(exc).__name__}
            current[record["id"]] = record
            records["assets"] = sorted(current.values(), key=lambda a: a["id"])
            temp = MANIFEST.with_suffix(".tmp")
            temp.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(MANIFEST)
            print(json.dumps({"asset": record["id"], "state": record["state"]}, ensure_ascii=True), flush=True)
    return 1 if any(a["state"] in ["generation_failed", "review_rejected"] for a in current.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
