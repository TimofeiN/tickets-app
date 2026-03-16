## Backend Rules

### Code structure
- Keep route handlers thin.
- Keep business logic in `application` or `domain`, not in routers.
- Keep external API and DB access in `infrastructure`.
- Follow existing backend patterns before introducing new structure.

### Core principles
- KISS: simplest solution.
- YAGNI: create only when needed.
- Fail-fast: crash on invalid config.
- Single responsibility.
- Keep code junior-friendly.
- No TODOs in code; create tasks instead.

### Python and typing
- Follow PEP 8.
- Use explicit type hints (`list[str]`, `str | None`).
- Keep class names `PascalCase`, functions/variables `snake_case`, constants `UPPER_SNAKE_CASE`.
- Keep nesting depth within 3-4 levels.
- Do not mutate input arguments.
- Do not use magic numbers/strings without named constants or enums.

### Data and models
- Use Pydantic models for FastAPI request/response boundaries.
- Use `@dataclass` for small internal value objects instead of raw dicts.
- `dict` can be used only for mapping purpose, data transport between classes should be implemented with `dataclass` or `Pydantic model`
- Use `Enum`/`StrEnum` for closed sets of domain values.
- Do not repeat string literals for statuses and flags.

### Imports and dependencies
- Keep imports at top of file.
- Do not use lazy imports inside functions unless strictly required.
- Use `TYPE_CHECKING` only for confirmed circular-import cases.

### Quality and reliability
- Use concrete exception types with contextual messages.
- Security baseline: input validation, auth/authz, SQL injection prevention, secret handling.
- Performance baseline: avoid N+1 queries, use `selectinload`/`joinedload` deliberately, add indexes where needed.
- Use structured logging with service context (for example `logger.bind(service="Name")`).

### Comments and docs
- Prefer self-documenting code through clear names, small functions, and extracted methods.
- Avoid comments and docstrings unless they add non-obvious context that code cannot express.

### Tests
- Add or update tests for behavior changes.
