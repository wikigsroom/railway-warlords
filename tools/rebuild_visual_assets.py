"""Produce independent, immutable Sub2 assets for the approved atlas direction.

No image composition, retouching, cropping, mirroring or resizing occurs here.
Engine imports handle resolution; every installed PNG is identical to its source.
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
RAW = ROOT / "output/imagegen/warlord/atlas_v2"
MANIFEST = PROJECT / "assets/manifest.json"
SKILL = Path("C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py")
STYLE = """Premium 1920s Chinese military atlas illustration, NOT a close-up character illustration.
Warm newsprint #D8C8A5, coal ink #252B2B, muted olive #687659, dusty brass and steel blue #5A7985.
Fine confident woodcut contours and hand-painted washes, restrained contrast, elegant readable shapes.
Near-overhead elevated camera looking down at 60 degrees, slight isometric objects, light from upper left.
No glossy 3D, photorealism, anime, fantasy or neon. One coherent independent runtime asset, no sheet,
no montage, no text, labels, UI, hex outlines or watermark. Never bake geographic boundaries into materials.
"""


def plan():
    jobs = []
    for name in list(EQUIPMENT) + ["elite_assault", "elite_cavalry", "elite_artillery"]:
        base = {"elite_assault": "assault", "elite_cavalry": "cavalry", "elite_artillery": "field_artillery"}.get(name, name)
        for facing in ["se", "sw"]:
            direction = "bottom right (southeast)" if facing == "se" else "bottom left (southwest)"
            prompt = STYLE + f"""
Subject: {EQUIPMENT[base]}. The ENTIRE compact formation faces {direction}.
This is a very small tactical-map figurine formation viewed from ABOVE, NOT a portrait.
Human heads tiny, bodies simplified, every figure seen head-to-toe, ground-plane arrangement legible.
Composition: a low compact triangle of troops or a single low vehicle, distinct silhouettes with generous
air between individuals; ground feet at a shared isometric plane. Keep aspect around 1.35 wide to 1 high.
Object occupies 70% of canvas width and 56% of height, centered, full weapons and wheels inside margins.
It must look exquisite at 64 pixels. Painted charcoal silhouette edges, simple tan uniforms, subdued paper
highlights, individual faces NOT detailed. Early Republican high-collar tunics, plain unmarked peaked caps,
bolt-action weapons only, no modern rifle, steel WWII helmet, tank, jet, modern badge or sun/star emblem.
Transparent alpha exterior, no ground disc, no background, no checkerboard, no flags.
"""
            if name.startswith("elite_"):
                prompt += "Elite training is shown by orderly spacing and a slightly cleaner equipment silhouette, never invented insignia.\n"
            jobs.append(("unit", "unit_" + name + "_" + facing, prompt, True))
    for name, subject in [
        ("tile_plain_01", "warm pale parchment land wash #C7B58F, delicate sparse fine grass marks, quiet dry lowland earth, absolutely NO dense mottling, rocks, trees, hills or dark clumps"),
        ("tile_sea_01", "calm desaturated steel-blue water #5A7985, sparse thin ivory wave etching and broad gentle tonal washes, NO foamy ocean photograph, storms or high-frequency noise"),
    ]:
        jobs.append(("tile", name, STYLE + f"One seamless top-down material. {subject}. Continuous edges. Large quiet areas. Full opaque square texture. No coastline, geographic scene, objects, tile frame or grid.", False))
    for index, subject in enumerate([
        "a broad connected low east-west northern Chinese rocky mountain ridge, three craggy peaks and winding foothills",
        "an oblique connected northern Chinese mountain ridge, two tall asymmetric crags and low rolling shoulders",
        "a long irregular fan of northern Chinese rocky mountains, four small weathered crags, broad sloping bases",
        "a steep connected northern Chinese craggy ridge with a narrow central saddle and layered foothills",
    ], 1):
        jobs.append(("scenery", "scenery_atlas_ridge_%02d" % index, STYLE + f"""
One terrain illustration PATCH: {subject}. Overhead atlas relief, fine dark contour hatching on shaded
faces, olive and charcoal washes, warm sandy highlighted slopes. Wide 2:1 shape. Rich ink structure with
broad quiet pale lower foothills. No snow, distant skyline, buildings, forests, river, roads or backdrop.
No separate floating mountain icons: one CONNECTED MASS of terrain. Transparent alpha around a soft
irregular silhouette, gently fading sandy foothills, no square ground patch, no frame. Fill middle 80%.
""", True))
    for index, subject in enumerate(["a broad low rolling stony hill with several joined rounded shoulders", "a gently rising rocky northern Chinese foothill with fine contour lines and a shallow saddle"], 1):
        jobs.append(("scenery", "scenery_atlas_hill_%02d" % index, STYLE + f"One connected relief patch: {subject}. Wide low 2:1 shape. Warm tan washes, olive-gray hatching. Transparent alpha outside feathered irregular sandy base. No forests, buildings, road or geography labels.", True))
    for name, subject in [
        ("scenery_station_town", "a compact early Republican Chinese railway station settlement: low gray-brick station house, timber platform canopy, a few gray-tiled courtyard houses and telegraph poles, no track, no train"),
        ("scenery_walled_city", "a compact northern Chinese gray-brick walled town: crenellated low wall, one gate tower and a handful of gray-tiled courtyard roofs, no huge palace, no fantasy towers"),
    ]:
        jobs.append(("scenery", name, STYLE + f"Subject: {subject}. Miniature map settlement viewed from ABOVE, footprint 1.5:1, coherent low architecture, no scene, road or landscape. Entire building group centered inside 78% width. Transparent alpha outside object, no terrain base or labels.", True))
    jobs.append(("scenery", "scenery_recon_biplane", STYLE + """
ONE isolated small 1920s wood-and-fabric single-engine two-seat BIPLANE flying toward bottom right.
Camera looks DOWN from above at 60 degrees. Two stacked wings, fine bracing wires, fixed landing
wheels, two open cockpits, sand-colored fabric, charcoal engine nose and wooden propeller.
Complete aircraft centered in 76% of image width, full wings and tail inside generous empty margins.
Transparent alpha exterior. ONLY the flying aircraft: NO ground, settlement, buildings, trees, airfield,
landing strip, vignette, terrain base, label, flag, insignia, sheet, separate views or second object.
No jet, WWII monoplane, missiles or modern equipment. A compact readable independent map sprite.
""", True))
    for name, subject in [
        ("icon_order_move", "a simple early twentieth-century infantry marching boot"),
        ("icon_order_attack", "a thin circular sight with four short crosshair arms"),
        ("icon_order_tactics", "an open small field orders notebook"),
        ("icon_order_reinforce", "a compact wooden ammunition supply crate"),
        ("icon_resource_cash", "three small period wooden treasury boxes"),
        ("icon_resource_food", "a simple golden wheat stalk with two leaves"),
        ("icon_resource_arms", "three upright early twentieth-century brass rifle cartridges"),
    ]:
        jobs.append(("icon", name, STYLE + f"ONE elegant flat military-atlas pictogram: {subject}. Ivory and muted brass ink, strong silhouette, three-quarter flat drawing. Center in 72% of square canvas, recognizable at 28 pixels. Transparent alpha background. No lettering, number, decorative frame or other objects.", True))
    return jobs


def generate(job):
    category, name, prompt, transparent = job
    revision = "r002" if name == "scenery_recon_biplane" else "r001"
    folder = RAW / name / revision
    folder.mkdir(parents=True, exist_ok=True)
    prompt_path = folder / "prompt.txt"
    source = folder / "source.png"
    if prompt_path.exists() and prompt_path.read_text(encoding="utf-8") != prompt:
        raise RuntimeError("Immutable prompt already differs: " + name)
    prompt_path.write_text(prompt, encoding="utf-8")
    if not source.exists():
        result = subprocess.run([sys.executable, str(SKILL), "generate", "--model", "gpt-image-2.5", "--quality", "high", "--size", "1024x1024", "--prompt-file", str(prompt_path), "--out", str(source), "--background", "transparent" if transparent else "opaque"], capture_output=True, timeout=480)
        if result.returncode or not source.exists():
            return {"id": name, "state": "generation_failed", "exit_code": result.returncode}
    with Image.open(source) as image:
        dimensions = list(image.size)
        alpha_min = image.getchannel("A").getextrema()[0] if image.mode == "RGBA" else 255
    if transparent and alpha_min == 255:
        return {"id": name, "state": "review_rejected", "reason": "transparent_alpha_missing"}
    destination = PROJECT / "assets" / category / (name + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {"id": name, "category": category, "subject": name, "view": name.rsplit("_", 1)[-1], "state": "generated_pending_visual_review", "game_ready": False, "source_kind": "sub2_image_gen", "model": "gpt-image-2.5", "quality": "high", "style_version": "warlord_atlas_v2", "era": "1920-1924", "source_file": source.relative_to(ROOT).as_posix(), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "prompt_file": prompt_path.relative_to(ROOT).as_posix(), "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(), "actual_dimensions": dimensions, "planned_source_request": [1024, 1024], "engine_path": "res://" + destination.relative_to(PROJECT).as_posix(), "planned_engine_path": "res://" + destination.relative_to(PROJECT).as_posix(), "runtime_import_max_dimension": 512 if category == "unit" else 1024, "background": "transparent" if transparent else "tileable_or_scene_specific", "alpha_min": alpha_min, "revision": "atlas_v2_" + revision, "image_modified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--icons", action="store_true")
    parser.add_argument("--aircraft", action="store_true")
    args = parser.parse_args()
    jobs = plan()
    if args.aircraft:
        jobs = [job for job in jobs if job[1] == "scenery_recon_biplane"]
    if args.icons:
        jobs = [job for job in jobs if job[0] == "icon"]
    if args.pilot:
        names = {"unit_rifle_se", "unit_cavalry_se", "unit_machine_gun_se", "unit_field_artillery_se", "tile_plain_01", "tile_sea_01", "scenery_atlas_ridge_01", "scenery_atlas_ridge_02", "scenery_atlas_hill_01", "scenery_station_town", "scenery_walled_city"}
        jobs = [job for job in jobs if job[1] in names]
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current = {record["id"]: record for record in records["assets"]}
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(generate, job): job[1] for job in jobs}
        for future in as_completed(futures):
            try:
                record = future.result()
            except Exception as error:
                record = {"id": futures[future], "state": "generation_failed", "reason": type(error).__name__}
            if record["state"] in ["generation_failed", "review_rejected"]:
                failed.append(record)
            else:
                current[record["id"]] = record
                records["assets"] = sorted(current.values(), key=lambda item: item["id"])
                temporary = MANIFEST.with_suffix(".tmp")
                temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                temporary.replace(MANIFEST)
            print(json.dumps({"asset": record["id"], "state": record["state"]}), flush=True)
    (PROJECT / "reports/atlas_v2_generation.json").write_text(json.dumps({"requested": len(jobs), "failed": failed, "provider": "sub2_image_gen", "manual_compositing": False}, ensure_ascii=False, indent=2), encoding="utf-8")
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
