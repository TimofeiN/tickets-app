# Repository Rules

- Never use the `codex/` prefix in branch names.
- Never use the `codex/` prefix in commit messages.
- Merge into `develop` must always be done via squash commit (single commit per feature branch merge).
- Before commit: run `make backend-check`; if format/lint fails, run `make backend-format`; if tests fail, fix tests before commit.
- Commit messages must be short and follow best practices.
