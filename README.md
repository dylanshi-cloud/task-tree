# task-tree

**A traceable, living task tree for Claude Code — intent, work, evidence, and drift control in one source of truth.**

Most agent workflows lose the *why* after the first few turns. `task-tree` keeps a single JSON source for the mission, branches, acceptance criteria, decisions, and calibrations, then renders it as a read-only Obsidian mirror: a canvas, linked notes, a calibration ledger, and a growth chart that shows what actually moved.

> 中文说明见 [README.zh-CN.md](README.zh-CN.md)。v0.1 UI strings are Chinese; English UI is on the roadmap.

## Why it exists

- **Intent first.** The skill asks *why / for whom / what counts as success / what is out of scope* before splitting work.
- **One source of truth.** `tree.json` is the only state. Notes and canvases are generated, never hand-edited.
- **Calibration instead of overwrite.** Goal changes append to `calibrations`; stale numbers are caught by `drift_checks`.
- **Growth is visible.** Every run records a snapshot. The growth page shows new nodes, state transitions, who did what, and a stacked-bar chart of the last 24 runs.
- **Collaboration is explicit.** `roles` and per-node `owner` produce a “who is doing what / what needs your decision / what is blocked” view.
- **Low overhead.** One JSON file and one generator run per round. Small tasks use a one-branch, ≤3-node tree.

## What gets generated

```text
<vault>/50 任务树/
├── 任务总览.md                  # cross-task index
└── <program>/
    ├── <title>.md               # root: mission, users, success, current, collaboration
    ├── 分支/                     # one page per branch
    ├── 节点/                     # one page per deliverable
    ├── <title> 口径校准.md        # current canonical values + calibration history + drift scan
    ├── <title> 演进时间线.md      # decisions and daily log
    ├── <title> 生长.md + .svg     # this round's delta + growth chart
    └── <title>.canvas           # visual map for Obsidian
```

Each node page carries: why it exists, its success criterion, next action, evidence, linked decisions, lessons, and a 🆕/🔄 badge when it changed this round.

## Install

### Plugin marketplace

```text
/plugin install task-tree --marketplace dylanshi-cloud/task-tree
```

Or add the marketplace first, then install:

```text
/plugin marketplace add dylanshi-cloud/task-tree
/plugin install task-tree@task-tree-marketplace
```

Both the plugin and marketplace manifests live in `.claude-plugin/`; validate
them with `claude plugin validate --strict .`.

### Standalone skill

```bash
git clone https://github.com/dylanshi-cloud/task-tree.git ~/.claude/skills/task-tree
```

Or copy the folder into `~/.claude/skills/task-tree/` (`%USERPROFILE%\.claude\skills\task-tree\` on Windows).

Requirements: Python 3.10+ (stdlib only), Obsidian for the rendered view, macOS/Windows/Linux.

### Point it at a vault

Choose one:

- `--vault /path/to/ObsidianVault`
- `TASK_TREE_VAULT=/path/to/ObsidianVault`
- `~/.config/task-tree/config.json`:

```json
{ "vault": "/Users/you/Desktop/ObsidianVault" }
```

## Quick start

```bash
cp templates/tree.json .task-tree/my-task/tree.json
# edit program, title, mission, branches, nodes
python3 ~/.claude/skills/task-tree/scripts/build_task_tree.py \
  --tree .task-tree/my-task/tree.json
```

The generator prints the task folder and an `obsidian://` link, and opens the canvas automatically. Use `--no-open` to disable.

Run the built-in example:

```bash
python3 scripts/build_task_tree.py \
  --tree templates/tree.json \
  --vault /tmp/task-tree-test --no-open
```

Expected: 13 notes, 1 canvas, 1 SVG.

A lightweight one-branch example:

```bash
python3 scripts/build_task_tree.py \
  --tree examples/small-task.json \
  --vault /tmp/task-tree-example \
  --history /tmp/task-tree-example-history.json --no-open
```

## Data model

See [`templates/tree.json`](templates/tree.json) for a complete example and [`schema/tree.schema.json`](schema/tree.schema.json) for the machine-readable schema.

Core fields:

| Field | Purpose |
|---|---|
| `program` | Short slug; also the output folder name (`[A-Za-z0-9._-]`) |
| `title` | Human-readable tree title |
| `roles` | Who is responsible for what (`Claude`, user, external) |
| `mission` | `why`, `who`, `non_goals`, `success[]` |
| `branches` | 3–9 areas; each says why it exists and which success criteria it serves |
| `nodes` | Deliverables with `state`, `owner`, `judge`, `next`, `evidence` |
| `decisions` | Decisions with ids, dates, status |
| `calibrations` | Goal/approach/scope changes; append-only |
| `drift_checks` | Canonical values and stale patterns to scan |
| `current` | The one thing being worked on now |

States: `done | partial | open | decide | blocked | later`.

## How the skill is used

`SKILL.md` defines the three-step protocol:

1. **Clarify intent** until you can restate it without the user changing keywords.
2. **Split into root → branches → nodes**, each node independently acceptable.
3. **Confirm, then execute** one node at a time; update the JSON and regenerate at the end of each round.

The bundled script handles rendering, history snapshots, drift scanning, cross-task indexing, and opening the result in Obsidian.

## Security and trust

- `tree.json` is treated as untrusted input: `program` is validated to prevent path traversal, filenames are sanitized, JSON parse errors are reported with line/column.
- Generated files are marked with `generator: task-tree skill`; cleanup only deletes files carrying that marker.
- No network calls, no third-party dependencies.
- The generator writes only inside `<vault>/50 任务树/`.

See [SECURITY.md](SECURITY.md) for reporting.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

CI runs the suite on Linux, macOS, and Windows across Python 3.10–3.12.

## Repository layout

```text
.claude-plugin/          # plugin.json, marketplace.json, icon
SKILL.md                 # the skill Claude loads
scripts/build_task_tree.py
templates/               # tree.json + config.json
examples/                # lightweight one-branch example
schema/tree.schema.json  # editor/CI schema
tests/                   # integration tests
evals/                   # realistic prompts for skill evaluation
.github/workflows/       # CI
```

## Status

v0.1.0 — core loop and release scaffolding are complete; the plugin and
marketplace manifests pass `claude plugin validate`. Known gaps: English UI
strings, demo screenshots/GIF, and the first public repository push. See
[CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
