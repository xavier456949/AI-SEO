"""Observable installation, relocation, and packaging behavior (stdlib only)."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("openai_installer", ROOT / "install-codex.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class OpenAIInstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="seo install test ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_self_contained_bundle_and_workflow_links(self):
        target = installer.install(self.base / "skills")
        self.assertEqual(list(target.rglob("SKILL.md")), [target / "SKILL.md"])
        for relative in ("agents/openai.yaml", "requirements.txt", "LICENSE",
                         "scripts/runtime.py"):
            self.assertTrue((target / relative).is_file(), relative)
        for source in (ROOT / "data").glob("*.json"):
            self.assertEqual((target / "data" / source.name).read_bytes(), source.read_bytes())
        for source in (ROOT / "skills").glob("*/SKILL.md"):
            self.assertTrue((target / "skills" / source.parent.name / "WORKFLOW.md").is_file())
        for document in (target / "SKILL.md", target / "references/workflows.md"):
            links = re.findall(r"\]\(([^)]+)\)", document.read_text())
            for link in links:
                self.assertTrue((document.parent / link).is_file(), link)
        self.assertTrue((target / "skills/seo-schema/../seo/references/schema-types.md").is_file())
        self.assertTrue((target / "extensions/banana/skills/seo-image-gen/references/presets.md").is_file())
        for path in target.rglob("*.md"):
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", path.read_text(), str(path))

    def test_existing_install_is_preserved(self):
        target = installer.install(self.base)
        marker = target / "my-notes.txt"
        marker.write_text("preserve me")
        with self.assertRaises(FileExistsError):
            installer.install(self.base)
        self.assertEqual(marker.read_text(), "preserve me")

    def test_relocatable_archive_runtime(self):
        target = installer.install(self.base / "build")
        archive = self.base / "seo.zip"
        installer.archive_bundle(target, archive)
        extracted = self.base / "relocated package"
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            self.assertEqual([n for n in names if n.endswith("SKILL.md")], ["seo/SKILL.md"])
            self.assertFalse(any(".venv" in n or "setup_mcp" in n for n in names))
            bundle.extractall(extracted)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        result = subprocess.run([sys.executable, str(extracted / "seo/scripts/runtime.py"),
                                 "doctor", "--json"], cwd=self.base, env=env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 3, result.stderr)
        diagnosis = json.loads(result.stdout)
        self.assertFalse(diagnosis["ready"])
        self.assertEqual(diagnosis["mode"], "manual")
        self.assertNotEqual(diagnosis["plugin_version"], "unknown")

    def test_source_symlink_is_not_followed(self):
        source = self.base / "source"
        source.mkdir()
        (source / "private.md").symlink_to(ROOT / "README.md")
        with self.assertRaises(ValueError):
            installer.copy_resources(source, self.base / "output")

    def test_failed_build_does_not_create_installation(self):
        original = installer.build_bundle

        def broken_build(target):
            target.mkdir()
            raise ValueError("failed build")

        installer.build_bundle = broken_build
        try:
            with self.assertRaises(ValueError):
                installer.install(self.base)
        finally:
            installer.build_bundle = original
        self.assertFalse((self.base / "seo").exists())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_archive_does_not_overwrite(self):
        target = installer.install(self.base / "skills")
        archive = self.base / "existing.zip"
        archive.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            installer.archive_bundle(target, archive)
        self.assertEqual(archive.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
