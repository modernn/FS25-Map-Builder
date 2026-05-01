#!/usr/bin/env python3
"""Initialize or adopt FS25 Map Builder projects.

This helper is intentionally conservative. It creates planning/profile
artifacts and a bootstrap wrapper, but it does not claim the project can build a
map until project-specific slices are implemented and verified.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


PLANNING_PHASES: tuple[dict[str, object], ...] = (
    {
        "slug": "source-reference",
        "title": "Source Reference",
        "goal": "Build the allowed, region-specific reference set before producing map assets.",
        "tasks": [
            "Record map extent, center, profile id, and required landmarks.",
            "Collect public or licensed imagery, elevation, parcel, road, and hydro references.",
            "Write source provenance and license notes for every shipped derivative.",
        ],
        "acceptance": [
            "Reference manifest exists and identifies allowed versus reference-only sources.",
            "Required roads, farms, shops, and public anchors have coordinates or placement notes.",
        ],
    },
    {
        "slug": "terrain-heightmap",
        "title": "Terrain Heightmap",
        "goal": "Create a playable terrain base that respects the real local relief.",
        "tasks": [
            "Generate heightmap from approved elevation data.",
            "Smooth gameplay-critical routes without flattening regional identity.",
            "Audit slopes, playable bounds, and off-map containment.",
        ],
        "acceptance": [
            "Heightmap and terrain scale are documented.",
            "Vehicle routes are passable and the player cannot drive out of the playable map.",
        ],
    },
    {
        "slug": "base-map",
        "title": "Base Map",
        "goal": "Create the FS25 map shell, i3d references, density maps, and core XML wiring.",
        "tasks": [
            "Create or verify map directory structure and modDesc references.",
            "Generate base textures, density maps, and overview assets.",
            "Run load/package checks before adding complex content.",
        ],
        "acceptance": [
            "Map loads in the toolchain without missing required files.",
            "No generated base asset points outside the project package.",
        ],
    },
    {
        "slug": "roads",
        "title": "Roads",
        "goal": "Bake a drivable road network that follows real road classes and access rules.",
        "tasks": [
            "Survey centerlines, road class, access, and surface notes.",
            "Bake road surfaces and shoulders with visible QA previews.",
            "Grade road terrain and remove stray road/street artifacts.",
        ],
        "acceptance": [
            "Road QA reports core routes passable and visually coherent.",
            "No random street fragments or off-map road escapes remain.",
        ],
    },
    {
        "slug": "fields",
        "title": "Fields",
        "goal": "Create region-plausible playable fields and contracts.",
        "tasks": [
            "Survey field parcels, sizes, access points, and ownership boundaries.",
            "Bake field surfaces and field XML from deterministic data.",
            "Verify fields are visible, playable, buyable, and not overlapping roads/buildings.",
        ],
        "acceptance": [
            "Field layout and XML audits pass.",
            "Human tester can identify farms, fields, and workable parcels in-game.",
        ],
    },
    {
        "slug": "landmarks-shops-farmyards",
        "title": "Landmarks, Shops, And Farmyards",
        "goal": "Place the player-facing structures that make the map recognizable and useful.",
        "tasks": [
            "Survey farmyards, sheds, shops, silos, homes, and public landmarks.",
            "Place or proxy buildings with correct access, triggers, and openable doors where expected.",
            "Run visual QA for important anchors from player-height views.",
        ],
        "acceptance": [
            "Dealer/shop, sell points, farmyards, and landmarks are visible and reachable.",
            "Interactive structures expected by players, including shed doors, behave correctly.",
        ],
    },
    {
        "slug": "vegetation-landscape",
        "title": "Vegetation And Landscape",
        "goal": "Add regional vegetation, ground cover, water, and terrain dressing without hiding gameplay.",
        "tasks": [
            "Define tree, brush, grass, crop, and ground-cover palettes for the region.",
            "Bake vegetation density and landscape materials from approved references.",
            "Audit visibility, collisions, field edges, and performance.",
        ],
        "acceptance": [
            "Vegetation matches the target region and does not block key gameplay routes.",
            "Landscape QA includes both automated previews and human-drive checks.",
        ],
    },
    {
        "slug": "region-systems",
        "title": "Region Systems",
        "goal": "Configure gameplay systems so the map feels local, not generic.",
        "tasks": [
            "Configure crops, calendar, economy, traffic, snow/weather assumptions, and fill types.",
            "Document intentional deviations from the real region for FS25 gameplay.",
            "Run system audits for missing or conflicting XML references.",
        ],
        "acceptance": [
            "Region-specific gameplay assumptions are documented.",
            "System audit reports no broken references or missing placeable dependencies.",
        ],
    },
    {
        "slug": "package",
        "title": "Package",
        "goal": "Produce a clean preview zip that can be installed and tested repeatedly.",
        "tasks": [
            "Package the map with only allowed files and local dependencies.",
            "Run manifest, license, missing-file, and package-size audits.",
            "Install the preview zip into the configured FS25 mods directory.",
        ],
        "acceptance": [
            "Package audit passes and reports a preview zip hash.",
            "Installed mod zip is the same artifact produced by the package gate.",
        ],
    },
    {
        "slug": "human-test",
        "title": "Human Verification",
        "goal": "Prove the map works from the player seat before calling it ready.",
        "tasks": [
            "Load the map in FS25 and complete the morning verification checklist.",
            "Drive roads, field access, shops, farmyards, boundaries, and landmarks.",
            "Record failures into the fix queue before additional automation work.",
        ],
        "acceptance": [
            "Human verification document is filled in with pass/fail evidence.",
            "Blockers are either fixed or intentionally deferred with owner and reason.",
        ],
    },
)

DEFAULT_PHASES = tuple(str(phase["slug"]) for phase in PLANNING_PHASES)


BOOTSTRAP_PS1 = r'''param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        & $VenvPython "scripts\fs25.py" @CommandArgs
    } else {
        & python "scripts\fs25.py" @CommandArgs
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
'''


BOOTSTRAP_PY = r'''#!/usr/bin/env python3
"""Bootstrap FS25 project wrapper.

Replace this with project-specific deterministic slices as generators and QA
gates are added.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


STATE_PATH = Path(".fs25-map-builder.json")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"project_name": Path.cwd().name, "phases": []}


def phases(state: dict) -> list[str]:
    raw = state.get("phases")
    return [str(item) for item in raw] if isinstance(raw, list) else []


def cmd_status(_: argparse.Namespace) -> int:
    state = load_state()
    print(f"FS25 project: {state.get('project_name', Path.cwd().name)}")
    print(f"location: {state.get('location', 'unknown')}")
    print(f"profile: {state.get('profile_path', 'not configured')}")
    print("")
    print("Bootstrap phases:")
    for phase in phases(state):
        marker = "HUMAN" if phase == "human-test" else "TODO"
        print(f"  {marker:5} {phase}")
    print("")
    print("Next: implement project-specific generators and QA gates in scripts/fs25.py.")
    return 0


def cmd_recommend(_: argparse.Namespace) -> int:
    state = load_state()
    print("Recommended next FS25 action:")
    print("  Work from .planning/STATE.md and .planning/TASKS.md, starting with source-reference.")
    print("")
    print("Useful commands:")
    print("  .\\scripts\\fs25.ps1 status")
    print("  .\\scripts\\fs25.ps1 list")
    if state.get("mode") in {"init", "adopt"}:
        print("  Ask Codex or Claude to run the next planned FS25 slice.")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    for phase in phases(load_state()):
        print(phase)
    return 0


def cmd_start(_: argparse.Namespace) -> int:
    cmd_recommend(_)
    print("")
    print("No automated build slice is configured yet.")
    return 2


def cmd_run(args: argparse.Namespace) -> int:
    print(f"No automated slice is configured for: {args.slice}")
    return 2


def cmd_install(_: argparse.Namespace) -> int:
    state = load_state()
    preview_zip = Path(str(state.get("preview_zip", "")))
    mods_dir_raw = str(state.get("mods_dir") or "").strip()
    if not preview_zip.exists() or not mods_dir_raw:
        print("Preview zip or mods_dir is not configured yet.")
        return 2
    mods_dir = Path(mods_dir_raw)
    mods_dir.mkdir(parents=True, exist_ok=True)
    destination = mods_dir / preview_zip.name
    shutil.copy2(preview_zip, destination)
    print(f"Installed {destination}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap FS25 project command wrapper.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("recommend", aliases=["next"]).set_defaults(func=cmd_recommend)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("start").set_defaults(func=cmd_start)
    run = sub.add_parser("run")
    run.add_argument("slice")
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)
    install = sub.add_parser("install")
    install.add_argument("--dry-run", action="store_true")
    install.set_defaults(func=cmd_install)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
'''


@dataclass(frozen=True)
class WriteResult:
    path: Path
    action: str


def slugify(value: str, fallback: str = "fs25-map") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--bbox-wgs84-wsen must be west,south,east,north")
    return tuple(float(part) for part in parts)  # type: ignore[return-value]


def bbox_from_center(lat: float, lon: float, map_size_m: int) -> tuple[float, float, float, float]:
    half_m = map_size_m / 2.0
    lat_delta = half_m / 111_320.0
    lon_scale = max(0.1, math.cos(math.radians(lat)))
    lon_delta = half_m / (111_320.0 * lon_scale)
    return (lon - lon_delta, lat - lat_delta, lon + lon_delta, lat + lat_delta)


def split_landmarks(values: Iterable[str] | None) -> list[str]:
    landmarks: list[str] = []
    for value in values or []:
        for item in re.split(r"[;\n]", value):
            item = item.strip()
            if item:
                landmarks.append(item)
    return landmarks


def write_file(path: Path, content: str, *, overwrite: bool) -> WriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return WriteResult(path, "kept")
    path.write_text(content, encoding="utf-8", newline="\n")
    return WriteResult(path, "wrote")


def write_json(path: Path, payload: dict, *, overwrite: bool) -> WriteResult:
    return write_file(path, json.dumps(payload, indent=2) + "\n", overwrite=overwrite)


def project_signals(project: Path) -> dict[str, object]:
    return {
        "has_git": (project / ".git").exists(),
        "has_wrapper_ps1": (project / "scripts" / "fs25.ps1").exists(),
        "has_wrapper_py": (project / "scripts" / "fs25.py").exists(),
        "profiles": [str(path.relative_to(project)) for path in sorted((project / "profiles").glob("*.json"))]
        if (project / "profiles").exists()
        else [],
        "build_dirs": [str(path.relative_to(project)) for path in sorted((project / "build").glob("*")) if path.is_dir()]
        if (project / "build").exists()
        else [],
    }


def first_existing_profile(project: Path) -> tuple[Path, dict[str, object]] | None:
    profiles_dir = project / "profiles"
    if not profiles_dir.exists():
        return None
    for path in sorted(profiles_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return path, data
    return None


def existing_state(project: Path) -> dict[str, object]:
    path = project / ".fs25-map-builder.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def apply_defaults(args: argparse.Namespace, mode: str) -> tuple[tuple[float, float, float, float], list[str], Path]:
    args.project = (args.project or Path.cwd()).resolve()
    state = existing_state(args.project)
    profile_info = first_existing_profile(args.project)
    profile_path: Path | None = None
    profile_data: dict[str, object] = {}
    if profile_info is not None:
        profile_path, profile_data = profile_info

    args.project_name = args.project_name or str(state.get("project_name") or profile_data.get("profile_id") or args.project.name)
    args.location = args.location or str(state.get("location") or profile_data.get("description") or "TODO: real-world location")
    args.profile_id = args.profile_id or str(profile_data.get("profile_id") or slugify(args.project_name))
    args.map_size_m = args.map_size_m or int(profile_data.get("map_size_m") or 0)
    args.heightmap_max_m = args.heightmap_max_m or int(profile_data.get("heightmap_max_m") or 1000)
    args.terrain_height_scale_m = args.terrain_height_scale_m or int(
        profile_data.get("terrain_height_scale_m") or args.heightmap_max_m
    )
    args.preview_zip = args.preview_zip or profile_data.get("preview_zip") or f"build/FS25_{args.profile_id}_preview.zip"
    args.description = args.description or str(profile_data.get("description") or f"{args.project_name} FS25 map")

    center = profile_data.get("center_wgs84_lat_lon")
    if args.center_lat is None and isinstance(center, list) and len(center) >= 2:
        args.center_lat = float(center[0])
    if args.center_lon is None and isinstance(center, list) and len(center) >= 2:
        args.center_lon = float(center[1])

    bbox = parse_bbox(args.bbox_wgs84_wsen)
    if bbox is None:
        existing_bbox = profile_data.get("bbox_wgs84_wsen")
        if isinstance(existing_bbox, list) and len(existing_bbox) == 4:
            bbox = tuple(float(value) for value in existing_bbox)  # type: ignore[assignment]
    if bbox is not None:
        if args.center_lat is None:
            args.center_lat = (bbox[1] + bbox[3]) / 2.0
        if args.center_lon is None:
            args.center_lon = (bbox[0] + bbox[2]) / 2.0

    missing = []
    if not args.map_size_m:
        missing.append("--map-size-m")
    if args.center_lat is None:
        missing.append("--center-lat")
    if args.center_lon is None:
        missing.append("--center-lon")
    if missing:
        raise ValueError(
            f"{mode} needs {', '.join(missing)} unless an existing profiles/*.json supplies them"
        )
    if bbox is None:
        bbox = bbox_from_center(float(args.center_lat), float(args.center_lon), int(args.map_size_m))

    landmarks = split_landmarks(args.landmark)
    if not landmarks and isinstance(state.get("landmarks"), list):
        landmarks = [str(item) for item in state["landmarks"]]

    profile_rel = Path("profiles") / f"{args.profile_id}.json"
    if profile_path is not None and profile_path.is_relative_to(args.project):
        profile_rel = profile_path.relative_to(args.project)
    return bbox, landmarks, profile_rel


def profile_payload(args: argparse.Namespace, bbox: tuple[float, float, float, float]) -> dict[str, object]:
    return {
        "profile_id": args.profile_id,
        "description": args.description or f"{args.project_name} FS25 map",
        "map_size_m": args.map_size_m,
        "heightmap_max_m": args.heightmap_max_m,
        "terrain_height_scale_m": args.terrain_height_scale_m or args.heightmap_max_m,
        "bbox_wgs84_wsen": list(bbox),
        "center_wgs84_lat_lon": [args.center_lat, args.center_lon],
        "build_dir": f"build/{args.profile_id}",
        "preview_zip": preview_zip_value(args),
    }


def preview_zip_value(args: argparse.Namespace) -> str:
    return str(args.preview_zip or f"build/FS25_{args.profile_id}_preview.zip")


def state_payload(
    args: argparse.Namespace,
    profile_path: Path,
    landmarks: list[str],
    mode: str,
    bbox: tuple[float, float, float, float],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "fs25-map-builder.project.v1",
        "mode": mode,
        "project_name": args.project_name,
        "location": args.location,
        "map_size_m": args.map_size_m,
        "center_lat": args.center_lat,
        "center_lon": args.center_lon,
        "bbox_wsen": list(bbox),
        "profile_path": str(profile_path).replace("\\", "/"),
        "preview_zip": preview_zip_value(args),
        "mods_dir": args.mods_dir or "",
        "landmarks": landmarks,
        "phases": list(DEFAULT_PHASES),
        "active_gate": DEFAULT_PHASES[0],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return payload


def markdown_list(items: Iterable[str], fallback: str) -> list[str]:
    lines = [f"- {item}" for item in items]
    return lines or [f"- {fallback}"]


def markdown_checklist(items: Iterable[str], fallback: str) -> list[str]:
    lines = [f"- [ ] {item}" for item in items]
    return lines or [f"- [ ] {fallback}"]


def phase_items(phase: dict[str, object], key: str) -> list[str]:
    raw = phase.get(key, [])
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def phase_dir_name(index: int, phase: dict[str, object]) -> str:
    return f"{index:02d}-{phase['slug']}"


def project_markdown(
    args: argparse.Namespace,
    bbox: tuple[float, float, float, float],
    landmarks: list[str],
    profile_path: Path,
) -> str:
    return "\n".join(
        [
            "# FS25 Project",
            "",
            "Generated by `fs25-init` / `fs25-adopt`.",
            "",
            "## Project",
            "",
            f"- Name: `{args.project_name}`",
            f"- Location: `{args.location}`",
            f"- Profile id: `{args.profile_id}`",
            f"- Profile path: `{profile_path}`",
            f"- Map size: `{args.map_size_m}` m",
            f"- Center lat/lon: `{args.center_lat}`, `{args.center_lon}`",
            f"- BBox W/S/E/N: `{bbox[0]}`, `{bbox[1]}`, `{bbox[2]}`, `{bbox[3]}`",
            f"- Preview zip: `{preview_zip_value(args)}`",
            "",
            "## Required Anchors",
            "",
            *markdown_list(landmarks, "Add landmarks, farms, shops, fields, and public reference anchors."),
            "",
            "## Agent Contract",
            "",
            "- The user invokes `$fs25-*` or `/fs25-*`; Codex or Claude runs the scripts and reports results.",
            "- Do not ask the user to run wrapper commands unless they explicitly want to.",
            "- Preserve existing map work during adoption unless `--force` is explicitly requested.",
            "- Treat every generated map feature as incomplete until it has automated QA and human verification evidence.",
            "",
        ]
    )


def roadmap_markdown() -> str:
    rows = [
        "| Phase | Goal | Done When |",
        "| --- | --- | --- |",
    ]
    for index, phase in enumerate(PLANNING_PHASES, start=1):
        acceptance = phase_items(phase, "acceptance")
        done_when = acceptance[0] if acceptance else "Acceptance is documented."
        rows.append(f"| {index:02d}. {phase['title']} | {phase['goal']} | {done_when} |")
    return "\n".join(
        [
            "# FS25 Roadmap",
            "",
            "This roadmap is generated during project init/adoption and should be updated as slices become real.",
            "",
            *rows,
            "",
            "## Operating Rule",
            "",
            "Advance only when the current phase has fresh automated evidence or is explicitly blocked on human verification.",
            "",
        ]
    )


def requirements_markdown(args: argparse.Namespace, landmarks: list[str]) -> str:
    return "\n".join(
        [
            "# FS25 Requirements",
            "",
            "Requirements are grouped by FS25 production gate and traced back to the authoritative docs.",
            "",
            "## Map Scope",
            "",
            f"- Build a `{args.map_size_m}` m FS25 map for `{args.location}`.",
            "- Preserve regional identity in terrain, roads, farms, buildings, vegetation, and gameplay systems.",
            "- Keep shipped content license-safe and reproducible from documented sources.",
            "",
            "## Required Anchors",
            "",
            *markdown_list(landmarks, "Add required farms, shops, landmarks, field areas, and access roads."),
            "",
            "## Gate Requirements",
            "",
            *[f"- `{phase['slug']}`: {phase['goal']}" for phase in PLANNING_PHASES],
            "",
            "## Verification Requirements",
            "",
            "- Automated QA must write a durable artifact before a gate can be marked complete.",
            "- Human verification is required for load, driving, boundaries, fields, shops, save/reload, and performance.",
            "- Failures belong in `docs/fs25_fix_queue.md` until fixed or explicitly deferred.",
            "",
        ]
    )


def state_markdown(args: argparse.Namespace, mode: str) -> str:
    return "\n".join(
        [
            "# FS25 State",
            "",
            f"- Project: `{args.project_name}`",
            f"- Mode: `{mode}`",
            f"- Generated: `{datetime.now().astimezone().isoformat(timespec='seconds')}`",
            "- Current milestone: `fs25-map-ready`",
            "- Current phase: `01-source-reference`",
            "- FS25 source of truth: `docs/fs25_map_state.md`",
            "- Next recommended action: build/verify the source-reference slice, then update this file.",
            "",
            "## Stop Conditions",
            "",
            "- A generator changes shipped content without a matching QA artifact.",
            "- A source lacks provenance or license notes.",
            "- A player-facing issue appears in roads, fields, buildings, boundaries, or save/load behavior.",
            "- Human verification finds a blocker.",
            "",
            "## Handoff Notes",
            "",
            "- Keep `docs/fs25_project_brief.md`, `.planning/TASKS.md`, and this file current.",
            "- Put failures into a fix queue before starting another visual/content phase.",
            "",
        ]
    )


def tasks_markdown() -> str:
    lines = [
        "# FS25 Tasks",
        "",
        "Generated project task list. Check items only after fresh evidence exists.",
        "",
    ]
    for index, phase in enumerate(PLANNING_PHASES, start=1):
        lines.extend(
            [
                f"## {index:02d}. {phase['title']}",
                "",
                *markdown_checklist(phase_items(phase, "tasks"), "Define phase tasks."),
                "",
                "### Acceptance",
                "",
                *markdown_checklist(phase_items(phase, "acceptance"), "Define phase acceptance evidence."),
                "",
            ]
        )
    return "\n".join(lines)


def milestone_markdown(args: argparse.Namespace) -> str:
    phase_lines = [f"- [ ] {index:02d}. {phase['title']}: {phase['goal']}" for index, phase in enumerate(PLANNING_PHASES, start=1)]
    return "\n".join(
        [
            "# Milestone: FS25 Map Ready",
            "",
            f"Project: `{args.project_name}`",
            "",
            "## Outcome",
            "",
            "A packaged FS25 preview map that loads, drives, saves, and represents the target region well enough for human verification.",
            "",
            "## Phase Checklist",
            "",
            *phase_lines,
            "",
            "## Required Evidence",
            "",
            "- Source provenance and license audit.",
            "- Terrain, road, field, farmyard/shop, vegetation, and package QA artifacts.",
            "- Installed preview zip hash.",
            "- Completed human verification checklist.",
            "",
        ]
    )


def phase_plan_markdown(index: int, phase: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# Phase {index:02d}: {phase['title']}",
            "",
            "## Goal",
            "",
            str(phase["goal"]),
            "",
            "## Tasks",
            "",
            *markdown_checklist(phase_items(phase, "tasks"), "Define phase tasks."),
            "",
            "## QA Gates",
            "",
            *markdown_checklist(phase_items(phase, "acceptance"), "Define acceptance evidence."),
            "",
            "## Notes",
            "",
            "- Prefer deterministic generators and repeatable audits over hand edits.",
            "- Record regional assumptions and source provenance in the project docs.",
            "- Leave this phase open until evidence is current.",
            "",
        ]
    )


def docs_milestone_plan_markdown() -> str:
    return "\n".join(
        [
            "# FS25 Milestone Plan",
            "",
            "Codex/Claude should use `.planning/STATE.md`, `.planning/TASKS.md`, and `.planning/phases/*/PLAN.md` as the work queue.",
            "",
            "## Commands",
            "",
            "Ask the agent for `$fs25-progress`, `$fs25-next`, `$fs25-start`, or `$fs25-adopt`; the agent should run the wrapper and summarize results.",
            "",
            "## Phase Order",
            "",
            *[f"- {index:02d}. {phase['title']} (`{phase['slug']}`)" for index, phase in enumerate(PLANNING_PHASES, start=1)],
            "",
            "## Human Gate",
            "",
            "The final ready decision belongs to the FS25 human verification checklist, not to generated files alone.",
            "",
        ]
    )


def map_state_markdown(
    args: argparse.Namespace,
    bbox: tuple[float, float, float, float],
    profile_path: Path,
    *,
    mode: str,
) -> str:
    rows = [
        "| Stage | Status | Evidence | Blocker |",
        "| --- | --- | --- | --- |",
    ]
    for index, phase in enumerate(PLANNING_PHASES, start=1):
        status = "active" if index == 1 else "pending"
        rows.append(f"| {phase['slug']} | {status} | `.planning/phases/{phase_dir_name(index, phase)}/PLAN.md` |  |")
    return "\n".join(
        [
            "# FS25 Map State",
            "",
            f"- Last updated: `{datetime.now().astimezone().isoformat(timespec='seconds')}`",
            f"- Active map: `{args.project_name}`",
            f"- Adoption mode: `{mode}`",
            "- Overall status: `planning`",
            "- Current gate: `source-reference`",
            f"- Profile: `{profile_path}`",
            f"- Preview zip: `{preview_zip_value(args)}`",
            "",
            "## Scope",
            "",
            f"- Location: `{args.location}`",
            f"- Map size: `{args.map_size_m}` m",
            f"- Center lat/lon: `{args.center_lat}`, `{args.center_lon}`",
            f"- BBox W/S/E/N: `{bbox[0]}`, `{bbox[1]}`, `{bbox[2]}`, `{bbox[3]}`",
            "",
            "## Stage Board",
            "",
            *rows,
            "",
            "## Current Focus",
            "",
            "- Build the source/reference gate and record source provenance before new generated map content.",
            "",
            "## Evidence Ledger",
            "",
            "- TODO: add source manifest, QA reports, package audit, preview hash, and human verification evidence.",
            "",
            "## Automation Inventory",
            "",
            "- `scripts/fs25.ps1`: agent-facing command wrapper.",
            "- `scripts/fs25.py`: project automation entrypoint.",
            "- `.fs25-map-builder.json`: machine-readable project state.",
            "",
            "## Human Review Needed",
            "",
            "- Load, driveability, roads, fields, shops/farmyards, boundaries, save/reload, and performance.",
            "",
            "## Ship Constraints",
            "",
            "- No missing local references.",
            "- No unlicensed shipped derivatives.",
            "- No known blockers in `docs/fs25_fix_queue.md`.",
            "",
        ]
    )


def fix_queue_markdown() -> str:
    return "\n".join(
        [
            "# FS25 Fix Queue",
            "",
            "Record every failed QA or human verification finding here before starting another content gate.",
            "",
            "## Open Issues",
            "",
            "| ID | Severity | Stage | Status | Issue | Evidence | Next action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| FQ-001 | info | source-reference | placeholder | Replace this row with the first real issue. |  |  |",
            "",
            "## Closed Issues",
            "",
            "| ID | Severity | Stage | Status | Fix/defer reason | Verification |",
            "| --- | --- | --- | --- | --- | --- |",
            "",
            "## Queue Rules",
            "",
            "- Do not close an issue without fresh verification evidence.",
            "- Use blocker severity for load failures, broken save/reload, out-of-map escape, or unusable core gameplay.",
            "- Deferred issues need an explicit reason and the next milestone where they will be revisited.",
            "",
        ]
    )


def gsd_chain_markdown() -> str:
    rows = [
        "| GSD phase | FS25 gate | Source of truth | Exit evidence |",
        "| --- | --- | --- | --- |",
    ]
    for phase in PLANNING_PHASES:
        rows.append(f"| `{phase['slug']}` | `{phase['slug']}` | `docs/fs25_map_state.md` | QA artifact or human note |")
    return "\n".join(
        [
            "# FS25 GSD Chain",
            "",
            "FS25 state is authoritative; `.planning` mirrors routing so agents can stay on task.",
            "",
            "## Gate Mapping",
            "",
            *rows,
            "",
            "## Routing Rules",
            "",
            "- `what next`: read `docs/fs25_map_state.md`, `.planning/STATE.md`, and `.planning/TASKS.md`.",
            "- `do it`: run the applicable `$fs25-*` command or wrapper and update evidence.",
            "- `plan`: create or update the smallest needed phase plan before implementation.",
            "- `pause` or `handoff`: update state, fix queue, evidence links, and next action.",
            "",
            "## Verification Rule",
            "",
            "No gate is complete until current evidence is present in docs, tests, or human verification.",
            "",
        ]
    )


def human_verification_markdown() -> str:
    return "\n".join(
        [
            "# Morning Human Verification",
            "",
            "Complete this in FS25 after the preview zip is installed.",
            "",
            "## Checklist",
            "",
            "- [ ] Install/load: map appears in FS25 and starts without fatal errors.",
            "- [ ] Primary route: drive the main road loop without harsh terrain jolts or random road artifacts.",
            "- [ ] Boundary: attempt edge routes and verify the player cannot drive off the map.",
            "- [ ] Fields: fields are visible, accessible, and usable for expected gameplay.",
            "- [ ] Dealer/shop: shop/dealer/sell areas are visible, reachable, and functional.",
            "- [ ] Farmyards/buildings: expected doors, sheds, and yards behave correctly.",
            "- [ ] Save/reload: save, exit, reload, and confirm player state persists.",
            "- [ ] Performance: note load time, stutter, and obvious frame drops.",
            "- [ ] Evidence: capture screenshots/log notes for failures.",
            "",
            "## Failure Recording",
            "",
            "Put every failure in `docs/fs25_fix_queue.md` with severity, evidence, and next action.",
            "",
        ]
    )


def project_management_results(
    project: Path,
    args: argparse.Namespace,
    bbox: tuple[float, float, float, float],
    profile_path: Path,
    *,
    mode: str,
    overwrite: bool,
) -> list[WriteResult]:
    return [
        write_file(project / "docs" / "fs25_map_state.md", map_state_markdown(args, bbox, profile_path, mode=mode), overwrite=overwrite),
        write_file(project / "docs" / "fs25_fix_queue.md", fix_queue_markdown(), overwrite=overwrite),
        write_file(project / "docs" / "fs25_gsd_chain.md", gsd_chain_markdown(), overwrite=overwrite),
        write_file(project / "docs" / "morning_human_verification.md", human_verification_markdown(), overwrite=overwrite),
    ]


def planning_results(
    project: Path,
    args: argparse.Namespace,
    bbox: tuple[float, float, float, float],
    landmarks: list[str],
    profile_path: Path,
    *,
    mode: str,
    overwrite: bool,
) -> list[WriteResult]:
    planning_dir = project / ".planning"
    results = [
        write_file(planning_dir / "PROJECT.md", project_markdown(args, bbox, landmarks, profile_path), overwrite=overwrite),
        write_file(planning_dir / "REQUIREMENTS.md", requirements_markdown(args, landmarks), overwrite=overwrite),
        write_file(planning_dir / "ROADMAP.md", roadmap_markdown(), overwrite=overwrite),
        write_file(planning_dir / "STATE.md", state_markdown(args, mode), overwrite=overwrite),
        write_file(planning_dir / "TASKS.md", tasks_markdown(), overwrite=overwrite),
        write_file(planning_dir / "milestones" / "fs25-map-ready.md", milestone_markdown(args), overwrite=overwrite),
        write_file(project / "docs" / "fs25_milestone_plan.md", docs_milestone_plan_markdown(), overwrite=overwrite),
    ]
    for index, phase in enumerate(PLANNING_PHASES, start=1):
        results.append(
            write_file(
                planning_dir / "phases" / phase_dir_name(index, phase) / "PLAN.md",
                phase_plan_markdown(index, phase),
                overwrite=overwrite,
            )
        )
    return results


def brief_markdown(args: argparse.Namespace, bbox: tuple[float, float, float, float], landmarks: list[str]) -> str:
    landmark_lines = [f"- {item}" for item in landmarks] or ["- TODO: add public landmarks, farmyards, shops, and local reference points."]
    return "\n".join(
        [
            "# FS25 Project Brief",
            "",
            "Generated by `fs25-init` / `project_setup.py`.",
            "",
            f"- Project: `{args.project_name}`",
            f"- Location: `{args.location}`",
            f"- Profile id: `{args.profile_id}`",
            f"- Map size: `{args.map_size_m}` m",
            f"- Center lat/lon: `{args.center_lat}`, `{args.center_lon}`",
            f"- BBox W/S/E/N: `{bbox[0]}`, `{bbox[1]}`, `{bbox[2]}`, `{bbox[3]}`",
            f"- Height scale: `{args.heightmap_max_m}` m",
            "",
            "## Landmarks And Required Anchors",
            "",
            *landmark_lines,
            "",
            "## Early Questions To Resolve",
            "",
            "- Which public data sources are allowed for shipped derivatives?",
            "- Which roads should be player-drivable, decorative only, or excluded?",
            "- Which farmyards/shops need openable placeables and gameplay triggers?",
            "- Which vegetation, crops, seasons, and economy assumptions are region-specific?",
            "",
            "## Next Commands",
            "",
            "```powershell",
            ".\\scripts\\fs25.ps1 status",
            ".\\scripts\\fs25.ps1 recommend",
            "```",
            "",
        ]
    )


def adoption_markdown(project: Path, signals: dict[str, object], results: list[WriteResult]) -> str:
    result_lines = [f"- {result.action}: `{result.path}`" for result in results]
    return "\n".join(
        [
            "# FS25 Project Adoption",
            "",
            "Generated by `fs25-adopt` / `project_setup.py`.",
            "",
            f"- Project path: `{project}`",
            f"- Git repo present: `{signals['has_git']}`",
            f"- Existing PowerShell wrapper: `{signals['has_wrapper_ps1']}`",
            f"- Existing Python wrapper: `{signals['has_wrapper_py']}`",
            f"- Profiles found: `{len(signals['profiles'])}`",
            f"- Build dirs found: `{len(signals['build_dirs'])}`",
            "",
            "## Files",
            "",
            *result_lines,
            "",
            "## Next Steps",
            "",
            "- Run `.\\scripts\\fs25.ps1 status`.",
            "- Replace the bootstrap wrapper with project-specific slices as deterministic generators and QA gates are added.",
            "- Keep raw/reference-only data out of shipped packages unless license provenance is explicit.",
            "",
        ]
    )


def add_common_args(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--project", type=Path, required=required, help="project directory")
    parser.add_argument("--project-name", required=required)
    parser.add_argument("--location", required=required, help="human-readable real-world location")
    parser.add_argument("--profile-id", help="profile id; defaults to slugified project name")
    parser.add_argument("--map-size-m", type=int, required=required)
    parser.add_argument("--center-lat", type=float, help="center latitude; optional if bbox is supplied")
    parser.add_argument("--center-lon", type=float, help="center longitude; optional if bbox is supplied")
    parser.add_argument("--bbox-wgs84-wsen", help="optional west,south,east,north override")
    parser.add_argument("--heightmap-max-m", type=int, default=1000)
    parser.add_argument("--terrain-height-scale-m", type=int)
    parser.add_argument("--preview-zip")
    parser.add_argument("--mods-dir")
    parser.add_argument("--landmark", action="append", help="repeat or separate landmarks with semicolons")
    parser.add_argument("--description")
    parser.add_argument("--force", action="store_true", help="overwrite generated files")


def run_init(args: argparse.Namespace) -> int:
    bbox, landmarks, profile_path = apply_defaults(args, "init")
    results = [
        write_json(args.project / profile_path, profile_payload(args, bbox), overwrite=args.force),
        write_json(args.project / ".fs25-map-builder.json", state_payload(args, profile_path, landmarks, "init", bbox), overwrite=args.force),
        write_file(args.project / "docs" / "fs25_project_brief.md", brief_markdown(args, bbox, landmarks), overwrite=args.force),
        *project_management_results(args.project, args, bbox, profile_path, mode="init", overwrite=args.force),
        *planning_results(args.project, args, bbox, landmarks, profile_path, mode="init", overwrite=args.force),
        write_file(args.project / "scripts" / "fs25.ps1", BOOTSTRAP_PS1, overwrite=args.force),
        write_file(args.project / "scripts" / "fs25.py", BOOTSTRAP_PY, overwrite=args.force),
    ]
    for directory in ("data/sources", "research", "build"):
        (args.project / directory).mkdir(parents=True, exist_ok=True)

    print(f"Initialized FS25 project scaffold: {args.project}")
    for result in results:
        print(f"{result.action}: {result.path}")
    return 0


def run_adopt(args: argparse.Namespace) -> int:
    bbox, landmarks, profile_path = apply_defaults(args, "adopt")
    args.project.mkdir(parents=True, exist_ok=True)
    signals = project_signals(args.project)

    results: list[WriteResult] = [
        write_json(args.project / ".fs25-map-builder.json", state_payload(args, profile_path, landmarks, "adopt", bbox), overwrite=args.force),
        write_json(args.project / profile_path, profile_payload(args, bbox), overwrite=args.force),
        write_file(args.project / "docs" / "fs25_project_brief.md", brief_markdown(args, bbox, landmarks), overwrite=args.force),
        *project_management_results(args.project, args, bbox, profile_path, mode="adopt", overwrite=args.force),
        *planning_results(args.project, args, bbox, landmarks, profile_path, mode="adopt", overwrite=args.force),
        write_file(args.project / "scripts" / "fs25.ps1", BOOTSTRAP_PS1, overwrite=args.force),
        write_file(args.project / "scripts" / "fs25.py", BOOTSTRAP_PY, overwrite=args.force),
    ]
    adoption_doc = adoption_markdown(args.project, signals, results)
    results.append(write_file(args.project / "docs" / "fs25_adoption.md", adoption_doc, overwrite=True))

    print(f"Adopted existing FS25 project: {args.project}")
    for result in results:
        print(f"{result.action}: {result.path}")
    return 0


def run_questions(args: argparse.Namespace) -> int:
    mode = args.mode
    print(f"FS25 {mode} questions:")
    print("1. What project folder/repo should be used?")
    print("2. What real-world location is the map centered on?")
    print("3. What center latitude/longitude or bbox should define the map?")
    print("4. What map size should be used, in meters?")
    print("5. Which landmarks, shops, farmyards, and public anchors must be represented?")
    print("6. Which data/license constraints or paid/public imagery sources are acceptable?")
    print("7. Where is the FS25 mods folder, if install automation should be enabled?")
    print("8. Should existing planning/state docs be preserved, or regenerated with --force?")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialize a new FS25 map project")
    add_common_args(init, required=True)
    init.set_defaults(func=run_init)
    adopt = sub.add_parser("adopt", help="attach FS25 Map Builder to an existing project")
    add_common_args(adopt, required=False)
    adopt.set_defaults(func=run_adopt)
    questions = sub.add_parser("questions", help="print the question set for an agent to ask")
    questions.add_argument("--mode", choices=("init", "adopt"), default="init")
    questions.set_defaults(func=run_questions)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
