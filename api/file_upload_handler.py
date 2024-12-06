# api/file_upload_handler.py
import logging

from core.data_processing import data_processor  # Import the shared instance
from fastapi import APIRouter, File, UploadFile
from models.schemas import FileUploadResponse

router = APIRouter()

# Configure the logging
logging.basicConfig(
    level=logging.INFO,  # Set the level to INFO or DEBUG to see more logs
    format="%(asctime)s [%(levelname)s] %(message)s",  # Add a timestamp and level to log messages
    handlers=[logging.StreamHandler()],  # Log to console
)
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        filename = file.filename or "uploaded_file.csv"
        logger.info(f"File upload initiated for file: {filename}")

        # Process the file and retrieve the wrapper object
        wrapper = data_processor.process_file(contents, filename)

        # Access attributes directly from the wrapper
        data_id = wrapper.id
        logger.info(
            f"File processed successfully with ID: {data_id}, Filename: {wrapper.filename}"
        )

        return FileUploadResponse(
            message="File processed successfully",
            data_id=data_id,
            filename=wrapper.filename,
        )
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        return FileUploadResponse(
            message=f"File processing failed: {str(e)}", data_id=None, filename=None
        )
