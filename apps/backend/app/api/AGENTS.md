## API Rules

### Router design
- Keep route handlers thin.
- Routers only do: request/response mapping, dependency injection, and one call to API service.
- Route handlers must not contain business logic, DB access, or provider orchestration.

### Layer boundaries
- Keep request orchestration in `app/api/services`.
- Keep business logic in `application` or `domain`.
- Keep DB and external API access in `infrastructure`.

### FastAPI dependencies
- Use FastAPI dependencies for request-scoped DB session lifecycle.
- Use `get_db_session` dependency in API dependency graph.
- Keep auth/session extraction in dependency functions, not in routers.

### API schemas
- Group API schemas by bounded context under `app/api/schemas/<context>/`.
- Keep request and response schemas separated by module (for example `request.py`, `response.py`, `saved.py`).
- Do not mix unrelated schema domains in one file.
- Keep schema names explicit to endpoint intent.
