from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.search import router as search_router
from app.core.logging import configure_logging
from app.middleware import setup_middleware

configure_logging()
app = FastAPI(title="tickets_app backend", version="0.1.0")
setup_middleware(app)
app.include_router(health_router)
app.include_router(search_router)
