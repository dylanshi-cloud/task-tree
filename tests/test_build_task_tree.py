#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for the task-tree generator."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "build_task_tree.py"
TEMPLATE = SKILL / "templates" / "tree.json"
EXAMPLE = SKILL / "examples" / "small-task.json"


def run(tree, vault, history, *extra):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--tree", str(tree),
         "--vault", str(vault), "--history", str(history), "--no-open", *extra],
        capture_output=True, encoding="utf-8", errors="replace",
    )


def load_template(tmp):
    cfg = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    path = tmp / "tree.json"
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return cfg, path


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.vault = self.root / "vault"
        self.history = self.root / "history.json"
        self.cfg, self.tree = load_template(self.root)
        self.out = self.vault / "50 任务树" / self.cfg["program"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_generates_root_branches_history_canvas_and_svg(self):
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.out / f'{self.cfg["title"]}.md').exists())
        self.assertTrue((self.out / f'{self.cfg["title"]} 演进.md').exists())
        self.assertFalse((self.out / "节点").exists())
        self.assertEqual(len(list(self.out.glob("* 生长.md"))), 0)
        self.assertEqual(len(list(self.out.glob("* 口径校准.md"))), 0)
        self.assertEqual(len(list(self.out.glob("* 演进时间线.md"))), 0)
        canvas = json.loads(next(self.out.glob("*.canvas")).read_text(encoding="utf-8"))
        ids = {n["id"] for n in canvas["nodes"]}
        self.assertTrue({"mission", "change", "home", "history", "algorithm"} <= ids)
        self.assertEqual(len(canvas["edges"]), 7)

    def test_small_task_generates_five_files(self):
        r = run(EXAMPLE, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = self.vault / "50 任务树" / "newsletter-launch"
        files = [p for p in out.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 5, sorted(p.name for p in files))

    def test_second_identical_run_does_not_append_snapshot(self):
        self.assertEqual(run(self.tree, self.vault, self.history).returncode, 0)
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("本轮无变化未追加", r.stdout)
        snaps = json.loads(self.history.read_text(encoding="utf-8"))["snapshots"]
        self.assertEqual(len(snaps), 1)

    def test_state_change_appends_snapshot_and_marks_node(self):
        self.assertEqual(run(self.tree, self.vault, self.history).returncode, 0)
        for n in self.cfg["nodes"]:
            if n["id"] == "B2":
                n["state"] = "partial"
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        snaps = json.loads(self.history.read_text(encoding="utf-8"))["snapshots"]
        self.assertEqual(len(snaps), 2)
        branch = next(self.out.glob("分支/B *.md")).read_text(encoding="utf-8")
        self.assertIn("🔄 本轮状态", branch)
        self.assertIn("### B2 域名与部署", branch)
        root = (self.out / f'{self.cfg["title"]}.md').read_text(encoding="utf-8")
        self.assertIn("未开始 → 推进中", root)
        self.assertIn("协同（这一轮）", root)

    def test_root_shows_algorithm_gate(self):
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        root = (self.out / f'{self.cfg["title"]}.md').read_text(encoding="utf-8")
        self.assertIn("## 算法关（删除与自动化）", root)
        self.assertIn("删除 2 项", root)
        self.assertIn("独立「关于」页", root)
        self.assertIn("还没有自动化项", root)

    def test_algorithm_gate_empty_state(self):
        self.cfg.pop("deleted", None)
        self.cfg.pop("automation", None)
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        root = (self.out / f'{self.cfg["title"]}.md').read_text(encoding="utf-8")
        self.assertIn("还没有删除记录", root)
        self.assertIn("删除 0 项", root)

    def test_duplicate_node_id_is_rejected(self):
        self.cfg["nodes"].append(dict(self.cfg["nodes"][0]))
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("节点 id 重复", r.stderr)

    def test_path_traversal_program_is_rejected(self):
        self.cfg["program"] = "../escape"
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.root / "escape").exists())

    def test_missing_branch_is_rejected(self):
        self.cfg["nodes"][0]["branch"] = "Z"
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("不在 branches 里", r.stderr)

    def test_slash_in_title_does_not_break_canvas(self):
        self.cfg["title"] = "Demo / Tree"
        self.tree.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(list(self.out.glob("Demo · Tree.canvas")))

    def test_canvas_open_uri_omits_extension(self):
        r = run(self.tree, self.vault, self.history)
        self.assertEqual(r.returncode, 0, r.stderr)
        uri = next(line for line in r.stdout.splitlines() if "obsidian://" in line)
        self.assertIn("file=50%20%E4%BB%BB", uri)
        self.assertNotIn(".canvas", uri)
        self.assertNotIn(".md", uri)

    def test_no_broken_wiki_links(self):
        self.assertEqual(run(self.tree, self.vault, self.history).returncode, 0)
        files = [p for p in self.vault.rglob("*") if p.is_file()]
        full = {p.relative_to(self.vault).as_posix().rsplit(".", 1)[0] for p in files}
        stems = {p.stem for p in files}
        names = {p.name for p in files}
        broken = []
        for p in self.vault.rglob("*.md"):
            for m in re.findall(r"\[\[([^\]|#]+)", p.read_text(encoding="utf-8")):
                target = m.strip()
                if target not in (full | stems | names):
                    broken.append((p.name, target))
        self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
