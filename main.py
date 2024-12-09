# src/main.py

from fastapi import FastAPI

from src.app.imp_practices.route import main_router
from src.app.stream_data.route import stream_router
from src.app.stream_data.socket import socket_router
from src.app.user.middleware import setup_middleware
from src.app.user.mongo import mongorouter
from src.app.user.route import user_router

app = FastAPI()

setup_middleware(app)
app.include_router(user_router)
app.include_router(stream_router)
app.include_router(socket_router)
app.include_router(mongorouter)

app.include_router(main_router)
__all__ = ["app"]
