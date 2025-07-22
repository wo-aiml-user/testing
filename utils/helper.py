from langchain_community.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers.pdf import PDFPlumberParser
from langchain_core.documents import Document
from typing import List
from typing import Dict, Any
from threading import Lock
import uuid
import time
from functools import wraps
import logging
import io
import assemblyai as aai
from dotenv import load_dotenv
import tempfile
import os

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

logger = logging.getLogger(__name__)

def transcribe_audio_to_text(audio_bytes: bytes) -> str:
    logger.info("ENTERING: transcribe_audio_to_text")
    try:
        if len(audio_bytes) < 1000:
            logger.warning("Audio file is too small, likely empty or invalid")
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name

        config = aai.TranscriptionConfig(
            speaker_labels=False,
            language_code="en",
            audio_start_from=0,
            audio_end_at=None,
            boost_param="high"
        )
        transcriber = aai.Transcriber()

        logger.debug(f"Transcribing audio file: {temp_file_path}, size: {len(audio_bytes)} bytes")
        transcript = transcriber.transcribe(temp_file_path, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"Transcription failed: {transcript.error}")
            raise Exception(f"Transcription failed: {transcript.error}")

        transcribed_text = transcript.text or ""
        logger.debug(f"Transcribed text: {transcribed_text}")

        os.unlink(temp_file_path)
        logger.info("Temporary audio file deleted")

        if not transcribed_text:
            logger.warning("No speech detected in the audio")
            return ""

        logger.info("Transcription successful")
        return transcribed_text
    except Exception as e:
        logger.error(f"Error in transcribe_audio_to_text: {str(e)}")
        raise

sessions: Dict[str, Dict[str, Any]] = {}
session_lock = Lock()

def time_logger(func):
    """A decorator that logs the execution time of a synchronous function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.info(f"ENTERING: {func_name}")
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"EXITING: {func_name} | DURATION: {duration:.4f} seconds")
        return result
    return wrapper

def async_time_logger(func):
    """A decorator that logs the execution time of an asynchronous function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.info(f"ENTERING ASYNC: {func_name}")

        result = await func(*args, **kwargs)
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"EXITING ASYNC: {func_name} | DURATION: {duration:.4f} seconds")
        return result
    return wrapper

def parse_pdf(file_bytes: bytes, filename: str) -> str:
    blob = Blob.from_data(file_bytes, path=filename)
    parser = PDFPlumberParser(extract_images=True)
    documents: List[Document] = parser.parse(blob)
    return "\n\n".join(doc.page_content for doc in documents)

def get_session(session_id: str) -> Dict[str, Any]:
    """Get or create a session"""
    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = {
                "thread_id": str(uuid.uuid4()),
                "workflow_active": False,
                "workflow_completed": False,
                "chat_history": [],
                "current_state": None
            }
        return sessions[session_id]

def update_session(session_id: str, updates: Dict[str, Any]):
    """Update session data"""
    with session_lock:
        if session_id in sessions:
            sessions[session_id].update(updates)

def get_stage_content(state_values: Dict[str, Any], current_stage: str) -> str:
    """Extract content based on current stage"""
    stage_content_map = {
        "initial_summary": "initial_summary",
        "overview": "overview",
        "features": "extracted_features",
        "tech_stack": "tech_stack",
        "scope_of_work": "scope_of_work"
    }
    
    content_key = stage_content_map.get(current_stage, "initial_summary")
    return state_values.get(content_key, f"Error: No content generated for stage {current_stage}")

def get_stage_message(current_stage: str, content: str, workflow_completed: bool = False) -> str:
    """Generate appropriate message for current stage"""
    if workflow_completed:
        return content
    return content