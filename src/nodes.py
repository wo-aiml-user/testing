from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from utils.prompts import overview_prompt, feature_suggestion_prompt, tech_stack_prompt, work_scope_prompt, router_prompt, summary_prompt
from utils.helper import time_logger
from langgraph.graph import END
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("API_KEY")

try:
    LLM = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key, temperature=0.4)
    logger.info("LLM initialized")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    LLM = None

@time_logger
def load_initial_state_node(state):
    logger.info("Loading initial state into the graph.")
    return state

@time_logger
def generate_initial_summary_node(state):
    """Generates an interactive, high-level summary as the first step."""
    user_feedback = getattr(state, 'user_feedback', "")
    try:
        prompt = ChatPromptTemplate.from_template(summary_prompt.template)
        chain = prompt | LLM
        llm_input = {"parsed_data": state.file_content, "user_feedback": user_feedback}
        logger.info("Invoking LLM for initial interactive summary...")
        output = chain.invoke(llm_input)
        
        return {
            "initial_summary": output.content.strip(),
            "current_stage": "initial_summary",
            "user_feedback": ""
        }
    except Exception as e:
        logger.error(f"Initial summary generation error: {e}", exc_info=True)
        return {"initial_summary": f"Error: {str(e)}", "current_stage": "initial_summary"}
    

@time_logger
def router_node(state):
    user_input = getattr(state, 'user_input', "")
    current_stage = getattr(state, 'current_stage', "overview")

    state_updates = {"user_input": "", "user_feedback": "", "routing_decision": None}

    if not user_input or user_input.strip() == "":
        logger.warning(f"Router received empty user_input at stage {current_stage}. Pausing.")
        return {**state_updates, "routing_decision": "PAUSE", "current_stage": current_stage}

    current_content = ""
    if current_stage == "initial_summary":
        current_content = getattr(state, 'initial_summary', "")
    elif current_stage == "overview":
        current_content = getattr(state, 'overview', "")
    elif current_stage == "features":
        current_content = getattr(state, 'extracted_features', "")
    elif current_stage == "tech_stack":
        current_content = getattr(state, 'tech_stack', "")
    elif current_stage == "scope_of_work":
        current_content = getattr(state, 'scope_of_work', "")

    try:
        prompt = ChatPromptTemplate.from_template(router_prompt.template)
        chain = prompt | LLM
        llm_input = {"user_input": user_input, "current_stage": current_stage, "current_content": current_content}
        logger.info(f"Invoking LLM for router with user_input: '{user_input}', stage: {current_stage}")
        output = chain.invoke(llm_input)
        response = output.content.strip()
        action, feedback = "", ""
        for line in response.split("\n"):
            if line.startswith("ACTION:"):
                action = line.split("ACTION:")[1].strip().upper()
            elif line.startswith("FEEDBACK:"):
                feedback = line.split("FEEDBACK:")[1].strip()

        if action not in ["APPROVE", "EDIT"]:
            action, feedback = "EDIT", user_input
        
        logger.info(f"Router decision: {action}, Feedback: '{feedback}'")
        return {**state_updates, "routing_decision": action, "user_feedback": feedback if action == "EDIT" else "", "current_stage": current_stage}
    except Exception as e:
        logger.error(f"Router error: {e}", exc_info=True)
        return {**state_updates, "routing_decision": "EDIT", "user_feedback": user_input, "current_stage": current_stage}


@time_logger
def generate_overview_node(state):
    user_feedback = getattr(state, 'user_feedback', "")
    try:
        prompt = ChatPromptTemplate.from_template(overview_prompt.template)
        chain = prompt | LLM
        llm_input = {
            "parsed_data": state.file_content, 
            "user_feedback": user_feedback,
            "approved_summary": state.initial_summary 
        }
        
        logger.info(f"Invoking LLM for overview, building on approved summary...")
        output = chain.invoke(llm_input)
        return {
            "overview": output.content.strip(), 
            "current_stage": "overview", 
            "user_feedback": ""
        }
    except Exception as e:
        logger.error(f"Overview generation error: {e}", exc_info=True)
        return {"overview": f"Error: {str(e)}", "current_stage": "overview"}

@time_logger
def feature_extraction_node(state):
    user_feedback = getattr(state, 'user_feedback', "")
    try:
        prompt = ChatPromptTemplate.from_template(feature_suggestion_prompt.template)
        chain = prompt | LLM
        llm_input = {"parsed_data": state.file_content, "approved_summary": state.overview, "user_feedback": user_feedback}
        logger.info(f"Invoking LLM for features...")
        output = chain.invoke(llm_input)
        return {"extracted_features": output.content.strip(), "current_stage": "features", "user_feedback": ""}
    except Exception as e:
        logger.error(f"Feature extraction error: {e}", exc_info=True)
        return {"extracted_features": f"Error: {str(e)}", "current_stage": "features"}

@time_logger
def generate_tech_stack_node(state):
    user_feedback = getattr(state, 'user_feedback', "")
    try:
        prompt = ChatPromptTemplate.from_template(tech_stack_prompt.template)
        chain = prompt | LLM
        llm_input = {
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "approved_features": state.extracted_features,
            "user_feedback": user_feedback
        }
        logger.info(f"Invoking LLM for tech stack...")
        output = chain.invoke(llm_input)
        return {"tech_stack": output.content, "current_stage": "tech_stack", "user_feedback": ""}
    except Exception as e:
        logger.error(f"Tech stack generation error: {e}", exc_info=True)
        return {"tech_stack": f"Error: {str(e)}", "current_stage": "tech_stack"}

@time_logger
def generate_scope_of_work_node(state):
    user_feedback = getattr(state, 'user_feedback', "")
    try:
        prompt = ChatPromptTemplate.from_template(work_scope_prompt.template)
        chain = prompt | LLM
        llm_input = {
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "approved_features": state.extracted_features,
            "approved_tech_stack": state.tech_stack,
            "user_feedback": user_feedback
        }
        logger.info(f"Invoking LLM for scope of work...")
        output = chain.invoke(llm_input)
        return {"scope_of_work": output.content, "current_stage": "scope_of_work", "user_feedback": ""}
    except Exception as e:
        logger.error(f"Scope of work generation error: {e}", exc_info=True)
        return {"scope_of_work": f"Error: {str(e)}", "current_stage": "scope_of_work"}

@time_logger
def regenerate_current(state):
    current_stage = getattr(state, 'current_stage', 'overview')
    logger.info(f"Regenerating current stage: {current_stage}")
    if current_stage == "initial_summary": return generate_initial_summary_node(state)
    if current_stage == "overview": return generate_overview_node(state)
    if current_stage == "features": return feature_extraction_node(state)
    if current_stage == "tech_stack": return generate_tech_stack_node(state)
    if current_stage == "scope_of_work": return generate_scope_of_work_node(state)
    logger.warning(f"Unknown stage for regeneration: {current_stage}.")
    return state

@time_logger
def pause_node(state):
    logger.info(f"Paused at stage {getattr(state, 'current_stage', 'unknown')}. Awaiting next user input.")
    return state

@time_logger
def should_continue_from_router(state):
    routing_decision = getattr(state, 'routing_decision', None)
    current_stage = getattr(state, 'current_stage', 'overview')
    logger.info(f"Routing from stage: {current_stage} with decision: {routing_decision}")
    if routing_decision == "APPROVE":
        if current_stage == "initial_summary": return "generate_overview"
        if current_stage == "overview": return "feature_extraction"
        if current_stage == "features": return "generate_tech_stack"
        if current_stage == "tech_stack": return "generate_scope_of_work"
        if current_stage == "scope_of_work": return END
    elif routing_decision == "EDIT":
        return "regenerate_current"
        
    return "pause_node"