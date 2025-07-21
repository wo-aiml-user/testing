

import streamlit as st
from src.graph import graph, State
import uuid
from langchain_community.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers.pdf import PDFPlumberParser
from langchain_core.documents import Document
from utils.helper import get_stage_content
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "workflow_active" not in st.session_state:
    st.session_state.workflow_active = False
if "current_state" not in st.session_state:
    st.session_state.current_state = None


st.title("Work Scope Generator")

uploaded_file = st.file_uploader("Upload a PDF file:", type=["pdf"])

if uploaded_file and not st.session_state.workflow_active:
    try:
        file_bytes = uploaded_file.read()
        blob = Blob.from_data(file_bytes, path=uploaded_file.name)
        parser = PDFPlumberParser(extract_images=True)
        documents: List[Document] = parser.parse(blob)
        file_content = "\n\n".join(doc.page_content for doc in documents)

        initial_state = State(file_content=file_content)
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        graph.invoke(initial_state, config=config, interrupt_after=["pause_node"]) 
        result_state = graph.get_state(config=config)
        st.session_state.current_state = result_state

        overview_content = result_state.values.get("overview", "Error: No overview generated")
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": overview_content 
        })

        st.session_state.workflow_active = True
        st.success("File uploaded and workflow started!")
        st.rerun()

    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        st.error(f"Error: {str(e)}")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if st.session_state.workflow_active:
    user_input = st.chat_input("Your response:")

    if user_input:
        if user_input.lower().strip() == "reset":
            st.session_state.chat_history = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.workflow_active = False
            st.session_state.current_state = None
            st.rerun()
        else:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            try:
                config = {
                    "configurable": {"thread_id": st.session_state.thread_id},
                    "recursion_limit": 50
                }
                graph.update_state(config, {"user_input": user_input})

                graph.invoke(None, config=config, interrupt_after=["pause_node"]) 

                result_state = graph.get_state(config=config)
                st.session_state.current_state = result_state

                logger.info(f"Current stage: {result_state.values.get('current_stage')}, State values: {result_state.values}")

                current_stage = result_state.values.get("current_stage", "overview")
                
                content_to_display = get_stage_content(result_state.values, current_stage)
                workflow_finished = (result_state.next == () and current_stage == "scope_of_work" and result_state.values.get("routing_decision") == "APPROVE")
                
                if workflow_finished:
                    assistant_message = f"{content_to_display}\n\nWorkflow completed."
                    st.session_state.workflow_active = False
                else:
                    assistant_message = content_to_display 
                if assistant_message and (not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != assistant_message):
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": assistant_message
                    })

                st.rerun()

            except Exception as e:
                logger.exception("Error during input processing")
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })
                st.rerun()
    else:
        if st.session_state.workflow_active:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            current_state = graph.get_state(config=config)
            
            current_stage = current_state.values.get("current_stage", "overview")
            content_to_display = get_stage_content(current_state.values, current_stage)

            workflow_finished_display_check = (current_state.next == () and current_stage == "scope_of_work" and current_state.values.get("routing_decision") == "APPROVE")
            
            if workflow_finished_display_check:
                message_to_display = f"{content_to_display}\n\nWorkflow completed."
            else:
                message_to_display = content_to_display
            if message_to_display and (not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != message_to_display):
                if not st.session_state.chat_history or st.session_state.chat_history[-1]["role"] != "user":
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": message_to_display
                    })
            st.rerun()