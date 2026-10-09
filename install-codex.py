#!/usr/bin/env python3
"""Build/install this checkout as one self-contained OpenAI SEO skill.

Standard library only. Deliberately separate from the upstream Claude installer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP = {"__pycache__", ".venv", "node_modules", ".git", ".DS_Store"}
SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".html", ".txt", ".svg"}


def adapt_markdown(text: str) -> str:
    """Keep relative topology; replace Claude launcher/path assumptions."""
    text = text.replace('"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo"',
                        'python3 "<SEO_ROOT>/scripts/runtime.py"')
    text = text.replace('${CLAUDE_PLUGIN_ROOT}', '<SEO_ROOT>')
    text = text.replace('SKILL.md', 'WORKFLOW.md')
    return text


def copy_resources(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in SKIP or part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Refusing symlink in package resources: {path}")
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        # Do not distribute host-specific installers, credential setup, or artifacts.
        if path.name in {"setup_mcp.py"} or path.name.startswith(("install.", "uninstall.")):
            continue
        dest = target / relative
        if path.name == "SKILL.md":
            dest = dest.with_name("WORKFLOW.md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            text = path.read_text(encoding="utf-8")
            if path.name == "SKILL.md" or source.name == "agents":
                text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
            dest.write_text(adapt_markdown(text), encoding="utf-8")
        else:
            shutil.copy2(path, dest)


def build_bundle(target: Path) -> None:
    shutil.copytree(ROOT / "openai" / "seo", target)
    for folder in ("skills", "scripts", "agents", "schema", "data"):
        copy_resources(ROOT / folder, target / folder)
    for extension in sorted((ROOT / "extensions").iterdir()):
        if not extension.is_dir():
            continue
        for folder in ("skills", "scripts", "agents", "references", "docs"):
            copy_resources(extension / folder, target / "extensions" / extension.name / folder)
        # Extension skills sometimes rely on references shipped in the core mirror.
        for skill in (extension / "skills").glob("*"):
            dest = target / "extensions" / extension.name / "skills" / skill.name / "references"
            copy_resources(ROOT / "skills" / skill.name / "references", dest)
            copy_resources(extension / "references", dest)
    for name in ("LICENSE", "requirements.txt"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copy2(ROOT / ".claude-plugin" / "plugin.json", target / "runtime-plugin.json")
    # Preserve the legacy launcher for scripts which mention it internally.
    shutil.copy2(ROOT / "scripts" / "claude-seo", target / "scripts" / "claude-seo")
    workflows = sorted(target.glob("skills/*/WORKFLOW.md"))
    workflows += sorted(target.glob("extensions/*/skills/*/WORKFLOW.md"))
    lines = ["# SEO workflows", "", "Read only the workflow relevant to the request.", ""]
    for path in workflows:
        name = path.parent.name
        label = name + (" (optional provider)" if "extensions" in path.relative_to(target).parts else "")
        lines.append(f"- [{label}](../{path.relative_to(target).as_posix()})")
    refs = target / "references"
    refs.mkdir(exist_ok=True)
    (refs / "workflows.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Exactly one discovery manifest; nested procedures are reference documents.
    manifests = list(target.rglob("SKILL.md"))
    if manifests != [target / "SKILL.md"]:
        raise ValueError("Bundle must contain exactly one SKILL.md")
    (target / "openai-install.json").write_text(json.dumps({
        "format": 1, "source": "xavier456949/AI-SEO", "workflows": len(workflows),
    }, indent=2) + "\n", encoding="utf-8")


def install(destination: Path) -> Path:
    destination = destination.expanduser().resolve()
    target = destination / "seo"
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Skill already exists: {target}. Choose another --dest or back it up first.")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".seo-build-", dir=destination) as temporary:
        staged = Path(temporary) / "seo"
        build_bundle(staged)
        staged.rename(target)
    return target


def archive_bundle(target: Path, archive: Path) -> None:
    archive = archive.expanduser().resolve()
    if archive.is_relative_to(target):
        raise ValueError("Archive must be outside the skill directory")
    archive.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids overwriting an unrelated existing archive.
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(target.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(target.parent).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    parser.add_argument("--dest", type=Path, default=default,
                        help="Skills parent directory (default: $CODEX_HOME/skills or ~/.codex/skills)")
    parser.add_argument("--archive", type=Path, help="Also create a portable ZIP, before runtime setup")
    parser.add_argument("--setup", action="store_true", help="Install isolated Python dependencies and Chromium")
    parser.add_argument("--skip-browser", action="store_true", help="With --setup, skip Chromium")
    args = parser.parse_args()
    if args.skip_browser and not args.setup:
        parser.error("--skip-browser requires --setup")
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required; invoke this installer with a newer interpreter")
    try:
        target = install(args.dest)
        print(f"Installed SEO skill: {target}", flush=True)
        if args.archive:
            archive_bundle(target, args.archive)
            print(f"Portable bundle: {args.archive.resolve()}", flush=True)
        if args.setup:
            command = [sys.executable, str(target / "scripts" / "runtime.py"), "setup"]
            if args.skip_browser:
                command.append("--skip-browser")
            status = subprocess.run(command).returncode
            if status:
                print("Skill files are installed, but runtime setup is incomplete. Retry runtime.py setup.",
                      file=sys.stderr)
                return status
        print("Available on your next turn. Try: $seo audit https://example.com")
        return 0
    except (OSError, ValueError) as exc:
        print(f"SEO installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
