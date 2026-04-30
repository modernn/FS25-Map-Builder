#!/usr/bin/env python3
"""Simple command router for the Focused Butte FS25 map pipeline."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.map_profile import load_profile  # noqa: E402

DEFAULT_PROFILE = Path("profiles/focused_butte_4km.json")
DEFAULT_MODS_DIR = Path(
    r"C:\Users\Dad\AppData\Local\Packages\GIANTSSoftware.FarmingSimulator25PC_fa8jxm5fj0esw\LocalCache\Local\mods"
)


@dataclass(frozen=True)
class Slice:
    name: str
    title: str
    purpose: str
    commands: tuple[tuple[str, ...], ...]
    outputs: tuple[str, ...]
    automated: bool = True


def py_cmd(*args: str) -> tuple[str, ...]:
    return ("{python}", *args)


SLICES: tuple[Slice, ...] = (
    Slice(
        "source-reference",
        "Source/reference snapshot",
        "Verify source manifests and refresh current imagery references.",
        (
            py_cmd("scripts/verify_manifest.py", "--also", "research/MANIFEST.tsv:research"),
            py_cmd(
                "scripts/discover_reference_imagery.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--date-range",
                "2025-05-01T00:00:00Z/2026-04-30T23:59:59Z",
                "--max-cloud",
                "30",
                "--limit",
                "10",
                "--export-matsu-preview",
            ),
        ),
        (
            "docs/reference_imagery_sources.md",
            "research/reference_imagery/reference_imagery_candidates.json",
        ),
    ),
    Slice(
        "terrain-heightmap",
        "Heightmap bake",
        "Bake the focused 4 km DEM heightmap.",
        (
            py_cmd(
                "scripts/bake_heightmap.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--size",
                "2049",
                "--out",
                "data/derived/focused_butte_4km_heightmap_2049.png",
                "--force",
            ),
        ),
        ("data/derived/focused_butte_4km_heightmap_2049.png",),
    ),
    Slice(
        "terrain-relief",
        "Local relief bake",
        "Enhance the Butte relief from the focused heightmap.",
        (py_cmd("scripts/enhance_butte_terrain.py", "--profile", "profiles/focused_butte_4km.json"),),
        ("data/derived/focused_butte_4km_heightmap_2049_butte_relief.png",),
    ),
    Slice(
        "base-map",
        "Base Maps4FS project",
        "Generate the base focused map project from the enhanced DEM.",
        (
            py_cmd(
                "scripts/generate_maps4fs.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--custom-dem",
                "data/derived/focused_butte_4km_heightmap_2049_butte_relief.png",
            ),
        ),
        ("build/focused_butte_4km/map/map.i3d", "build/focused_butte_4km/map/map.xml"),
    ),
    Slice(
        "fields-geometry",
        "Fields and farmlands",
        "Bake playable field geometry, field XML, farmlands, and the field audit.",
        (
            py_cmd(
                "scripts/bake_playable_fields.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--map-dir",
                "build/focused_butte_4km",
            ),
            py_cmd(
                "scripts/bake_fields_xml.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--map-dir",
                "build/focused_butte_4km",
            ),
            py_cmd(
                "scripts/audit_focused_fields.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--map-dir",
                "build/focused_butte_4km",
                "--field-layout",
                "docs/field_layout.md",
                "--doc",
                "docs/field_parcel_audit.md",
                "--preview",
                "docs/visual_previews/field_parcel_audit.png",
            ),
        ),
        ("docs/field_parcel_audit.md",),
    ),
    Slice(
        "fields-surface",
        "Visible field surfaces",
        "Bake visible field/crop surfaces and rerun the field audit.",
        (
            py_cmd(
                "scripts/bake_visible_field_surfaces.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--map-dir",
                "build/focused_butte_4km",
                "--field-layout",
                "docs/field_layout.md",
                "--doc",
                "docs/visible_field_surfaces.md",
            ),
            py_cmd(
                "scripts/audit_focused_fields.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--map-dir",
                "build/focused_butte_4km",
                "--field-layout",
                "docs/field_layout.md",
                "--doc",
                "docs/field_parcel_audit.md",
                "--preview",
                "docs/visual_previews/field_parcel_audit.png",
            ),
        ),
        ("docs/visible_field_surfaces.md", "docs/field_parcel_audit.md"),
    ),
    Slice(
        "roads-paint",
        "Road texture paint",
        "Paint the clean core road masks and audit the raster output.",
        (
            py_cmd(
                "scripts/bake_road_textures.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--no-access",
                "--no-public-local",
                "--include-essential-locals",
            ),
            py_cmd(
                "scripts/audit_road_texture_outputs.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--doc",
                "docs/road_texture_audit.md",
                "--full-preview",
                "docs/visual_previews/road_texture_audit_graded.png",
                "--zoom-preview",
                "docs/visual_previews/road_texture_audit_graded_zooms.jpg",
            ),
        ),
        ("docs/road_texture_audit.md",),
    ),
    Slice(
        "roads-grade",
        "Road terrain grading",
        "Smooth drivable road centerlines and rerun the road raster audit.",
        (
            py_cmd(
                "scripts/grade_road_terrain.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--input",
                "data/derived/focused_butte_4km_heightmap_2049_butte_relief.png",
                "--no-access",
                "--no-public-local",
                "--include-essential-locals",
                "--smooth-window-m",
                "220",
                "--max-grade",
                "0.02",
                "--edge-blend-m",
                "12",
                "--center-radius-m",
                "14",
                "--max-adjust-m",
                "12",
                "--post-smooth-passes",
                "4",
                "--apply-build",
            ),
            py_cmd(
                "scripts/audit_road_texture_outputs.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--doc",
                "docs/road_texture_audit.md",
                "--full-preview",
                "docs/visual_previews/road_texture_audit_graded.png",
                "--zoom-preview",
                "docs/visual_previews/road_texture_audit_graded_zooms.jpg",
            ),
        ),
        ("docs/road_terrain_grading.md", "docs/road_texture_audit.md"),
    ),
    Slice(
        "region-config",
        "Region systems audit",
        "Audit crops, calendar, economy, and Alaska-region assumptions.",
        (
            py_cmd(
                "scripts/audit_region_systems.py",
                "--profile",
                "profiles/focused_butte_region.json",
                "--doc",
                "docs/region_systems.md",
            ),
        ),
        ("docs/region_systems.md",),
    ),
    Slice(
        "landscape-foliage",
        "Landscape, foliage, and trees",
        "Bake visible Alaska-proxy vegetation and rerun the landscape QA gate.",
        (
            py_cmd(
                "scripts/bake_focused_landscape.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--doc",
                "docs/landscape_visible_bake.md",
            ),
            py_cmd(
                "scripts/audit_landscape_visible_qa.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--doc",
                "docs/landscape_visible_qa.md",
                "--preview",
                "docs/visual_previews/landscape_visible_qa.png",
            ),
        ),
        ("docs/landscape_visible_bake.md", "docs/landscape_visible_qa.md"),
    ),
    Slice(
        "placeables",
        "Landmarks, shops, and farmyards",
        "Bake visible landmark/shop/farmyard placeables from stock assets.",
        (
            py_cmd(
                "scripts/bake_visible_landmark_placeables.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--require-stock-assets",
            ),
        ),
        ("docs/visible_landmark_placeables.md", "build/focused_butte_4km/map/config/placeables.xml"),
    ),
    Slice(
        "bounds-references",
        "Map bounds and local references",
        "Fix map-edge collision references and local package references.",
        (
            py_cmd("scripts/fix_preview_map_boundaries.py"),
            py_cmd(
                "scripts/fix_preview_local_references.py",
                "--map-dir",
                "build/focused_butte_4km",
                "--doc",
                "docs/local_reference_fixes.md",
            ),
        ),
        ("docs/local_reference_fixes.md", "build/focused_butte_4km/assets/map_bounds/map_bounds.i3d"),
    ),
    Slice(
        "package",
        "Package and static QA",
        "Package the preview zip and run package/player-visible QA.",
        (
            py_cmd("scripts/fix_preview_map_boundaries.py"),
            py_cmd(
                "scripts/fix_preview_local_references.py",
                "--map-dir",
                "build/focused_butte_4km",
                "--doc",
                "docs/local_reference_fixes.md",
            ),
            py_cmd(
                "scripts/package_preview_zip.py",
                "--root",
                "build/focused_butte_4km",
                "--out",
                "build/FS25_FocusedButte_4km_preview.zip",
            ),
            py_cmd(
                "scripts/audit_preview_package.py",
                "--zip",
                "build/FS25_FocusedButte_4km_preview.zip",
                "--doc",
                "docs/package_license_audit.md",
            ),
            py_cmd(
                "scripts/audit_player_visible_qa.py",
                "--profile",
                "profiles/focused_butte_4km.json",
                "--zip",
                "build/FS25_FocusedButte_4km_preview.zip",
                "--doc",
                "docs/player_visible_qa.md",
            ),
        ),
        ("build/FS25_FocusedButte_4km_preview.zip", "docs/package_license_audit.md", "docs/player_visible_qa.md"),
    ),
    Slice(
        "install-prep",
        "Install preview zip",
        "Copy the preview zip to the known FS25 mods folder and verify SHA256.",
        (),
        ("build/FS25_FocusedButte_4km_preview.zip",),
    ),
    Slice(
        "human-test",
        "Morning FS25 human verification",
        "Run the in-game load, drive, boundary, field, save, and performance checklist.",
        (),
        ("docs/morning_human_verification.md",),
        automated=False,
    ),
)

SLICE_BY_NAME = {slice_.name: slice_ for slice_ in SLICES}


def repo_path(path: str | Path) -> Path:
    return Path(path)


def read_text_if_exists(path: str | Path) -> str:
    file_path = repo_path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def doc_passes(path: str | Path, pass_markers: tuple[str, ...] = ("PASS", "passed")) -> bool:
    text = read_text_if_exists(path)
    if not text:
        return False
    if "Result: FAIL" in text or "Verdict: `FAIL`" in text or "Package audit: FAIL" in text:
        return False
    return any(marker in text for marker in pass_markers)


def file_exists(path: str | Path) -> bool:
    return repo_path(path).exists()


REQUIRED_LOCAL_REFERENCE_MASKS = (
    "GEN_forestBorders.png",
    "GEN_forestUPDT.png",
    "GEN_meadowUPDT.png",
    "GEN_roadsMask.png",
    "GEN_slopeMask.png",
    "PG_bushLand.png",
    "PG_forest.png",
    "PG_meadow.png",
)


def translation_for_named_node(text: str, tag: str, name: str) -> str | None:
    pattern = rf'<{tag}\b[^>]*\bname="{re.escape(name)}"[^>]*\btranslation="([^"]+)"'
    match = re.search(pattern, text)
    if not match:
        return None
    return " ".join(match.group(1).split())


def zip_matches_install(profile_zip: Path, mods_dir: Path) -> bool:
    installed = mods_dir / profile_zip.name
    if not profile_zip.exists() or not installed.exists():
        return False
    return sha256(profile_zip) == sha256(installed)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


GateFn = Callable[[Path], bool]


def gate_source(_: Path) -> bool:
    return file_exists("docs/reference_imagery_sources.md") and file_exists(
        "research/reference_imagery/reference_imagery_candidates.json"
    )


def gate_heightmap(_: Path) -> bool:
    return file_exists("data/derived/focused_butte_4km_heightmap_2049.png")


def gate_relief(_: Path) -> bool:
    return file_exists("data/derived/focused_butte_4km_heightmap_2049_butte_relief.png")


def gate_base(profile_path: Path) -> bool:
    profile = load_profile(profile_path)
    return (profile.build_dir / "map" / "map.i3d").exists() and (profile.build_dir / "map" / "map.xml").exists()


def gate_fields(_: Path) -> bool:
    return doc_passes("docs/field_parcel_audit.md", ("PASS", "no_blockers"))


def gate_field_surface(_: Path) -> bool:
    return file_exists("docs/visible_field_surfaces.md") and gate_fields(DEFAULT_PROFILE)


def gate_roads_paint(_: Path) -> bool:
    text = read_text_if_exists("docs/road_texture_audit.md")
    return bool(re.search(r"blocking road conflicts:\s*`?0`?", text, flags=re.IGNORECASE))


def gate_roads_grade(_: Path) -> bool:
    return file_exists("docs/road_terrain_grading.md") and gate_roads_paint(DEFAULT_PROFILE)


def gate_region(_: Path) -> bool:
    return file_exists("docs/region_systems.md")


def gate_landscape(_: Path) -> bool:
    return doc_passes("docs/landscape_visible_qa.md", ("Result: PASS", "PASS"))


def gate_placeables(_: Path) -> bool:
    return file_exists("docs/visible_landmark_placeables.md") and file_exists(
        "build/focused_butte_4km/map/config/placeables.xml"
    )


def gate_bounds(profile_path: Path) -> bool:
    profile = load_profile(profile_path)
    map_i3d = profile.build_dir / "map" / "map.i3d"
    bounds_i3d = profile.build_dir / "assets" / "map_bounds" / "map_bounds.i3d"
    masks_dir = profile.build_dir / "map" / "data" / "masks"
    if not file_exists("docs/local_reference_fixes.md") or not map_i3d.exists() or not bounds_i3d.exists():
        return False
    if not all((masks_dir / name).exists() for name in REQUIRED_LOCAL_REFERENCE_MASKS):
        return False
    map_text = map_i3d.read_text(encoding="utf-8", errors="replace")
    bounds_text = bounds_i3d.read_text(encoding="utf-8", errors="replace")
    return (
        'externalShapesFile="map.i3d.shapes"' not in map_text
        and translation_for_named_node(map_text, "ReferenceNode", "mapbounds") == "0 0 0"
        and translation_for_named_node(bounds_text, "TransformGroup", "mapbounds") == "0 0 0"
    )


def gate_package(profile_path: Path) -> bool:
    from scripts.audit_preview_package import audit_zip

    profile = load_profile(profile_path)
    if not profile.preview_zip.exists():
        return False
    package_inputs = [
        profile.build_dir / "map" / "map.i3d",
        profile.build_dir / "map" / "map.xml",
        profile.build_dir / "map" / "data" / "dem.png",
        profile.build_dir / "background" / "FULL.png",
        profile.build_dir / "map" / "config" / "placeables.xml",
        profile.build_dir / "assets" / "map_bounds" / "map_bounds.i3d",
        profile.build_dir / "assets" / "map_bounds" / "map_bounds.i3d.shapes",
    ]
    package_inputs.extend(
        profile.build_dir / "map" / "data" / "masks" / name for name in REQUIRED_LOCAL_REFERENCE_MASKS
    )
    existing_inputs = [path for path in package_inputs if path.exists()]
    if existing_inputs and profile.preview_zip.stat().st_mtime < max(path.stat().st_mtime for path in existing_inputs):
        return False
    zip_audit = audit_zip(profile.preview_zip)
    return (
        bool(zip_audit.get("exists")) and not zip_audit.get("problems")
        and gate_bounds(profile_path)
        and doc_passes("docs/package_license_audit.md", ("Package audit: PASS", "Manifest/license audit: PASS"))
        and doc_passes("docs/player_visible_qa.md", ("Result: PASS", "PASS"))
    )


def mods_dir() -> Path:
    override = os.environ.get("FS25_MODS_DIR")
    return Path(override) if override else DEFAULT_MODS_DIR


def gate_install(profile_path: Path) -> bool:
    profile = load_profile(profile_path)
    return zip_matches_install(profile.preview_zip, mods_dir())


GATES: dict[str, GateFn] = {
    "source-reference": gate_source,
    "terrain-heightmap": gate_heightmap,
    "terrain-relief": gate_relief,
    "base-map": gate_base,
    "fields-geometry": gate_fields,
    "fields-surface": gate_field_surface,
    "roads-paint": gate_roads_paint,
    "roads-grade": gate_roads_grade,
    "region-config": gate_region,
    "landscape-foliage": gate_landscape,
    "placeables": gate_placeables,
    "bounds-references": gate_bounds,
    "package": gate_package,
    "install-prep": gate_install,
    "human-test": lambda _: False,
}


def render_command(command: tuple[str, ...]) -> str:
    parts = [r".\.venv\Scripts\python.exe" if part == "{python}" else part for part in command]
    rendered: list[str] = []
    for part in parts:
        if any(char.isspace() for char in part):
            rendered.append(f'"{part}"')
        else:
            rendered.append(part)
    return " ".join(rendered)


def slice_passes(slice_: Slice, profile_path: Path) -> bool:
    gate = GATES.get(slice_.name)
    if gate is None:
        return all(file_exists(output) for output in slice_.outputs)
    return gate(profile_path)


def first_recommendation(profile_path: Path) -> Slice:
    for slice_ in SLICES:
        if not slice_passes(slice_, profile_path):
            return slice_
    return SLICE_BY_NAME["human-test"]


def print_slice(slice_: Slice, *, include_commands: bool = True) -> None:
    status = "automated" if slice_.automated else "human"
    print(f"{slice_.name} - {slice_.title} ({status})")
    print(f"  {slice_.purpose}")
    if slice_.outputs:
        print("  outputs:")
        for output in slice_.outputs:
            print(f"    - {output}")
    if include_commands and slice_.commands:
        print("  commands:")
        for command in slice_.commands:
            print(f"    {render_command(command)}")


def cmd_list(_: argparse.Namespace) -> int:
    print("Available FS25 slices:")
    for slice_ in SLICES:
        print_slice(slice_, include_commands=False)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    profile = load_profile(profile_path)
    recommendation = first_recommendation(profile_path)

    print("FS25 Focused Butte status")
    print(f"  profile: {profile_path}")
    print(f"  build:   {profile.build_dir} ({'exists' if profile.build_dir.exists() else 'missing'})")
    print(f"  zip:     {profile.preview_zip} ({'exists' if profile.preview_zip.exists() else 'missing'})")
    print(f"  mods:    {mods_dir()}")
    if profile.preview_zip.exists():
        print(f"  zip sha: {sha256(profile.preview_zip)}")
    print("")
    print("Slice gates:")
    for slice_ in SLICES:
        if slice_.name == "human-test":
            continue
        marker = "PASS" if slice_passes(slice_, profile_path) else "NEXT" if slice_.name == recommendation.name else "TODO"
        print(f"  {marker:4} {slice_.name}")
    print("")
    print("Recommended next command:")
    print(f"  .\\scripts\\fs25.ps1 start")
    print("")
    print_slice(recommendation)
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    recommendation = first_recommendation(profile_path)
    print("Recommended next FS25 command:")
    if recommendation.automated:
        print(f"  .\\scripts\\fs25.ps1 run {recommendation.name}")
        print("")
        print("Or just run:")
        print("  .\\scripts\\fs25.ps1 start")
    else:
        print("  Open FS25 and follow docs\\morning_human_verification.md")
    print("")
    print_slice(recommendation)
    print("")
    print("Useful commands:")
    print("  .\\scripts\\fs25.ps1 status")
    print("  .\\scripts\\fs25.ps1 list")
    print("  .\\scripts\\fs25.ps1 run <slice-name>")
    print("  .\\scripts\\fs25.ps1 start --all")
    print("  .\\scripts\\fs25.ps1 install")
    return 0


def run_command(command: tuple[str, ...], dry_run: bool) -> int:
    rendered = render_command(command)
    print(f"> {rendered}")
    if dry_run:
        return 0
    resolved = [sys.executable if part == "{python}" else part for part in command]
    completed = subprocess.run(resolved, check=False)
    return completed.returncode


def run_slice(slice_: Slice, dry_run: bool) -> int:
    if not slice_.automated:
        print(f"{slice_.name} is a human gate:")
        print_slice(slice_)
        return 2
    if slice_.name == "install-prep":
        return install_preview(dry_run=dry_run)
    print(f"Running slice: {slice_.name} - {slice_.title}")
    for command in slice_.commands:
        result = run_command(command, dry_run=dry_run)
        if result != 0:
            print(f"FAILED: {slice_.name} stopped at exit code {result}")
            return result
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    slice_ = SLICE_BY_NAME.get(args.slice)
    if slice_ is None:
        print(f"Unknown slice: {args.slice}")
        print("Run .\\scripts\\fs25.ps1 list")
        return 2
    return run_slice(slice_, dry_run=args.dry_run)


def cmd_start(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    while True:
        recommendation = first_recommendation(profile_path)
        if not recommendation.automated:
            print("Next gate is human verification.")
            print("Open FS25 and follow docs\\morning_human_verification.md")
            return 0
        result = run_slice(recommendation, dry_run=args.dry_run)
        if result != 0:
            return result
        if args.dry_run:
            return 0
        if not args.dry_run and not slice_passes(recommendation, profile_path):
            print(f"FAILED: {recommendation.name} command finished, but its gate still does not pass.")
            return 1
        if not args.all:
            return result


def install_preview(*, dry_run: bool = False) -> int:
    profile = load_profile(DEFAULT_PROFILE)
    source = profile.preview_zip
    destination_dir = mods_dir()
    destination = destination_dir / source.name
    if not source.exists():
        print(f"Missing preview zip: {source}")
        return 2
    print(f"> copy {source} -> {destination}")
    if dry_run:
        return 0
    destination_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = sha256(source)
    destination_hash = sha256(destination)
    print(f"source sha:      {source_hash}")
    print(f"installed sha:   {destination_hash}")
    if source_hash != destination_hash:
        print("FAILED: installed zip hash mismatch")
        return 1
    print("Installed preview zip to FS25 mods folder.")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    return install_preview(dry_run=args.dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple FS25 Focused Butte command launcher.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE), help="map profile JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show current gates and the next recommendation")
    status.set_defaults(func=cmd_status)

    recommend = subparsers.add_parser("recommend", aliases=["next"], help="show what command should be run next")
    recommend.set_defaults(func=cmd_recommend)

    list_cmd = subparsers.add_parser("list", help="list available slices")
    list_cmd.set_defaults(func=cmd_list)

    run = subparsers.add_parser("run", help="run one named automated slice")
    run.add_argument("slice", choices=tuple(SLICE_BY_NAME.keys()))
    run.add_argument("--dry-run", action="store_true", help="print commands without running them")
    run.set_defaults(func=cmd_run)

    start = subparsers.add_parser("start", help="run the recommended next automated slice")
    start.add_argument("--all", action="store_true", help="keep running recommended automated slices until a failure or human gate")
    start.add_argument("--dry-run", action="store_true", help="print commands without running them")
    start.set_defaults(func=cmd_start)

    install = subparsers.add_parser("install", help="copy the preview zip to the FS25 mods folder")
    install.add_argument("--dry-run", action="store_true", help="print copy action without running it")
    install.set_defaults(func=cmd_install)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
