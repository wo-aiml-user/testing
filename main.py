from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
from typing import Optional
import os
from dotenv import load_dotenv
from utils.helper import transcribe_audio_to_text
from src.graph import graph, END
from utils.logger import setup_logging
from utils.helper import (
    parse_pdf,
    get_session,
    update_session,
    get_stage_content,
    async_time_logger,
)

from langchain_google_genai import ChatGoogleGenerativeAI

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Work Scope Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

LLM = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.getenv("API_KEY"),
    temperature=0.4
)


class SimplifiedSessionResponse(BaseModel):
    content: str
    current_stage: str


class VoiceInputResponse(SimplifiedSessionResponse):
    transcribed_text: Optional[str] = None


class UserInputRequest(BaseModel):
    user_input: str


class InitialInputRequest(BaseModel):
    initial_input: str


@app.post("/sessions/{session_id}/upload", response_model=SimplifiedSessionResponse)
@async_time_logger
async def upload_file(session_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    session = get_session(session_id)
    if session.get("workflow_active"):
        raise HTTPException(
            status_code=409,
            detail=f"Session with ID '{session_id}' already has an active workflow."
        )

    try:
        file_bytes = await file.read()
        file_content = parse_pdf(file_bytes, file.filename)

        initial_state = {"file_content": file_content, "LLM": LLM}
        config = {"configurable": {"thread_id": session["thread_id"]}}

        graph.invoke(initial_state, config=config)
        result_state = graph.get_state(config=config)

        current_stage = result_state.values.get("current_stage", "initial_summary")
        content = get_stage_content(result_state.values, current_stage)

        session_updates = {
            "workflow_active": True,
            "current_state": result_state,
        }
        update_session(session_id, session_updates)

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage,
        )
    except Exception as e:
        logger.error(f"PDF processing failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/sessions/{session_id}/initial-input", response_model=SimplifiedSessionResponse)
@async_time_logger
async def process_initial_input(session_id: str, request: InitialInputRequest):
    session = get_session(session_id)
    if session.get("workflow_active"):
        raise HTTPException(
            status_code=409,
            detail=f"Session with ID '{session_id}' already has an active workflow."
        )

    try:
        file_content = request.initial_input.strip()
        if not file_content:
            raise HTTPException(status_code=400, detail="Input cannot be empty.")

        initial_state = {"file_content": file_content, "LLM": LLM}
        config = {"configurable": {"thread_id": session["thread_id"]}}

        graph.invoke(initial_state, config=config)
        result_state = graph.get_state(config=config)

        current_stage = result_state.values.get("current_stage", "initial_summary")
        content = get_stage_content(result_state.values, current_stage)

        session_updates = {
            "workflow_active": True,
            "current_state": result_state,
        }
        update_session(session_id, session_updates)

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage,
        )
    except Exception as e:
        logger.error(f"Initial input processing failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing initial input: {str(e)}")


@app.post("/sessions/{session_id}/input", response_model=SimplifiedSessionResponse)
@async_time_logger
async def process_user_input(session_id: str, request: UserInputRequest):
    session = get_session(session_id)
    if not session.get("workflow_active"):
        raise HTTPException(status_code=400, detail="No active workflow for this session")

    user_input = request.user_input.strip()
    if user_input.lower() == "reset":
        raise HTTPException(status_code=501, detail="Reset functionality not implemented.")

    config = {"configurable": {"thread_id": session["thread_id"]}}

    try:
        final_run_state = graph.invoke({"user_input": user_input, "LLM": LLM}, config=config)
        workflow_completed = END in final_run_state
        result_state = graph.get_state(config=config)

        current_stage = result_state.values.get("current_stage", "scope_of_work" if workflow_completed else "initial_summary")
        content = get_stage_content(result_state.values, current_stage)

        session_updates = {
            "current_state": result_state,
            "workflow_completed": workflow_completed
        }
        update_session(session_id, session_updates)

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage,
        )
    except Exception as e:
        logger.exception(f"Error processing input for session {session_id}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/sessions/{session_id}/voice-input", response_model=VoiceInputResponse)
@async_time_logger
async def process_voice_input(session_id: str, audio_file: UploadFile = File(...)):
    session = get_session(session_id)

    try:
        audio_bytes = await audio_file.read()
        if len(audio_bytes) < 1000:
            raise HTTPException(status_code=400, detail="Audio file is too small or empty.")

        transcribed_text = transcribe_audio_to_text(audio_bytes)
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="No speech detected in the audio.")

        config = {"configurable": {"thread_id": session["thread_id"]}}

        if not session.get("workflow_active"):
            initial_state = {"file_content": transcribed_text, "LLM": LLM}
            graph.invoke(initial_state, config=config)
        else:
            graph.invoke({"user_input": transcribed_text, "LLM": LLM}, config=config)

        result_state = graph.get_state(config=config)
        workflow_completed = END in result_state

        current_stage = result_state.values.get("current_stage", "scope_of_work" if workflow_completed else "initial_summary")
        content = get_stage_content(result_state.values, current_stage)

        session_updates = {
            "workflow_active": True,
            "workflow_completed": workflow_completed,
            "current_state": result_state,
        }
        update_session(session_id, session_updates)

        return VoiceInputResponse(
            content=content,
            current_stage=current_stage,
            transcribed_text=transcribed_text
        )
    except Exception as e:
        logger.exception(f"Error processing voice input for session {session_id}")
        raise HTTPException(status_code=500, detail=f"Voice input error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
