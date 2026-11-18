# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
