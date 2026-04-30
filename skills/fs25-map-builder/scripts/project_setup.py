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


DEFAULT_PHASES = (
    "source-reference",
    "terrain-heightmap",
    "base-map",
    "roads",
    "fields",
    "landmarks-shops-farmyards",
    "vegetation-landscape",
    "region-systems",
    "package",
    "human-test",
)


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
    print("  Turn docs/fs25_project_brief.md into the first deterministic source/reference slice.")
    print("")
    print("Useful commands:")
    print("  .\\scripts\\fs25.ps1 status")
    print("  .\\scripts\\fs25.ps1 list")
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
    preview_zip = args.preview_zip or f"build/FS25_{args.profile_id}_preview.zip"
    return {
        "profile_id": args.profile_id,
        "description": args.description or f"{args.project_name} FS25 map",
        "map_size_m": args.map_size_m,
        "heightmap_max_m": args.heightmap_max_m,
        "terrain_height_scale_m": args.terrain_height_scale_m or args.heightmap_max_m,
        "bbox_wgs84_wsen": list(bbox),
        "center_wgs84_lat_lon": [args.center_lat, args.center_lon],
        "build_dir": f"build/{args.profile_id}",
        "preview_zip": preview_zip,
    }


def state_payload(args: argparse.Namespace, profile_path: Path, landmarks: list[str], mode: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "fs25-map-builder.project.v1",
        "mode": mode,
        "project_name": args.project_name,
        "location": args.location,
        "map_size_m": args.map_size_m,
        "profile_path": str(profile_path).replace("\\", "/"),
        "preview_zip": args.preview_zip or f"build/FS25_{args.profile_id}_preview.zip",
        "mods_dir": args.mods_dir or "",
        "landmarks": landmarks,
        "phases": list(DEFAULT_PHASES),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    return payload


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
        write_json(args.project / ".fs25-map-builder.json", state_payload(args, profile_path, landmarks, "init"), overwrite=args.force),
        write_file(args.project / "docs" / "fs25_project_brief.md", brief_markdown(args, bbox, landmarks), overwrite=args.force),
        write_file(args.project / "docs" / "morning_human_verification.md", "# Morning Human Verification\n\n- TODO: add load, drive, boundary, field, save/reload, and performance checklist.\n", overwrite=args.force),
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

    results: list[WriteResult] = []
    if not (args.project / ".fs25-map-builder.json").exists() or args.force:
        results.append(write_json(args.project / ".fs25-map-builder.json", state_payload(args, profile_path, landmarks, "adopt"), overwrite=args.force))
    if not (args.project / profile_path).exists() or args.force:
        results.append(write_json(args.project / profile_path, profile_payload(args, bbox), overwrite=args.force))
    if not (args.project / "docs" / "fs25_project_brief.md").exists() or args.force:
        results.append(write_file(args.project / "docs" / "fs25_project_brief.md", brief_markdown(args, bbox, landmarks), overwrite=args.force))
    if not (args.project / "scripts" / "fs25.ps1").exists() or args.force:
        results.append(write_file(args.project / "scripts" / "fs25.ps1", BOOTSTRAP_PS1, overwrite=args.force))
    if not (args.project / "scripts" / "fs25.py").exists() or args.force:
        results.append(write_file(args.project / "scripts" / "fs25.py", BOOTSTRAP_PY, overwrite=args.force))
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
