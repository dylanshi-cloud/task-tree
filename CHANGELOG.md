# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] — 2026-11-18

### Changed

- `CLAUDE.md` and `SKILL.md` now open with the five-step Algorithm gate: 去愚 → 删除 → 优化 → 加速 → 自动化.
- `SKILL.md` consolidated from 183 to 114 lines (5756 → 3665 characters): removed duplicate page-shape, maintenance, growth, efficiency and porting sections; the data model is a compact skeleton pointing at `schema/` and `templates/`.
- Output is consolidated: node sections live inside branch pages, calibration and timeline merge into one history page, and growth changes plus the SVG embed live on the root page. A one-branch, three-node task now generates 5 files instead of 10.
- The snapshot ledger table is gone; the SVG chart and the root change list carry the same signal with less duplication.
- Canvas and cross-task index now link to the root and history pages.
- README status and architecture notes updated for v0.1.2.

### Added

- Execution Algorithm gate: optional `deleted` and `automation` arrays record what was removed and which flows were validated enough to automate.
- Root page gains an “算法关（删除与自动化）” section with empty-state guidance, so a tree that only grows is visibly called out.
- Protocol now requires a delete pass before branches and a fixed receipt line: what this version removed / what should not be automated yet.
- Two integration tests for the gate and its empty state (12 total).

### Fixed

- Documentation no longer references a standalone growth page; growth lives on the root page and history page.

## [0.1.1] — 2026-11-18

### Fixed

- Windows consoles could crash on Chinese status output when stdout was redirected; the generator now forces UTF-8.
- Wiki-link integrity test compared backslash paths against forward-slash links on Windows; it now compares POSIX paths.
- CI targets Python 3.10–3.12, since `ubuntu-latest` no longer ships 3.9.

## [0.1.0] — 2026-11-18

### Added

- Three-step protocol: clarify intent → split branches and nodes → confirm and execute.
- Single-source `tree.json` with mission, roles, branches, nodes, decisions, calibrations, drift checks.
- Obsidian renderer: root page, branch pages, node pages, calibration ledger, timeline, canvas.
- Growth view: per-round snapshots, change list, collaboration block, branch progress, 24-run SVG chart.
- Per-node 🆕 / 🔄 badges and a “this round” canvas node.
- Cross-task overview page (`任务总览.md`) and `_index.json`.
- Automatic Obsidian canvas opening with `--no-open` opt-out.
- Input validation: duplicate ids, unknown branch, invalid state, malformed JSON, path-traversal `program`.
- Integration test suite (9 tests) covering generation, idempotency, history, validation, link integrity, and canvas URIs.
- JSON Schema, a lightweight example, and three realistic eval prompts.
- Plugin and marketplace manifests with a listing icon, validated by `claude plugin validate`.
- MIT license, CI matrix, security policy.

### Fixed

- Obsidian canvas links kept the `.canvas` extension and silently failed to switch tabs; URIs now omit `.md` and `.canvas`.
- Windows consoles could crash on Chinese status output when stdout was redirected; the generator now forces UTF-8.
- CI now targets Python 3.10–3.12, since `ubuntu-latest` no longer ships 3.9.

### Known gaps

- UI strings are Chinese; English localization is planned.
- Demo screenshots/GIF and the first public repository push are still pending.
