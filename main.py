from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.graph import graph, State 
from utils.session import parse_pdf   
import uuid
import logging
from typing import List, Dict, Any
from utils.session import get_session, update_session, get_stage_content, get_stage_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Work Scope Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionResponse(BaseModel):
    session_id: str
    message: str
    current_stage: str
    content: str
    workflow_active: bool
    workflow_completed: bool

class UserInputRequest(BaseModel):
    user_input: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatHistoryResponse(BaseModel):
    chat_history: List[ChatMessage]
    current_stage: str
    workflow_active: bool
    workflow_completed: bool

@app.post("/api/upload", response_model=SessionResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload PDF file and start workflow"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    session_id = str(uuid.uuid4())
    session = get_session(session_id)
    
    try:

        file_bytes = await file.read()
        file_content = parse_pdf(file_bytes, file.filename)
        initial_state = State(file_content=file_content)
        config = {"configurable": {"thread_id": session["thread_id"]}}
        
        graph.invoke(initial_state, config=config, interrupt_after=["generate_overview"])
        
        result_state = graph.get_state(config=config)
        current_stage = result_state.values.get("current_stage", "overview")
        content = get_stage_content(result_state.values, current_stage)
        message = get_stage_message(current_stage, content)
        session_updates = {
            "workflow_active": True,
            "current_state": result_state,
            "chat_history": [{"role": "assistant", "content": message}]
        }
        update_session(session_id, session_updates)
        
        logger.info(f"File uploaded successfully for session {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            message=message,
            current_stage=current_stage,
            content=content,
            workflow_active=True,
            workflow_completed=False
        )
        
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/api/sessions/{session_id}/input", response_model=SessionResponse)
async def process_user_input(session_id: str, request: UserInputRequest):
    """Process user input and continue workflow"""
    session = get_session(session_id)
    
    if not session["workflow_active"]:
        raise HTTPException(status_code=400, detail="No active workflow for this session")
    
    user_input = request.user_input.strip()
    if user_input.lower() == "reset":
        session_updates = {
            "thread_id": str(uuid.uuid4()),
            "workflow_active": False,
            "workflow_completed": False,
            "chat_history": [],
            "current_state": None
        }
        update_session(session_id, session_updates)
        
        return SessionResponse(
            session_id=session_id,
            message="Session reset. Please upload a new file to start over.",
            current_stage="overview",
            content="",
            workflow_active=False,
            workflow_completed=False
        )
    
    try:
        session["chat_history"].append({"role": "user", "content": user_input})
        
        config = {
            "configurable": {"thread_id": session["thread_id"]}
        }
        graph.update_state(config, {"user_input": user_input})
        graph.invoke(None, config=config, interrupt_after=[
            "generate_overview", 
            "feature_extraction", 
            "generate_tech_stack", 
            "generate_scope_of_work", 
            "regenerate_current"
        ])
        
        result_state = graph.get_state(config=config)
        current_stage = result_state.values.get("current_stage", "overview")
        content = get_stage_content(result_state.values, current_stage)
        workflow_completed = result_state.next == () and current_stage == "scope_of_work"
        
        message = get_stage_message(current_stage, content, workflow_completed)
        session_updates = {
            "current_state": result_state,
            "workflow_completed": workflow_completed
        }
        session["chat_history"].append({"role": "assistant", "content": message})
        update_session(session_id, session_updates)
        
        logger.info(f"User input processed for session {session_id}, stage: {current_stage}")
        
        return SessionResponse(
            session_id=session_id,
            message=message,
            current_stage=current_stage,
            content=content,
            workflow_active=session["workflow_active"],
            workflow_completed=workflow_completed
        )
        
    except Exception as e:
        logger.exception(f"Error processing input for session {session_id}")
        error_message = f"Error: {str(e)}"
        session["chat_history"].append({"role": "assistant", "content": error_message})
        update_session(session_id, {"chat_history": session["chat_history"]})
        
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/api/sessions/{session_id}/chat", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    session = get_session(session_id)
    
    current_stage = "overview"
    if session["current_state"]:
        current_stage = session["current_state"].values.get("current_stage", "overview")
    
    return ChatHistoryResponse(
        chat_history=session["chat_history"],
        current_stage=current_stage,
        workflow_active=session["workflow_active"],
        workflow_completed=session["workflow_completed"]
    )

@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status"""
    session = get_session(session_id)
    
    current_stage = "overview"
    if session["current_state"]:
        current_stage = session["current_state"].values.get("current_stage", "overview")
    
    return {
        "session_id": session_id,
        "workflow_active": session["workflow_active"],
        "workflow_completed": session["workflow_completed"],
        "current_stage": current_stage,
        "chat_history_length": len(session["chat_history"])
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")