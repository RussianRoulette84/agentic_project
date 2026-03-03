#!/usr/bin/env python3
"""
Bootstrap script: copy .agents/ and AGENTS.md into a target project.
For existing files: prompts to overwrite, skip, diff, or merge.
"""

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path


def prompt_for_file_action(src: Path, dest: Path) -> str:
    """Ask user what to do when dest file exists. Returns o|s|d|m|all-o|all-s."""
    while True:
        rel = dest.relative_to(dest.anchor) if dest.is_absolute() else dest
        print(f"\n  File exists: {rel}")
        print("  [O]verwrite  [S]kip  [D]iff  [M]erge (append)  [A]ll overwrite  [L]all skip: ", end="")
        choice = input().strip().lower()
        if choice in ("o", "s", "d", "m"):
            return choice
        if choice == "a":
            return "all-o"
        if choice == "l":
            return "all-s"
        print("  Invalid. Choose O, S, D, M, A, or L.")


def merge_markdown(src: Path, dest: Path) -> bool:
    """Append source content to dest with a separator. Returns True if merged."""
    try:
        dest_content = dest.read_text(encoding="utf-8", errors="replace")
        src_content = src.read_text(encoding="utf-8", errors="replace")
        separator = "\n\n---\n\n<!-- Merged from bootstrap -->\n\n"
        dest.write_text(dest_content + separator + src_content, encoding="utf-8")
        return True
    except OSError as e:
        print(f"  Error merging: {e}")
        return False


def run_diff(src: Path, dest: Path) -> bool:
    """Run diff/diff command. Returns True if diff available."""
    for cmd in (["diff", "-u", str(dest), str(src)], ["fc", "/N", str(dest), str(src)]):
        try:
            subprocess.run(cmd)
            return True
        except FileNotFoundError:
            continue
    print("  No diff tool found (diff or fc)")
    return False


def copy_file(
    src: Path,
    dest: Path,
    *,
    all_overwrite: bool = False,
    all_skip: bool = False,
    mergeable: bool = True,
) -> tuple[bool, bool, bool]:
    """
    Copy src to dest, prompting if dest exists.
    Returns (done, all_overwrite, all_skip) - latter two to update global flags.
    """
    if all_overwrite:
        shutil.copy2(src, dest)
        print(f"  Copied (overwrite): {dest}")
        return True, True, False

    if all_skip:
        print(f"  Skipped: {dest}")
        return True, False, True

    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"  Copied: {dest}")
        return True, False, False

    if filecmp.cmp(src, dest, shallow=False):
        print(f"  Unchanged (identical): {dest}")
        return True, False, False

    action = prompt_for_file_action(src, dest)
    if action == "all-o":
        shutil.copy2(src, dest)
        print(f"  Copied (overwrite): {dest}")
        return True, True, False
    if action == "all-s":
        print(f"  Skipped: {dest}")
        return True, False, True
    if action == "o":
        shutil.copy2(src, dest)
        print(f"  Copied (overwrite): {dest}")
        return True, False, False
    if action == "s":
        print(f"  Skipped: {dest}")
        return True, False, False
    if action == "d":
        run_diff(src, dest)
        return copy_file(src, dest, all_overwrite=False, all_skip=False, mergeable=mergeable)
    if action == "m" and mergeable and src.suffix.lower() in (".md", ".markdown"):
        if merge_markdown(src, dest):
            print(f"  Merged: {dest}")
        return True, False, False
    if action == "m":
        print("  Merge only supported for .md files. Choose O or S.")
        return copy_file(src, dest, all_overwrite=False, all_skip=False, mergeable=mergeable)

    return False, False, False


def bootstrap(source_dir: Path, dest_dir: Path) -> None:
    """Copy .agents/ and AGENTS.md from source to dest, with merge prompts."""
    dest_dir = dest_dir.resolve()
    source_dir = source_dir.resolve()

    if not source_dir.is_dir():
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)

    agents_src = source_dir / ".agents"
    agents_md_src = source_dir / "AGENTS.md"

    if not agents_src.is_dir():
        print(f"Error: No .agents/ directory in source: {source_dir}")
        sys.exit(1)
    if not agents_md_src.is_file():
        print(f"Error: No AGENTS.md in source: {source_dir}")
        sys.exit(1)

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)
        print(f"Created destination: {dest_dir}")

    all_overwrite = False
    all_skip = False

    # 1. Copy AGENTS.md
    agents_md_dest = dest_dir / "AGENTS.md"
    print("\n--- AGENTS.md ---")
    _, ao, as_ = copy_file(
        agents_md_src, agents_md_dest, all_overwrite=all_overwrite, all_skip=all_skip, mergeable=True
    )
    all_overwrite |= ao
    all_skip |= as_

    # 2. Copy .agents/ recursively
    print("\n--- .agents/ ---")
    for src_path in sorted(agents_src.rglob("*")):
        if src_path.is_dir():
            continue
        rel = src_path.relative_to(agents_src)
        dest_path = dest_dir / ".agents" / rel
        _, ao, as_ = copy_file(
            src_path, dest_path, all_overwrite=all_overwrite, all_skip=all_skip, mergeable=True
        )
        all_overwrite |= ao
        all_skip |= as_

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="Copy .agents/ and AGENTS.md into a target project. Prompts when files exist."
    )
    parser.add_argument(
        "dest",
        type=Path,
        help="Destination project directory (folder path)",
    )
    parser.add_argument(
        "-s",
        "--source",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Source directory containing .agents/ and AGENTS.md (default: project root)",
    )
    args = parser.parse_args()
    bootstrap(args.source, args.dest)


if __name__ == "__main__":
    main()
