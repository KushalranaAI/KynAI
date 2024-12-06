# api/endpoints.py
from fastapi import APIRouter
from api.file_upload_handler import router as upload_router
from api.chat_handler import router as chat_router

router = APIRouter()
router.include_router(upload_router, prefix="/file")
router.include_router(chat_router)
