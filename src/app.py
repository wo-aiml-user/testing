import streamlit as st
from graph import graph, State
import uuid
from langchain_community.document_loaders.blob_loaders import Blob
from langchain_community.document_loaders.parsers.pdf import PDFPlumberParser
from langchain_core.documents import Document
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

        graph.invoke(initial_state, config=config, interrupt_after=["generate_overview"])
        
        result_state = graph.get_state(config=config)
        st.session_state.current_state = result_state

        overview = result_state.values.get("overview", "Error: No overview generated")
        logger.info(f"Retrieved overview: {overview}") 
        message = f"Here's the project overview:\n\n{overview}\n\nDo you approve this overview or would you like any changes?"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": message
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

                current_state = graph.get_state(config=config)
                if current_state.next != ("pause_node",):
                    graph.invoke(None, config=config, interrupt_after=["generate_overview", "feature_extraction", "generate_tech_stack", "generate_scope_of_work", "regenerate_current"])

                result_state = graph.get_state(config=config)
                st.session_state.current_state = result_state

                logger.info(f"Current stage: {result_state.values.get('current_stage')}, State values: {result_state.values}")

                current_stage = result_state.values.get("current_stage", "overview")
                if current_stage == "overview":
                    content = result_state.values.get("overview", "Error: No overview generated")
                    message = f"Here's the project overview:\n\n{content}\n\nDo you approve this overview or would you like any changes?"
                elif current_stage == "features":
                    content = result_state.values.get("extracted_features", "Error: No features generated")
                    message = f"Here are the suggested features:\n\n{content}\n\nDo you approve these features or want modifications?"
                elif current_stage == "tech_stack":
                    content = result_state.values.get("tech_stack", "Error: No tech stack generated")
                    message = f"Here's the recommended tech stack:\n\n{content}\n\nDo you approve this tech stack or want changes?"
                elif current_stage == "scope_of_work":
                    content = result_state.values.get("scope_of_work", "Error: No scope of work generated")
                    message = f"Here's the complete scope of work:\n\n{content}\n\nDo you approve this scope or want revisions?"
                else:
                    message = "Waiting for your input to proceed..."

                if result_state.next == ():
                    if current_stage == "scope_of_work":
                        message = f"Here's the complete scope of work:\n\n{content}\n\nWorkflow completed! Type 'reset' or upload a new file to start over."
                    else:
                        message = "Workflow completed! Type 'reset' or upload a new file to start over."

                if message:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": message
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
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        current_state = graph.get_state(config=config)
        if current_state.next == ("pause_node",):
            current_stage = current_state.values.get("current_stage", "overview")
            if current_stage == "overview":
                content = current_state.values.get("overview", "Error: No overview generated")
                message = f"\n\n{content}\n\n"
            elif current_stage == "features":
                content = current_state.values.get("extracted_features", "Error: No features generated")
                message = f"\n\n{content}\n\n"
            elif current_stage == "tech_stack":
                content = current_state.values.get("tech_stack", "Error: No tech stack generated")
                message = f"\n\n{content}\n\n"
            elif current_stage == "scope_of_work":
                content = current_state.values.get("scope_of_work", "Error: No scope of work generated")
                message = f"\n\n{content}\n\n"
            else:
                message = "Waiting for your input to proceed..."

            if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != message:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": message
                })
            st.rerun()