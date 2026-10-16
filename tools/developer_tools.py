"""Read-only developer diagnostics required by the railway-warlords architecture.

The tools inspect the same JSON, replay logs, and raster manifest that the Godot
runtime consumes. They never mutate content, saves, or images. Historical and
art review states remain explicit instead of being promoted by the checker.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
from typing import Any


P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_result(value: dict[str, Any], out: str | None) -> None:
    if out:
        path = Path(out)
        if not path.is_absolute():
            path = P / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def definitions() -> dict[str, list[dict[str, Any]]]:
    names = read(P / "content/definitions/catalog.json")["tables"]
    return {name: read(P / "content/definitions" / f"{name}.json") for name in names}


def maps() -> dict[str, dict[str, Any]]:
    return {name: read(P / "content/maps" / f"{name}.json") for name in read(P / "content/maps/catalog.json")["maps"]}


def scenarios() -> dict[str, dict[str, Any]]:
    return {name: read(P / "content/scenarios" / f"{name}.json") for name in read(P / "content/scenarios/catalog.json")["scenarios"]}


def scenario_inspector(args: argparse.Namespace) -> dict[str, Any]:
    all_scenarios = scenarios()
    if args.scenario not in all_scenarios:
        raise SystemExit(f"Unknown scenario: {args.scenario}")
    scenario = all_scenarios[args.scenario]
    all_maps = maps()
    map_data = all_maps[scenario["map_id"]]
    defs = definitions()
    faction_by_id = {row["id"]: row for row in defs["factions"]}
    roster = [{"id": faction, "name": faction_by_id.get(faction, {}).get("name", "<missing>"), "definition_found": faction in faction_by_id, "weak_tag": faction in scenario.get("weak_faction_ids", [])} for faction in scenario.get("faction_roster", [])]
    events = [{"id": event.get("id"), "date": event.get("date"), "type": event.get("type"), "source_ids": event.get("source_ids", []), "conditional": event.get("trigger_policy") == "conditional_conquest_calendar"} for event in scenario.get("events", [])]
    result = {
        "tool": "ScenarioInspector",
        "scenario_id": args.scenario,
        "scenario": {key: scenario.get(key) for key in ("id", "name", "anchor_date", "mode", "days_per_round", "round_limit", "content_status", "historical_status", "major_conflict", "map_id", "target_city_id", "player_formations", "enemy_formations", "source_ids")},
        "map": {"id": map_data["id"], "name": map_data["name"], "cells": len(map_data["cells"]), "cities": len(map_data["cities"]), "rail_nodes": len(map_data["rail_nodes"]), "rail_edges": len(map_data["rail_edges"]), "geography_status": map_data.get("geography_status"), "scale_revision": map_data.get("scale_revision")},
        "faction_roster": roster,
        "events": events,
        "source_resolution": {"scenario_sources": scenario.get("source_ids", []), "event_sources": sorted({source for event in scenario.get("events", []) for source in event.get("source_ids", [])}), "missing_faction_definitions": [row["id"] for row in roster if not row["definition_found"]]},
        "release_warning": "Authored tactical deployment is not a historical deployment release until the scenario's manual history audit is accepted." if scenario.get("content_status") != "historical_deployment_release" else "",
    }
    return result


def hex_inspector(args: argparse.Namespace) -> dict[str, Any]:
    all_maps = maps()
    if args.map not in all_maps:
        raise SystemExit(f"Unknown map: {args.map}")
    map_data = all_maps[args.map]
    cells = {cell["id"]: cell for cell in map_data["cells"]}
    selected = None
    if args.cell:
        selected = cells.get(args.cell)
    else:
        if args.r is None:
            raise SystemExit("--r is required with --q")
        selected = next((cell for cell in map_data["cells"] if cell["position"] == {"q": args.q, "r": args.r}), None)
    if selected is None:
        raise SystemExit("Cell not found")
    position = selected["position"]
    by_position = {(cell["position"]["q"], cell["position"]["r"]): cell for cell in map_data["cells"]}
    directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
    neighbors = []
    for dq, dr in directions:
        cell = by_position.get((position["q"] + dq, position["r"] + dr))
        neighbors.append({"q": position["q"] + dq, "r": position["r"] + dr, "cell_id": cell.get("id") if cell else None, "terrain_id": cell.get("terrain_id") if cell else None})
    city_rows = [city for city in map_data["cities"] if city["position"] == position]
    rail_node_rows = [node for node in map_data["rail_nodes"] if node["position"] == position]
    rail_ids = {row.get("id") for row in rail_node_rows}
    incident_edges = [edge for edge in map_data["rail_edges"] if edge.get("node_a") in rail_ids or edge.get("node_b") in rail_ids or edge.get("from") in rail_ids or edge.get("to") in rail_ids]
    return {"tool": "HexInspector", "map_id": args.map, "map_name": map_data["name"], "cell": selected, "neighbors": neighbors, "cities": city_rows, "rail_nodes": rail_node_rows, "incident_rail_edges": incident_edges, "geography_sources": map_data.get("sources", []), "administration_notes": map_data.get("administration_notes", [])}


def command_log(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.log)
    if not path.is_absolute():
        path = P / path
    if not path.is_file():
        raise SystemExit(f"Command log not found: {path}")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        command = row.get("command", {})
        if args.actor and row.get("actor") != args.actor:
            continue
        if args.type and command.get("type") != args.type:
            continue
        if args.round is not None and row.get("round_before") != args.round:
            continue
        rows.append(row)
    command_counts = Counter(row.get("command", {}).get("type", "<missing>") for row in rows)
    return {"tool": "CommandLog", "log": path.relative_to(P).as_posix() if path.is_relative_to(P) else str(path), "rows": len(rows), "command_counts": dict(sorted(command_counts.items())), "rounds": sorted({row.get("round_before") for row in rows}), "actors": sorted({row.get("actor") for row in rows}), "rows_preview": rows[: args.limit], "read_only": True}


def balance_runner(args: argparse.Namespace) -> dict[str, Any]:
    report_paths = [P / "reports/ai_soak.json", P / "reports/ai_full_conquest.json"]
    if args.report:
        report_paths = [Path(args.report) if Path(args.report).is_absolute() else P / args.report]
    summaries = []
    for path in report_paths:
        if not path.is_file():
            continue
        data = read(path)
        results = data.get("results", [])
        rows = []
        for row in results:
            rows.append({key: row.get(key) for key in ("id", "scenario", "player", "difficulty", "completed_rounds", "commands", "status", "rejects", "invariants_passed") if key in row})
        summaries.append({"report": path.relative_to(P).as_posix(), "content_hash": data.get("content_hash"), "cases": data.get("cases", len(rows)), "completed_rounds": data.get("completed_rounds"), "commands": data.get("commands"), "rejected_commands": sum(int(row.get("rejects", 0)) for row in results), "results": rows})
    outlier_rows = []
    for summary in summaries:
        for row in summary["results"]:
            if row.get("status") == "lost" or row.get("invariants_passed") is False:
                outlier_rows.append({"report": summary["report"], "case": row})
    return {"tool": "BalanceRunner", "mode": "read_authoritative_ai_reports", "reports": summaries, "outlier_or_manual_review_cases": outlier_rows, "human_balance_acceptance": False, "interpretation": "This runner summarizes actual Godot AI reports; it does not convert a win/loss into historical or human difficulty approval."}


def asset_validator(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read(P / "assets/manifest.json")
    rows = []
    errors = []
    for item in manifest["assets"]:
        path = P / item["engine_path"].removeprefix("res://")
        exists = path.is_file()
        digest = sha(path) if exists else None
        matches = exists and digest == item["source_sha256"]
        if not matches:
            errors.append({"id": item["id"], "path": str(path), "exists": exists, "actual_sha256": digest, "expected_sha256": item["source_sha256"]})
        rows.append({"id": item["id"], "path": path.relative_to(P).as_posix(), "exists": exists, "sha_matches": matches, "review_state": item.get("state"), "source_file": item.get("source_file")})
    return {"tool": "AssetValidator", "passed": not errors, "asset_count": len(rows), "review_state_counts": dict(Counter(row["review_state"] for row in rows)), "errors": errors, "raster_images_modified": False, "manual_visual_review": False, "assets": rows if args.verbose else []}


def historical_release_checker(args: argparse.Namespace) -> dict[str, Any]:
    all_scenarios = scenarios()
    all_maps = maps()
    defs = definitions()
    source_ids = {row.get("id") for row in defs.get("sources", [])}
    source_ids.update(row.get("id") for row in read(P / "content/geography_sources.json").get("sources", []))
    timeline_path = P / "content/history/asia_timeline.json"
    local_references = {}
    if timeline_path.is_file():
        timeline = read(timeline_path)
        source_ids.update(row["id"] for row in timeline.get("sources", []))
        if timeline.get("timelines"):
            source_ids.add("asia_timeline")
            local_references["asia_timeline"] = timeline_path.relative_to(P).as_posix()
    rows = []
    errors = []
    for scenario_id, scenario in all_scenarios.items():
        map_data = all_maps.get(scenario.get("map_id"), {})
        scenario_sources = set(scenario.get("source_ids", []))
        event_sources = {source for event in scenario.get("events", []) for source in event.get("source_ids", [])}
        missing_sources = sorted((scenario_sources | event_sources) - source_ids)
        status = "pending_manual_historical_release" if scenario.get("content_status") != "historical_deployment_release" or scenario.get("historical_status") != "historical_deployment_release" else "historical_release_flag_present"
        row = {"scenario_id": scenario_id, "map_id": scenario.get("map_id"), "content_status": scenario.get("content_status"), "historical_status": scenario.get("historical_status"), "source_ids": sorted(scenario_sources | event_sources), "missing_source_ids": missing_sources, "map_geography_status": map_data.get("geography_status"), "map_sources": map_data.get("sources", []), "administration_notes": map_data.get("administration_notes", []), "release_status": status}
        rows.append(row)
        if missing_sources:
            errors.append({"scenario_id": scenario_id, "missing_source_ids": missing_sources})
    return {"tool": "HistoricalReleaseChecker", "passed": not errors, "scenarios": len(rows), "source_ids_available": len(source_ids), "local_reference_ids": local_references, "rows": rows, "errors": errors, "historical_deployment_release": False, "interpretation": "A passing source-link check does not approve authored tactical deployments, equipment white lists, county borders, person affiliations, or human history review."}


def smoke_test(args: argparse.Namespace) -> dict[str, Any]:
    inspected = scenario_inspector(argparse.Namespace(scenario="conq_1924"))
    first_cell = maps()["conquest_china"]["cells"][0]["id"]
    hex_result = hex_inspector(argparse.Namespace(map="conquest_china", cell=first_cell, q=None, r=None))
    log_result = command_log(argparse.Namespace(log="reports/endurance/20261011T201519Z-154099b5/commands.jsonl", actor=None, type=None, round=None, limit=1))
    balance_result = balance_runner(argparse.Namespace(report=None))
    assets_result = asset_validator(argparse.Namespace(verbose=False))
    history_result = historical_release_checker(argparse.Namespace())
    for filename, value in [
        ("developer_scenario_conq_1924.json", inspected),
        ("developer_hex_first_cell.json", hex_result),
        ("developer_command_log_attack.json", log_result),
        ("developer_balance_matrix.json", balance_result),
        ("developer_asset_validation.json", assets_result),
        ("developer_historical_release_check.json", history_result),
    ]:
        (P / "reports" / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    checks = {
        "scenario_map_is_real_large_conquest": inspected["map"]["cells"] == 74762 and inspected["map"]["cities"] == 55,
        "scenario_factions_resolve": not inspected["source_resolution"]["missing_faction_definitions"],
        "hex_neighbors_are_reported": len(hex_result["neighbors"]) == 6,
        "command_log_has_actual_commands": log_result["rows"] >= 1,
        "balance_reports_have_no_rejected_commands": len(balance_result["reports"]) == 2 and all(row["rejected_commands"] == 0 for row in balance_result["reports"]),
        "asset_manifest_is_byte_valid": assets_result["passed"] and assets_result["asset_count"] == len(read(P / "assets/manifest.json")["assets"]),
        "history_source_links_resolve": history_result["passed"] and history_result["scenarios"] == len(scenarios()),
    }
    return {"tool": "DeveloperToolsSmoke", "passed": all(checks.values()), "checks": checks, "asset_review_states": assets_result["review_state_counts"], "historical_deployment_release": history_result["historical_deployment_release"], "manual_balance_acceptance": balance_result["human_balance_acceptance"], "source_reports": ["reports/developer_scenario_conq_1924.json", "reports/developer_hex_first_cell.json", "reports/developer_command_log_attack.json", "reports/developer_balance_matrix.json", "reports/developer_asset_validation.json", "reports/developer_historical_release_check.json"], "scope": "Read-only smoke of all six required developer diagnostics against current Godot content and evidence. It does not approve manual history, art, balance, or device acceptance."}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Godot developer diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("scenario", help="ScenarioInspector")
    p.add_argument("scenario")
    p.add_argument("--out")
    p.set_defaults(handler=scenario_inspector)
    p = sub.add_parser("hex", help="HexInspector")
    p.add_argument("map")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--cell")
    group.add_argument("--q", type=int)
    p.add_argument("--r", type=int)
    p.add_argument("--out")
    p.set_defaults(handler=hex_inspector)
    p = sub.add_parser("log", help="CommandLog")
    p.add_argument("--log", default="reports/endurance/20261011T201519Z-154099b5/commands.jsonl")
    p.add_argument("--actor")
    p.add_argument("--type")
    p.add_argument("--round", type=int)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--out")
    p.set_defaults(handler=command_log)
    p = sub.add_parser("balance", help="BalanceRunner")
    p.add_argument("--report")
    p.add_argument("--out")
    p.set_defaults(handler=balance_runner)
    p = sub.add_parser("assets", help="AssetValidator")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--out")
    p.set_defaults(handler=asset_validator)
    p = sub.add_parser("history", help="HistoricalReleaseChecker")
    p.add_argument("--out")
    p.set_defaults(handler=historical_release_checker)
    p = sub.add_parser("smoke", help="Run all developer diagnostics read-only")
    p.add_argument("--out", default="reports/developer_tools_smoke.json")
    p.set_defaults(handler=smoke_test)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.handler(args)
    write_result(result, args.out)
    if args.command in {"assets", "history"} and not result.get("passed", False):
        # A failed or pending release audit is an honest result, not a tool crash.
        return 2 if args.command == "history" else 1
    if args.command == "smoke" and not result.get("passed", False):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
