## Repository
- Branches:
  use `feature/<feature_name>` and never use the `codex/` prefix.
- Commits:
  keep messages short and descriptive, and never use the `codex/` prefix.
- Before commit:
  run `make backend-check`; if format or lint fails, run `make backend-format`, and fix failing tests before commit.
- Merge to `develop`:
  always use a squash commit.
  For squash merges into `develop`, keep a short subject line and include the
  merged branch commits in the commit message body, similar to the default
  GitHub squash-merge message.

## Code Writing
- Keep only code needed for the current scenario.
- Do not add preparatory abstractions or future-facing helpers without a clear need.
- When running backend tests or backend/dev scripts, run them in the container.

## Execution Discipline
- Follow the request exactly; do not expand scope without explicit instruction.
- Do not perform additional actions, refactoring, or improvements unless explicitly asked.
- If the request is unclear or ambiguous, ask clarifying questions before proceeding.
