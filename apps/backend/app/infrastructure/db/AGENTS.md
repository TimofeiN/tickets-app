## Repository Rules

### Session lifecycle
- Repositories in request-path code must receive `Session` via constructor injection.
- Do not open DB sessions inside request-path code with `with get_session()`.
- `with get_session()` is allowed for scripts/CLI jobs only.

### Responsibility
- Keep repository methods focused on persistence only.
- Repositories return domain/storage objects and raise typed errors from `app/core/errors.py`.
- Do not put HTTP concerns or response-shaping in repositories.

### Transactions and errors
- Explicitly `rollback` on write-operation failures.
- Convert SQLAlchemy exceptions to project-level `DataAccessError` (or specific typed errors).
- Keep error messages contextual and safe for logs.
