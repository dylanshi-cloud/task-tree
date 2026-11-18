#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一棵 tree.json 渲染成 Obsidian 只读任务树。

用法:
    python3 build_task_tree.py --tree .task-tree/tree.json [--vault <Obsidian库>] [--dry] [--no-open]

输出:
    <vault>/50 任务树/<program>/
      <title>.md          根页：为什么做 / 给谁用 / 什么算成功 / 当前态势
      分支/<id> <name>.md
      节点/<id> <title>.md
      <title> 口径校准.md
      <title> 演进时间线.md
      <title> 生长.md + <title> 生长.svg
      <title>.canvas

原则: tree.json 是唯一真相；本脚本只读它，页面是只读镜像。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

TODAY = date.today().isoformat()
STATE_LABEL = {
    "done": "已定", "partial": "推进中", "open": "未开始",
    "decide": "待拍板", "blocked": "受阻", "later": "后置",
}
STATE_ORDER = {"decide": 0, "blocked": 1, "partial": 2, "open": 3, "later": 4, "done": 5}
STATE_COLOR = {"decide": "1", "blocked": "1", "partial": "2", "open": "6", "later": "6", "done": "4"}
STATE_BADGE = {
    "done": "🟢 已定", "partial": "🟡 推进中", "open": "⚪ 未开始",
    "decide": "🔴 待拍板", "blocked": "⛔ 受阻", "later": "🔵 后置",
}
GROWTH_COLORS = {
    "done": "#34d399", "partial": "#fbbf24", "open": "#94a3b8",
    "blocked": "#ef4444", "later": "#60a5fa", "decide": "#ec4899",
}
GROWTH_STACK = ["done", "partial", "decide", "blocked", "open", "later"]


def clean(text, limit=None):
    s = re.sub(r"\s+", " ", (text or "")).strip()
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s


def cell(text, limit=90):
    return clean(text, limit).replace("|", "\\|")


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "·", name)


def worst(states):
    states = [s for s in states if s]
    if not states:
        return "open"
    return sorted(states, key=lambda s: STATE_ORDER.get(s, 9))[0]


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def safe_program(name):
    p = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name or "").strip()).strip(".-")
    return p or "task"


def validate_cfg(cfg):
    errors, warnings = [], []
    program = cfg.get("program")
    if not program or not str(program).strip():
        errors.append("program 为空")
    elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", str(program)):
        errors.append(f'program 只能含字母、数字、._-，且以字母或数字开头：{program!r}（例如 "my-task"）')

    branches = cfg.get("branches")
    if not isinstance(branches, dict) or not branches:
        errors.append("branches 必须是非空对象")
        branches = {}
    nodes = cfg.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 必须是非空数组")
        nodes = []

    seen = set()
    for i, n in enumerate(nodes):
        nid = n.get("id")
        if not nid:
            errors.append(f"nodes[{i}] 缺少 id")
            continue
        if nid in seen:
            errors.append(f"节点 id 重复：{nid}")
        seen.add(nid)
        if n.get("branch") not in branches:
            errors.append(f"节点 {nid} 的 branch={n.get('branch')!r} 不在 branches 里")
        if n.get("state") not in STATE_LABEL:
            warnings.append(f"节点 {nid} 的 state={n.get('state')!r} 不是标准值，按 open 处理")

    for s in (cfg.get("mission") or {}).get("success", []):
        for nid in s.get("nodes", []):
            if nid not in seen:
                warnings.append(f'成功判据 {s.get("id")} 引用了不存在的节点：{nid}')

    dids = set()
    for d in cfg.get("decisions", []):
        did = d.get("id")
        if not did:
            errors.append("decisions 里有条目缺少 id")
            continue
        if did in dids:
            errors.append(f"拍板 id 重复：{did}")
        dids.add(did)
    return errors, warnings


def make_snapshot(cfg, nodes):
    return {
        "ts": now_str(),
        "counts": {s: sum(1 for n in nodes if n.get("state") == s) for s in STATE_LABEL},
        "nodes": {n["id"]: n.get("state") for n in nodes},
        "decisions": len(cfg.get("decisions", [])),
        "calibrations": len(cfg.get("calibrations", [])),
    }


def same_ignoring_ts(a, b):
    return ({k: v for k, v in a.items() if k != "ts"}
            == {k: v for k, v in b.items() if k != "ts"})


def diff_snapshots(prev, cur):
    if not prev:
        return {"first": True, "added": [], "removed": [], "changed": {},
                "d_decisions": 0, "d_calibrations": 0}
    pn, cn = prev.get("nodes", {}), cur.get("nodes", {})
    return {
        "first": False,
        "added": [k for k in cn if k not in pn],
        "removed": [k for k in pn if k not in cn],
        "changed": {k: (pn[k], cn[k]) for k in cn if k in pn and pn[k] != cn[k]},
        "d_decisions": cur.get("decisions", 0) - prev.get("decisions", 0),
        "d_calibrations": cur.get("calibrations", 0) - prev.get("calibrations", 0),
        "prev_ts": prev.get("ts"),
    }


def resolve_vault(arg):
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("TASK_TREE_VAULT")
    if env:
        return Path(env).expanduser()
    conf = Path.home() / ".config" / "task-tree" / "config.json"
    if conf.exists():
        try:
            return Path(json.loads(conf.read_text(encoding="utf-8"))["vault"]).expanduser()
        except Exception:
            pass
    for cand in (
        Path.home() / "Desktop" / "Claude记忆",
        Path.home() / "Documents" / "Obsidian Vault",
        Path.home() / "Obsidian",
    ):
        if cand.exists():
            return cand
    return Path.home() / "task-tree-output"


def obsidian_uri(vault_root, rel_path):
    rel = Path(rel_path)
    file_part = rel.as_posix()
    for ext in (".md", ".canvas"):
        if file_part.endswith(ext):
            file_part = file_part[: -len(ext)]
            break
    return ("obsidian://open?vault=" + quote(vault_root.name)
            + "&file=" + quote(file_part, safe="/"))


def open_in_obsidian(vault_root, rel_path):
    uri = obsidian_uri(vault_root, rel_path)
    if sys.platform == "darwin":
        if Path("/Applications/Obsidian.app").exists():
            subprocess.run(["open", uri], check=False)
        else:
            subprocess.run(["open", "-R", str(vault_root / rel_path)], check=False)
    elif os.name == "nt":
        os.startfile(uri)
    else:
        subprocess.run(["xdg-open", uri], check=False)
    return uri


class Tree:
    def __init__(self, cfg, vault, dry=False, history=None, diff=None, history_path=None):
        self.cfg = cfg
        self.history = history or []
        self.diff = diff or {}
        self.history_path = history_path
        self.program = safe_program(cfg.get("program"))
        self.title = cfg.get("title") or f"{self.program} 任务树"
        self.mission = cfg.get("mission") or {}
        self.roles = cfg.get("roles") or []
        self.branches = cfg.get("branches") or {}
        self.nodes = cfg.get("nodes") or []
        self.decisions = {d["id"]: d for d in cfg.get("decisions", [])}
        self.calibrations = cfg.get("calibrations") or []
        self.checks = cfg.get("drift_checks") or []
        self.log = cfg.get("log") or []
        self.current = cfg.get("current") or ""
        self.out = Path(vault) / "50 任务树" / self.program
        self.dry = dry
        self.written = set()
        self.by_branch = {b: [n for n in self.nodes if n.get("branch") == b] for b in self.branches}
        self.node_by_id = {n["id"]: n for n in self.nodes}
        self.serves = {}
        for s in self.mission.get("success", []):
            for nid in s.get("nodes", []):
                self.serves.setdefault(nid, []).append(s["id"])
        self.success_text = {s["id"]: s["text"] for s in self.mission.get("success", [])}
        self.stem = {n["id"]: safe(f'{n["id"]} {n.get("title", n["id"])}') for n in self.nodes}
        self.branch_stem = {
            b: safe(f'{b} {self.branches[b].get("name", b)}') for b in self.branches
        }
        self.root_stem = safe(self.title)
        self.calib_stem = safe(f"{self.title} 口径校准")
        self.timeline_stem = safe(f"{self.title} 演进时间线")
        self.growth_stem = safe(f"{self.title} 生长")
        self.canvas_stem = safe(self.title)

    # ---------- helpers ----------
    def write(self, rel, text):
        p = self.out / rel
        if self.dry:
            print("  +", p)
            self.written.add(p)
            return p
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            p.chmod(0o644)
        p.write_text(text, encoding="utf-8")
        p.chmod(0o444)
        self.written.add(p)
        return p

    def fm(self, node_id, title, tags, extra=""):
        return (
            "---\n"
            f'node_id: "{node_id}"\n'
            f'title: "{title}"\n'
            f"tags: [{', '.join(tags)}]\n"
            f"{extra}"
            f"generated: {TODAY}\n"
            "generator: task-tree skill\n"
            "---\n\n"
        )

    def el_link(self, nid):
        return f'[[{self.stem[nid]}|{nid}]]' if nid in self.stem else nid

    def br_link(self, bid):
        return f'[[{self.branch_stem[bid]}|{bid} {self.branches[bid].get("name", bid)}]]'

    def decisions_of(self, node):
        out = []
        for did in node.get("decision_ids", []):
            if did in self.decisions:
                out.append(self.decisions[did])
        return sorted(out, key=lambda d: d.get("date", ""), reverse=True)

    # ---------- render ----------
    def render(self):
        self.render_root()
        for bid in self.branches:
            self.render_branch(bid)
        for n in self.nodes:
            self.render_node(n)
        self.render_calibration()
        self.render_timeline()
        self.render_growth()
        self.render_canvas()
        self.cleanup()
        self.update_index()
        if not self.dry:
            print(f"生成 {len(self.written)} 个文件（含 1 个 canvas、1 个生长 SVG）→ {self.out}")
            print(f"节点 {len(self.nodes)}："
                  + " · ".join(f"{STATE_LABEL[s]} {sum(1 for n in self.nodes if n.get('state') == s)}"
                               for s in STATE_ORDER if any(n.get("state") == s for n in self.nodes)))
            bad = sum(1 for _, hits in self.scan_drift() if hits)
            print(f"口径冲突：{bad} 项")

    def success_line(self, s):
        states = [self.node_by_id[x].get("state") for x in s.get("nodes", []) if x in self.node_by_id]
        st = worst(states)
        links = "、".join(self.el_link(x) for x in s.get("nodes", []) if x in self.node_by_id)
        return f'- **{s.get("id", "")}** {s.get("text", "")} — {STATE_BADGE.get(st, st)}（{links}）'

    def scan_drift(self):
        results = []
        default_files = [Path(p).expanduser() for p in self.cfg.get("drift_files", [])]
        for chk in self.checks:
            files = [Path(p).expanduser() for p in chk.get("files", [])] or default_files
            hits = []
            for f in files:
                if not f.exists():
                    continue
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    for pat in chk.get("stale_patterns", []):
                        if pat in line:
                            hits.append((f.name, i, pat, line.strip()))
                            break
            results.append((chk, hits))
        return results

    def render_root(self):
        counts = {s: sum(1 for n in self.nodes if n.get("state") == s) for s in STATE_LABEL}
        rows = []
        for bid, b in self.branches.items():
            sub = self.by_branch.get(bid, [])
            done = sum(1 for n in sub if n.get("state") == "done")
            st = worst([n.get("state") for n in sub])
            rows.append(f'| {self.br_link(bid)} | {cell(b.get("why"), 60)} | {done}/{len(sub)} | {STATE_LABEL.get(st, st)} |')

        success_md = "\n".join(self.success_line(s) for s in self.mission.get("success", [])) or "（未填写成功判据）"
        non_goals = self.mission.get("non_goals") or []
        non_goals_md = ("## 不做什么\n\n" + "\n".join(f"- {clean(x, 160)}" for x in non_goals) + "\n\n") if non_goals else ""
        pending = sorted(
            [d for d in self.decisions.values() if d.get("status") in ("proposed", "deferred")],
            key=lambda d: (d.get("date", ""), d["id"]), reverse=True,
        )[:5]
        pending_md = "\n".join(
            f'- `{d["id"]}` {d.get("date", "")} · {clean(d.get("title"), 80)} · *{d.get("status")}*'
            for d in pending
        ) or "（没有 proposed/deferred 条目。）"

        cal_rows = "\n".join(
            f'| {c.get("date", "")} | {c.get("kind", "")} | {c.get("title", "")} | {c.get("decision", "")} |'
            for c in self.calibrations[-6:]
        ) or "| — | — | 还没有校准记录 | — |"

        drift_md = "\n".join(
            f'- **{chk["topic"]}**：应以 {chk["canonical"]} 为准；'
            + "、".join(f'`{fname}` 第 {ln} 行 “{pat}”' for fname, ln, pat, _ in hits)
            for chk, hits in self.scan_drift() if hits
        )
        drift_md = ("⚠️ 发现旧口径，先改数据源再改页面：\n\n" + drift_md) if drift_md else "✅ 未发现旧口径。"

        body = self.fm(self.program, self.title, ["任务树", self.program, "根"],
                       f'mission: "{clean(self.mission.get("why"), 80)}"\n')
        body += f"""# {self.title}

> 生成于 {TODAY}。`tree.json` 是唯一真相；本库是只读镜像，改完源重新生成。
> 库内位置：`50 任务树/{self.program}/` · 画布：`{self.canvas_stem}.canvas`

## 为什么做

**{self.mission.get("why", "（未填写）")}**

来源：{self.mission.get("source", "（未标注）")}

## 给谁用

{self.mission.get("who", "（未填写）")}

{self.mission.get("who_secondary", "")}

来源：{self.mission.get("who_source", "（未标注）")}

{non_goals_md}## 什么算成功

{success_md}

> 任何新增工作都必须指向上面某一条；指向不了的工作不进主线。

## 当前态势

{("```text" + chr(10) + self.current + chr(10) + "```") if self.current else "（未填写 current）"}

节点 {len(self.nodes)} 项 = {' · '.join(f"{STATE_LABEL[s]} {counts[s]}" for s in STATE_LABEL)}。
本轮变化与生长曲线见 [[{self.growth_stem}]]。

## 待拍板（台账）

{pending_md}

## 协同（这一轮）

{self.roles_md()}{self.collaboration_md()}

## 分支

| 分支 | 这一枝为什么存在 | 进度 | 状态 |
|---|---|---|---|
{chr(10).join(rows)}

## 最近的目标校准

| 日期 | 类型 | 校准 | 依据 |
|---|---|---|---|
{cal_rows}

完整路径见 [[{self.calib_stem}]] 与 [[{self.timeline_stem}]]。

## 口径检查

{drift_md}

## 怎么读

- **根页**：使命、对象、成功判据、当前态势。
- **分支页**：这一枝的意图、节点表、修正史、相关原话。
- **节点页**：单个交付物的判据、证据、拍板链。
- **校准页**：目标变过什么、为什么变。
- **时间线**：按日期回放拍板与过程日志。
- **生长页**：本轮新增/迁移、分支进度、最近 24 次生成的状态构成。
- **维护**：只改 `tree.json`，再运行生成器；不手改本库。
"""
        self.write(f"{self.root_stem}.md", body)

    def render_branch(self, bid):
        b = self.branches[bid]
        sub = self.by_branch.get(bid, [])
        done = sum(1 for n in sub if n.get("state") == "done")
        st = worst([n.get("state") for n in sub])
        rows = [
            f'| {self.el_link(n["id"])} | {cell(n.get("title"), 28)} | {STATE_LABEL.get(n.get("state"), "")} '
            f'| {cell(n.get("judge"), 70)} | {cell(n.get("next"), 60)} |'
            for n in sub
        ]
        linked = []
        for n in sub:
            for d in self.decisions_of(n):
                if d not in linked:
                    linked.append(d)
        dec_md = "\n".join(
            f'- `{d["id"]}` {d.get("date", "")} · {d.get("title", "")} · {d.get("status", "")}'
            for d in linked
        ) or "（暂无直接挂接的拍板。）"
        quotes = b.get("quotes") or []
        quote_md = "\n\n".join(
            (f'> {clean(q, 200)}' if isinstance(q, str) else f'> **{q.get("label", "原话")}**：{clean(q.get("text"), 180)}\n>\n> {clean(q.get("value"), 100)}')
            for q in quotes
        ) or "（暂无挂接原话。）"
        serves = "、".join(f'{sid} {self.success_text.get(sid, "")}' for sid in b.get("serves", []))

        body = self.fm(f"{self.program}-{bid}", f'{bid} {b.get("name", bid)}',
                       ["任务树", self.program, f"分支-{bid}", "分支"],
                       f'branch: "{bid}"\nstate: "{st}"\n')
        body += f"""# {bid} {b.get("name", bid)}

> 父节点：[[{self.root_stem}]] · 节点 {len(sub)} 项 · 已定 {done}/{len(sub)} · {STATE_BADGE.get(st, st)}

## 这一枝为什么存在

{b.get("why", "（未填写）")}

服务：{serves or "（未挂接成功判据）"}

## 节点与判据

| 节点 | 名称 | 状态 | 成功判据 | 下一动作 |
|---|---|---|---|---|
{chr(10).join(rows)}

## 修正与拍板

{dec_md}

## 相关原话

{quote_md}

## 子节点

{chr(10).join(f'- [[{self.stem[n["id"]]}]]' for n in sub)}
"""
        self.write(f"分支/{self.branch_stem[bid]}.md", body)

    def render_node(self, n):
        nid = n["id"]
        bid = n.get("branch", "")
        dlist = self.decisions_of(n)
        dec_md = "\n\n".join(
            f'### `{d["id"]}` {d.get("date", "")} · {d.get("status", "")}\n\n'
            f'**{d.get("title", "")}**\n\n{clean(d.get("decision"), 500)}'
            for d in dlist
        ) or "（暂无直接挂接的拍板。）"
        ev = "\n".join(f"- `{x}`" for x in n.get("evidence", [])) or "（无）"
        serves = "、".join(f"{sid} {self.success_text[sid]}" for sid in self.serves.get(nid, [])) or "（未挂接成功判据，需要补）"
        why = n.get("why") or self.branches.get(bid, {}).get("why", "")
        lessons = n.get("lessons") or []
        lesson_md = "\n".join(f"- {clean(x, 200)}" for x in lessons) or "（无）"

        badge = ""
        if nid in self.diff.get("added", []):
            badge = "> 🆕 本轮新增\n\n"
        elif nid in self.diff.get("changed", {}):
            old, new = self.diff["changed"][nid]
            badge = f"> 🔄 本轮状态：{STATE_LABEL.get(old, old)} → {STATE_LABEL.get(new, new)}\n\n"

        body = self.fm(f"{self.program}-{nid}", f'{nid} {n.get("title", "")}',
                       ["任务树", self.program, "节点", f"分支-{bid}"],
                       f'branch: "{bid}"\nstate: "{n.get("state", "")}"\n')
        body += f"""# {nid} {n.get("title", "")}

{badge}> 所属：{self.br_link(bid) if bid in self.branches else bid} · 根：[[{self.root_stem}]] · {STATE_BADGE.get(n.get("state"), n.get("state"))}

## 为什么做

{why}

服务：{serves}

## 成功判据

{n.get("judge", "（未写判据）")}

## 下一动作

{n.get("next", "（未写）")}

## 证据

{ev}

## 修正与拍板

{dec_md}

## 教训

{lesson_md}
"""
        self.write(f"节点/{self.stem[nid]}.md", body)

    def render_calibration(self):
        cur = "\n".join(f'| {c["topic"]} | {c["canonical"]} |' for c in self.checks) or "| — | 还没有口径检查 |"
        cal = "\n".join(
            f'| {c.get("date", "")} | {c.get("kind", "")} | {c.get("title", "")} | {c.get("from", "")} '
            f'| {c.get("to", "")} | `{c.get("decision", "")}` |'
            for c in self.calibrations
        ) or "| — | — | — | — | — | — |"
        scan = "\n".join(
            f'| {chk["topic"]} | {chk["canonical"]} | '
            + ("✅ 一致" if not hits else "⚠️ " + "、".join(f"{fname} 第 {ln} 行 “{pat}”" for fname, ln, pat, _ in hits))
            + " |"
            for chk, hits in self.scan_drift()
        ) or "| — | — | 未配置检查 |"

        body = self.fm(f"{self.program}-calibration", f"{self.title} 口径校准", ["任务树", self.program, "校准"])
        body += f"""# {self.title} 口径校准

## 当前口径

| 主题 | 现在以什么为准 |
|---|---|
{cur}

## 目标与方案校准史

| 日期 | 类型 | 变的是什么 | 从 | 到 | 依据 |
|---|---|---|---|---|---|
{cal}

## 冲突扫描（实时）

| 主题 | 权威值 | 检查结果 |
|---|---|---|
{scan}

> 发现冲突时：先改 `tree.json` 或上游数据源，再重跑生成器；不要直接改页面。
"""
        self.write(f"{self.calib_stem}.md", body)

    def render_timeline(self):
        decs = sorted(self.decisions.values(), key=lambda d: (d.get("date", ""), d["id"]), reverse=True)
        lines, last = [], None
        for d in decs:
            if d.get("date") != last:
                lines.append(f"\n### {d.get('date', '日期未知')}\n")
                last = d.get("date")
            rel = []
            for n in self.nodes:
                if d["id"] in (n.get("decision_ids") or []):
                    rel.append(self.el_link(n["id"]))
            lines.append(f'- `{d["id"]}` · {clean(d.get("title"), 80)} · *{d.get("status", "")}*'
                         + ((" · 关联 " + "、".join(rel)) if rel else ""))
        log_md = "\n\n".join(
            f'### {e.get("date", "")} · {e.get("title", "")}\n\n{clean(e.get("summary"), 700)}'
            for e in self.log
        ) or "（没有过程日志。）"
        body = self.fm(f"{self.program}-timeline", f"{self.title} 演进时间线", ["任务树", self.program, "时间线"])
        body += f"""# {self.title} 演进时间线

> 按日期倒序回放：先看拍板与修正，再看每天的交付与发现。

## 拍板与修正

{chr(10).join(lines) or "（没有拍板记录。）"}

## 过程日志

{log_md}
"""
        self.write(f"{self.timeline_stem}.md", body)

    def owner_of(self, n):
        return n.get("owner") or (
            "用户" if n.get("state") == "decide"
            else "外部" if n.get("state") == "blocked" else "Claude"
        )

    def collaboration_md(self, links=True):
        ref = (lambda x: self.el_link(x)) if links else (lambda x: f"`{x}`")
        moved = set(self.diff.get("changed", {})) | set(self.diff.get("added", []))
        claude = [n["id"] for n in self.nodes if n["id"] in moved and self.owner_of(n) == "Claude"]
        active = [n["id"] for n in self.nodes if n.get("state") == "partial" and self.owner_of(n) == "Claude"]
        user = [n["id"] for n in self.nodes if self.owner_of(n) == "用户"]
        external = [n["id"] for n in self.nodes if self.owner_of(n) == "外部"]

        def listing(ids):
            if not ids:
                return ""
            shown = "、".join(ref(x) for x in ids[:8])
            return f"（{shown}{' 等' if len(ids) > 8 else ''}）"

        return "\n".join([
            f"- **Claude**：本轮动了 {len(claude)} 项{listing(claude)}；手上推进中 {len(active)} 项",
            f"- **用户**：待拍板 {len(user)} 项{listing(user)}",
            f"- **外部/解阻**：受阻 {len(external)} 项{listing(external)}",
        ])

    def roles_md(self):
        if not self.roles:
            return ""
        rows = "\n".join(
            f'| {r.get("who", "")} | {cell(r.get("does"), 90)} |' for r in self.roles
        )
        return "| 谁 | 负责 |\n|---|---|\n" + rows + "\n\n"

    def growth_changes_md(self, links=True):
        ref = (lambda x: self.el_link(x)) if links else (lambda x: f"`{x}`")
        if self.diff.get("first"):
            return "这是第一份快照；下次有变化时，这里会列出新增、迁移与删除。"
        if self.diff.get("unchanged"):
            return f"与上次快照（{self.diff.get('prev_ts', '')}）相比没有变化，本次未追加新快照。"
        lines = []
        if self.diff.get("prev_ts"):
            lines.append(f"- 上次快照：{self.diff['prev_ts']}；本次：{now_str()}")
        for nid in self.diff.get("added", []):
            n = self.node_by_id.get(nid, {})
            lines.append(f'- 🆕 {ref(nid)} {clean(n.get("title"), 40)}'.rstrip())
        for nid, (old, new) in sorted(self.diff.get("changed", {}).items()):
            lines.append(f'- 🔄 {ref(nid)}：{STATE_LABEL.get(old, old)} → {STATE_LABEL.get(new, new)}')
        for nid in self.diff.get("removed", []):
            lines.append(f"- ❌ 移除节点 `{nid}`")
        dd, dc = self.diff.get("d_decisions", 0), self.diff.get("d_calibrations", 0)
        if dd:
            lines.append(f"- 拍板台账 {dd:+d}")
        if dc:
            lines.append(f"- 目标校准 {dc:+d}")
        return "\n".join(lines) or "（有变化，但没落在节点或台账上。）"

    def growth_svg(self):
        snaps = self.history[-24:]
        n = max(len(snaps), 1)
        pad_l, pad_r, pad_t, pad_b = 48, 18, 44, 42
        step, bw, plot_h = 36, 22, 190
        legend_w = sum(25 + len(STATE_LABEL[st]) * 11 for st in GROWTH_STACK)
        w = max(pad_l + n * step + pad_r, pad_l + legend_w + pad_r)
        h = pad_t + plot_h + pad_b
        max_total = max((sum(s.get("counts", {}).values()) for s in snaps), default=0) or 1
        el = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="-apple-system, Helvetica, Arial, sans-serif">',
            "<!-- generator: task-tree skill -->",
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
            f'<text x="{pad_l}" y="20" font-size="13" font-weight="600" fill="#0f172a">'
            f'节点状态构成 · 最近 {len(snaps)} 次生成</text>',
        ]
        lx = pad_l
        for st in GROWTH_STACK:
            el.append(f'<rect x="{lx}" y="28" width="9" height="9" rx="2" fill="{GROWTH_COLORS[st]}"/>')
            el.append(f'<text x="{lx + 13}" y="36" font-size="10" fill="#475569">{STATE_LABEL[st]}</text>')
            lx += 25 + len(STATE_LABEL[st]) * 11
        for t in (0, 0.25, 0.5, 0.75, 1):
            y = pad_t + plot_h * (1 - t)
            el.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + n * step}" y2="{y:.1f}" '
                      f'stroke="#e2e8f0" stroke-width="1"/>')
            el.append(f'<text x="{pad_l - 8}" y="{y + 3.5:.1f}" font-size="9" fill="#94a3b8" '
                      f'text-anchor="end">{round(max_total * t)}</text>')
        for i, s in enumerate(snaps):
            c = s.get("counts", {})
            x = pad_l + i * step + (step - bw) / 2
            cur = pad_t + plot_h
            tip = " · ".join(f"{STATE_LABEL[st]} {c.get(st, 0)}" for st in GROWTH_STACK if c.get(st))
            el.append(f'<g><title>{s.get("ts", "")}：{tip}</title>')
            for st in GROWTH_STACK:
                v = c.get(st, 0)
                if not v:
                    continue
                bh = v / max_total * plot_h
                cur -= bh
                el.append(f'<rect x="{x:.1f}" y="{cur:.1f}" width="{bw}" height="{bh:.1f}" '
                          f'fill="{GROWTH_COLORS[st]}"/>')
            el.append("</g>")
        if snaps:
            idxs = sorted({0, len(snaps) - 1} | ({len(snaps) // 2} if len(snaps) > 2 else set()))
            for i in idxs:
                el.append(f'<text x="{pad_l + i * step + step / 2:.1f}" y="{pad_t + plot_h + 16}" '
                          f'font-size="9" fill="#64748b" text-anchor="middle">{snaps[i].get("ts", "")[5:10]}</text>')
        else:
            el.append(f'<text x="{w / 2}" y="{pad_t + plot_h / 2}" font-size="12" fill="#94a3b8" '
                      f'text-anchor="middle">还没有快照</text>')
        el.append(f'<text x="{pad_l}" y="{h - 8}" font-size="9" fill="#94a3b8">'
                  f'每根柱 = 一次生成；柱高 = 节点总数；悬停看当日构成。</text>')
        el.append("</svg>")
        return "\n".join(el)

    def render_growth(self):
        snaps = self.history[-24:]
        rows = []
        for s in reversed(snaps):
            c = s.get("counts", {})
            rows.append(
                f'| {s.get("ts", "")} | {sum(c.values())} | {c.get("done", 0)} | {c.get("partial", 0)} '
                f'| {c.get("decide", 0)} | {c.get("blocked", 0)} | {c.get("open", 0)} | {c.get("later", 0)} '
                f'| {s.get("decisions", 0)} | {s.get("calibrations", 0)} |'
            )
        table = "\n".join(rows) or "| — | — | — | — | — | — | — | — | — | — |"
        brows = []
        for bid in self.branches:
            sub = self.by_branch.get(bid, [])
            done = sum(1 for x in sub if x.get("state") == "done")
            pct = round(100 * done / len(sub)) if sub else 0
            filled = round(pct / 10)
            brows.append(f'| {self.br_link(bid)} | {done}/{len(sub)} | {"█" * filled}{"░" * (10 - filled)} {pct}% |')
        hist_note = f"`{self.history_path}`" if self.history_path else "（未记录路径）"

        body = self.fm(f"{self.program}-growth", f"{self.title} 生长",
                       ["任务树", self.program, "生长"])
        body += f"""# {self.title} 生长

> 每次运行生成器留一个快照，内容没变就不追加。历史源：{hist_note}
> 本页位置：`50 任务树/{self.program}/{self.growth_stem}.md`

## 本轮变化

{self.growth_changes_md()}

## 本轮协同

{self.collaboration_md()}

## 生长曲线

![[{self.growth_stem}.svg]]

## 分支进度

| 分支 | 已定/总数 | 进度 |
|---|---|---|
{chr(10).join(brows)}

## 快照台账

| 时间 | 节点 | 已定 | 推进中 | 待拍板 | 受阻 | 未开始 | 后置 | 拍板 | 校准 |
|---|---|---|---|---|---|---|---|---|---|
{table}

> 读法：先看「本轮变化」确认这轮动了什么，再看曲线确认整体在长还是在原地打转；
> 只有曲线变平、且待拍板一直不下降，才说明需要重新校准目标。返回 [[{self.root_stem}]]。
"""
        self.write(f"{self.growth_stem}.md", body)
        self.write(f"{self.growth_stem}.svg", self.growth_svg())

    def render_canvas(self):
        if self.dry:
            print("  +", self.out / f"{self.canvas_stem}.canvas")
            return
        nodes, edges = [], []
        nodes.append({"id": "mission", "type": "text", "x": 0, "y": 0, "width": 380, "height": 200,
                      "color": "6", "text": "# 使命\n\n" + self.mission.get("why", "")})
        nodes.append({"id": "who", "type": "text", "x": 0, "y": 240, "width": 380, "height": 140,
                      "color": "3", "text": "## 给谁用\n\n" + self.mission.get("who", "")})
        nodes.append({"id": "success", "type": "text", "x": 0, "y": 410, "width": 380, "height": 320,
                      "color": "4", "text": "## 什么算成功\n\n"
                      + "\n".join(f'- {s.get("id", "")} {s.get("text", "")}' for s in self.mission.get("success", []))})
        for i, bid in enumerate(self.branches):
            b = self.branches[bid]
            nid = f"br-{bid}"
            nodes.append({"id": nid, "type": "file",
                          "file": f"50 任务树/{self.program}/分支/{self.branch_stem[bid]}.md",
                          "x": 460, "y": i * 140, "width": 320, "height": 110,
                          "color": STATE_COLOR.get(worst([n.get("state") for n in self.by_branch.get(bid, [])]), "6")})
            edges.append({"id": f"e-m-{bid}", "fromNode": "mission", "fromSide": "right",
                          "toNode": nid, "toSide": "left"})
        nodes.append({"id": "next", "type": "text", "x": 860, "y": 0, "width": 380, "height": 260,
                      "color": "2", "text": "## 当前只做这一件\n\n" + (self.current or "（未填写）").replace("\n", "\n\n")})
        nodes.append({"id": "change", "type": "text", "x": 1260, "y": 0, "width": 360, "height": 360,
                      "color": "3", "text": "## 本轮变化\n\n" + self.growth_changes_md(links=False)
                      + "\n\n## 协同\n\n" + self.collaboration_md(links=False)})
        nodes.append({"id": "calib", "type": "file", "file": f"50 任务树/{self.program}/{self.calib_stem}.md",
                      "x": 860, "y": 300, "width": 380, "height": 100, "color": "1"})
        nodes.append({"id": "timeline", "type": "file", "file": f"50 任务树/{self.program}/{self.timeline_stem}.md",
                      "x": 860, "y": 440, "width": 380, "height": 100, "color": "5"})
        nodes.append({"id": "growth", "type": "file", "file": f"50 任务树/{self.program}/{self.growth_stem}.md",
                      "x": 860, "y": 580, "width": 380, "height": 100, "color": "4"})
        nodes.append({"id": "home", "type": "file", "file": f"50 任务树/{self.program}/{self.root_stem}.md",
                      "x": 860, "y": 720, "width": 380, "height": 100, "color": "6"})
        edges += [
            {"id": "e-m-who", "fromNode": "mission", "fromSide": "bottom", "toNode": "who", "toSide": "top"},
            {"id": "e-m-success", "fromNode": "mission", "fromSide": "bottom", "toNode": "success", "toSide": "top"},
            {"id": "e-next-change", "fromNode": "next", "fromSide": "right", "toNode": "change", "toSide": "left"},
        ]
        p = self.out / f"{self.canvas_stem}.canvas"
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            p.chmod(0o644)
        p.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=1), encoding="utf-8")
        p.chmod(0o444)
        self.written.add(p)

    def update_index(self):
        if self.dry:
            return
        base = self.out.parent
        idx = base / "_index.json"
        data = {}
        if idx.exists():
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data = {k: v for k, v in data.items()
                if k == self.program or (base / v.get("root", "")).exists()}
        counts = {s: sum(1 for n in self.nodes if n.get("state") == s) for s in STATE_LABEL}
        data[self.program] = {
            "program": self.program, "title": self.title, "updated": TODAY,
            "ts": now_str(), "total": len(self.nodes), "counts": counts,
            "current": clean(self.current, 120),
            "root": f"{self.program}/{self.root_stem}.md",
            "growth": f"{self.program}/{self.growth_stem}.md",
        }
        atomic_write(idx, json.dumps(data, ensure_ascii=False, indent=1))

        rows = []
        for p in sorted(data.values(), key=lambda x: x.get("ts", ""), reverse=True):
            c = p.get("counts", {})
            rows.append(
                f'| [[{base.name}/{p["root"][:-3]}|{p["title"]}]] | {cell(p.get("current"), 50) or "—"} '
                f'| {p.get("total", 0)} | {c.get("done", 0)} | {c.get("partial", 0)} '
                f'| {c.get("decide", 0)} | {c.get("blocked", 0)} '
                f'| {p.get("ts", "")} | [[{base.name}/{p["growth"][:-3]}|生长]] |'
            )
        body = self.fm("task-index", "任务总览", ["任务树", "总览"])
        body += f"""# 任务总览

> 每跑一次任一任务的生成器，本页自动更新。按最近生成时间倒序。

| 任务 | 当前只做 | 节点 | 已定 | 推进中 | 待拍板 | 受阻 | 最近生成 | 生长 |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

> 点任务进根页，点「生长」看这一轮动了什么、谁在做什么。
"""
        page = base / "任务总览.md"
        if page.exists():
            page.chmod(0o644)
        atomic_write(page, body)
        page.chmod(0o444)

    def cleanup(self):
        if self.dry or not self.out.exists():
            return
        for p in list(self.out.rglob("*.md")) + list(self.out.rglob("*.svg")):
            if p in self.written:
                continue
            try:
                head = p.read_text(encoding="utf-8")[:300]
            except Exception:
                continue
            if "generator: task-tree skill" in head:
                p.chmod(0o644)
                p.unlink()


def main():
    ap = argparse.ArgumentParser(description="渲染任务树到 Obsidian")
    ap.add_argument("--tree", default=".task-tree/tree.json", help="tree.json 路径")
    ap.add_argument("--vault", default=None, help="Obsidian 库根目录")
    ap.add_argument("--history", default=None,
                    help="历史快照 JSON；默认与 tree.json 同目录、文件名加 _history")
    ap.add_argument("--dry", action="store_true", help="只列出将生成的文件")
    ap.add_argument("--no-open", action="store_true", help="生成后不自动打开 Obsidian")
    args = ap.parse_args()

    tree_path = Path(args.tree).expanduser().resolve()
    if not tree_path.exists():
        sys.exit(f"找不到 tree 文件：{tree_path}")
    try:
        cfg = json.loads(tree_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"tree.json 不是合法 JSON：第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}")
    errors, warnings = validate_cfg(cfg)
    if errors:
        print("tree.json 校验失败：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    for w in warnings:
        print(f"⚠️ {w}")
    vault = resolve_vault(args.vault)
    if not vault.exists():
        vault.mkdir(parents=True, exist_ok=True)
        print(f"⚠️ 目标库不存在，已创建：{vault}（可在 ~/.config/task-tree/config.json 里改 vault）")

    hist_path = (Path(args.history).expanduser() if args.history
                 else tree_path.with_name(tree_path.stem + "_history.json"))
    history = []
    if hist_path.exists():
        try:
            raw = json.loads(hist_path.read_text(encoding="utf-8"))
            history = raw.get("snapshots", []) if isinstance(raw, dict) else raw
        except Exception as exc:
            print(f"⚠️ 历史快照读取失败，按首次生成处理：{exc}")

    cur = make_snapshot(cfg, cfg["nodes"])
    prev = history[-1] if history else None
    if prev and same_ignoring_ts(prev, cur):
        diff = {"first": False, "unchanged": True, "added": [], "removed": [], "changed": {},
                "d_decisions": 0, "d_calibrations": 0, "prev_ts": prev.get("ts")}
    else:
        diff = diff_snapshots(prev, cur)
        history.append(cur)
    history = history[-120:]

    tree = Tree(cfg, vault, dry=args.dry, history=history, diff=diff, history_path=hist_path)
    tree.render()
    if not args.dry:
        atomic_write(hist_path, json.dumps({"snapshots": history}, ensure_ascii=False, indent=1))
        print(f"历史快照 → {hist_path}（{len(history)} 条）" + ("，本轮无变化未追加" if diff.get("unchanged") else ""))
        rel_canvas = Path("50 任务树") / tree.program / f"{tree.canvas_stem}.canvas"
        uri = obsidian_uri(vault, rel_canvas)
        print(f"任务目录 → {tree.out}")
        print(f"在 Obsidian 打开 → {uri}")
        if not args.no_open:
            open_in_obsidian(vault, rel_canvas)


if __name__ == "__main__":
    main()
