# main.py

from api.endpoints import router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(router)
