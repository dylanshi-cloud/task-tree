# Contributing

Thanks for improving task-tree. Keep changes small and testable.

## Setup

```bash
git clone https://github.com/dylanshi-cloud/task-tree.git
cd task-tree
python3 -m unittest discover -s tests -v
```

No dependencies beyond the Python standard library.

## Pull requests

- Describe the user-visible change and the failure it prevents.
- Add or update a test in `tests/` for behavior changes.
- Keep `SKILL.md` under ~500 lines; move detail into `references/` when it grows.
- Do not commit generated vault output, `__pycache__`, or personal history files.
- Run the suite on at least one platform before opening the PR.

## Adding examples

Put realistic trees in `examples/`. Use fictional data, keep them small, and
verify they render:

```bash
python3 scripts/build_task_tree.py --tree examples/<name>.json \
  --vault /tmp/task-tree-example --history /tmp/task-tree-example-history.json \
  --no-open
```

## Reporting bugs

Include the `tree.json` (redacted), the command, Python version, OS, and the
full stderr. Security issues go to [SECURITY.md](SECURITY.md), not the issue tracker.
