from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
from typing import List
from utils.helper import transcribe_audio_to_text
from src.graph import graph, END 
from utils.logger import setup_logging
from utils.helper import (
    parse_pdf,
    get_session,
    update_session,
    get_stage_content,
    async_time_logger,
    sessions
)

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Work Scope Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimplifiedSessionResponse(BaseModel):
    content: str
    current_stage: str

class UserInputRequest(BaseModel):
    user_input: str

class InitialInputRequest(BaseModel):
    initial_input: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ConsolidatedChatResponse(BaseModel):
    session_id: str
    current_stage: str
    chat_history: List[ChatMessage]
    chat_history_length: int

@app.post("/sessions/{session_id}/upload", response_model=SimplifiedSessionResponse)
@async_time_logger
async def upload_file(session_id: str, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    if session_id in sessions:
        raise HTTPException(
            status_code=409,
            detail=f"Session with ID '{session_id}' already exists. Please use a new, unique session ID to start a new workflow."
        )

    session = get_session(session_id)

    try:
        file_bytes = await file.read()
        file_content = parse_pdf(file_bytes, file.filename)
        initial_state = {"file_content": file_content}
        config = {"configurable": {"thread_id": session["thread_id"]}}
        
        graph.invoke(initial_state, config=config)
        result_state = graph.get_state(config=config)
        
        current_stage = result_state.values.get("current_stage", "initial_summary")
        content = get_stage_content(result_state.values, current_stage)
        
        session_updates = {
            "workflow_active": True,
            "current_state": result_state,
            "chat_history": [{"role": "assistant", "content": content}]
        }
        update_session(session_id, session_updates)

        logger.info(f"File uploaded, new workflow started for session {session_id}.")

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage
        )
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code == 409:
            raise e
        logger.error(f"PDF processing failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/sessions/{session_id}/initial-input", response_model=SimplifiedSessionResponse)
@async_time_logger
async def process_initial_input(session_id: str, request: InitialInputRequest):
    """Process initial chat input to start the workflow at summary node."""
    if session_id in sessions and sessions[session_id].get("workflow_active"):
        raise HTTPException(
            status_code=409,
            detail=f"Session with ID '{session_id}' already has an active workflow. Please use a new session ID."
        )

    session = get_session(session_id)

    try:
        file_content = request.initial_input.strip()
        if not file_content:
            raise HTTPException(status_code=400, detail="Input cannot be empty.")

        initial_state = {"file_content": file_content}
        config = {"configurable": {"thread_id": session["thread_id"]}}
        
        graph.invoke(initial_state, config=config)
        result_state = graph.get_state(config=config)
        
        current_stage = result_state.values.get("current_stage", "initial_summary")
        content = get_stage_content(result_state.values, current_stage)
        
        session_updates = {
            "workflow_active": True,
            "current_state": result_state,
            "chat_history": [
                {"role": "user", "content": file_content},
                {"role": "assistant", "content": content}
            ]
        }
        update_session(session_id, session_updates)

        logger.info(f"Initial chat input processed for session {session_id}. New stage: {current_stage}")

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage
        )
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code == 409:
            raise e
        logger.error(f"Initial input processing failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing initial input: {str(e)}")

@app.post("/sessions/{session_id}/input", response_model=SimplifiedSessionResponse)
@async_time_logger
async def process_user_input(session_id: str, request: UserInputRequest):
    """Process user input and continue the workflow."""
    session = get_session(session_id)
    if not session.get("workflow_active"):
        raise HTTPException(status_code=400, detail="No active workflow for this session")

    user_input = request.user_input.strip()

    if user_input.lower() == "reset":
        raise HTTPException(status_code=501, detail="Reset functionality not implemented.")

    session["chat_history"].append({"role": "user", "content": user_input})
    config = {"configurable": {"thread_id": session["thread_id"]}}
    
    try:
        final_run_state = graph.invoke({"user_input": user_input}, config=config)
        workflow_completed = END in final_run_state

        result_state = graph.get_state(config=config)
        
        current_stage = result_state.values.get("current_stage", "scope_of_work" if workflow_completed else "initial_summary")
        content = get_stage_content(result_state.values, current_stage)
        
        session_updates = {
            "current_state": result_state,
            "workflow_completed": workflow_completed
        }
        session["chat_history"].append({"role": "assistant", "content": content})
        update_session(session_id, session_updates)

        logger.info(f"User input processed for session {session_id}. New stage: {current_stage}. Completed: {workflow_completed}")

        return SimplifiedSessionResponse(
            content=content,
            current_stage=current_stage
        )
    except Exception as e:
        logger.exception(f"Error processing input for session {session_id}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/sessions/{session_id}/voice-input", response_model=SimplifiedSessionResponse)
@async_time_logger
async def process_voice_input(session_id: str, audio_file: UploadFile = File(...)):
    """Accepts audio input, transcribes it, and processes as initial or user input."""
    session = get_session(session_id)

    try:
        audio_bytes = await audio_file.read()
        if len(audio_bytes) < 1000:
            raise HTTPException(status_code=400, detail="Audio file is too small or empty.")

        transcribed_text = transcribe_audio_to_text(audio_bytes)
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="No speech detected in the audio.")

        if not session.get("workflow_active"):
            if session_id in sessions and sessions[session_id].get("workflow_active"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Session with ID '{session_id}' already has an active workflow."
                )

            initial_state = {"file_content": transcribed_text}
            config = {"configurable": {"thread_id": session["thread_id"]}}
            
            graph.invoke(initial_state, config=config)
            result_state = graph.get_state(config=config)
            
            current_stage = result_state.values.get("current_stage", "initial_summary")
            content = get_stage_content(result_state.values, current_stage)
            
            session_updates = {
                "workflow_active": True,
                "current_state": result_state,
                "chat_history": [
                    {"role": "user", "content": transcribed_text},
                    {"role": "assistant", "content": content}
                ]
            }
            update_session(session_id, session_updates)

            logger.info(f"Voice input processed as initial input for session {session_id}. Stage: {current_stage}")

            return SimplifiedSessionResponse(
                content=content,
                current_stage=current_stage
            )
        else:
            session["chat_history"].append({"role": "user", "content": transcribed_text})
            config = {"configurable": {"thread_id": session["thread_id"]}}

            final_run_state = graph.invoke({"user_input": transcribed_text}, config=config)
            workflow_completed = END in final_run_state

            result_state = graph.get_state(config=config)
            current_stage = result_state.values.get("current_stage", "scope_of_work" if workflow_completed else "initial_summary")
            content = get_stage_content(result_state.values, current_stage)

            session_updates = {
                "current_state": result_state,
                "workflow_completed": workflow_completed
            }
            session["chat_history"].append({"role": "assistant", "content": content})
            update_session(session_id, session_updates)

            logger.info(f"Voice input processed for session {session_id}. Stage: {current_stage}")

            return SimplifiedSessionResponse(
                content=content,
                current_stage=current_stage
            )
    except Exception as e:
        logger.exception(f"Error processing voice input for session {session_id}")
        raise HTTPException(status_code=500, detail=f"Voice input error: {str(e)}")

@app.get("/sessions/{session_id}/chat", response_model=ConsolidatedChatResponse) 
@async_time_logger
async def get_chat_history(session_id: str):
    """Get chat history and current status for a session."""
    session = get_session(session_id)

    if not session.get("workflow_active"):
        return ConsolidatedChatResponse(
            session_id=session_id,
            current_stage="inactive",
            chat_history=[],
            chat_history_length=0
        )
        
    current_stage = "initial_summary"
    if session.get("current_state"):
        current_stage = session["current_state"].values.get("current_stage", "initial_summary")
    if session.get("workflow_completed", False):
        current_stage = "completed"
        
    chat_history = session.get("chat_history", [])

    return ConsolidatedChatResponse(
        session_id=session_id,
        current_stage=current_stage,
        chat_history=chat_history,
        chat_history_length=len(chat_history)
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)