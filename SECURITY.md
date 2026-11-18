# Security

## Reporting

Please report suspected vulnerabilities privately via GitHub Security Advisories
(“Report a vulnerability”) rather than a public issue. Include the version,
platform, and a minimal `tree.json` that reproduces the problem.

## Threat model

`tree.json` may come from another user or an untrusted repository. The generator:

- validates `program` against `[A-Za-z0-9._-]` and rejects path separators;
- sanitizes every filename derived from user content;
- reports malformed JSON with line/column instead of crashing;
- writes only under `<vault>/50 任务树/`;
- performs no network access and has no third-party dependencies.

Rendered Markdown and SVG are output artifacts, not a sandbox. Treat generated
notes like any other repository content: review before publishing a vault.
