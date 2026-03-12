## Backend Rules

- Keep route handlers thin.
- Keep business logic in `application` or `domain`, not in routers.
- Keep external API and DB access in `infrastructure`.
- Follow existing backend patterns before introducing new structure.
- Add or update tests for behavior changes.
