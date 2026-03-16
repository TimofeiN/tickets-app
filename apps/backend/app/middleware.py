from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3100",
            "http://127.0.0.1:3100",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
