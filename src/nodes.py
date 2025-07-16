from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from utils.prompts import overview_prompt, feature_suggestion_prompt, tech_stack_prompt, work_scope_prompt, router_prompt
import os
import logging

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

def read_file_node(state):
    """Pass through file_content from app.py"""
    file_content = state.file_content
    logger.info(f"Processing file content: {len(file_content)} characters")
    return {"file_content": file_content, "current_stage": "overview"}

def router_node(state):
    """Route user input to appropriate action"""
    user_input = getattr(state, "user_input", "")
    current_stage = getattr(state, "current_stage", "overview")

    state_updates = {"user_input": "", "user_feedback": "", "routing_decision": None}

    if not user_input or user_input.strip() == "":
        logger.info(f"Router received empty user_input at stage {current_stage}. Signaling graph to wait for user input.")
        return {**state_updates, "current_stage": current_stage}

    current_content = ""
    if current_stage == "overview":
        current_content = getattr(state, "overview", "")
    elif current_stage == "features":
        current_content = getattr(state, "extracted_features", "")
    elif current_stage == "tech_stack":
        current_content = getattr(state, "tech_stack", "")
    elif current_stage == "scope_of_work":
        current_content = getattr(state, "scope_of_work", "")

    try:
        prompt = ChatPromptTemplate.from_template(router_prompt.template)
        chain = prompt | LLM

        llm_input = {
            "user_input": user_input,
            "current_stage": current_stage,
            "current_content": current_content
        }
        logger.info(f"Invoking LLM for router with user_input: '{user_input}', stage: {current_stage}")

        output = chain.invoke(llm_input)

        response = output.content.strip()
        action = ""
        feedback = ""

        for line in response.split("\n"):
            if line.startswith("ACTION:"):
                action = line.split("ACTION:")[1].strip().upper()
            elif line.startswith("FEEDBACK:"):
                feedback = line.split("FEEDBACK:")[1].strip()

        if action not in ["APPROVE", "EDIT"]:
            logger.warning(f"Router LLM returned invalid action: '{action}'. Defaulting to EDIT.")
            action = "EDIT"

        logger.info(f"Router decision: {action}, Feedback: '{feedback}'")

        return {
            **state_updates,
            "routing_decision": action,
            "user_feedback": feedback if action == "EDIT" else "",
            "current_stage": current_stage
        }

    except Exception as e:
        logger.error(f"Router error: {e}")
        return {
            **state_updates,
            "routing_decision": "EDIT",
            "user_feedback": user_input,
            "current_stage": current_stage
        }

def generate_overview_node(state):
    """Generate overview using LLM with detailed logging"""
    user_feedback = getattr(state, "user_feedback", "")
    
    try:
        prompt = ChatPromptTemplate.from_template(overview_prompt.template)
        chain = prompt | LLM
        
        llm_input = {
            "parsed_data": state.file_content, 
            "user_feedback": user_feedback
        }
        
        logger.info(f"Invoking LLM for overview with input size: {len(llm_input['parsed_data'])} characters")
        
        output = chain.invoke(llm_input)
        logger.info(f"LLM output: {output.content if output and hasattr(output, 'content') else 'None'}")
        
        if output and hasattr(output, 'content') and output.content and output.content.strip():
            logger.info("Overview generated successfully")
            return {
                "overview": output.content.strip(),
                "current_stage": "overview",
                "user_feedback": ""
            }
        else:
            logger.error("Empty or invalid LLM output")
            return {
                "overview": "Error: Empty or invalid LLM response",
                "current_stage": "overview",
                "user_feedback": ""
            }
        
    except Exception as e:
        logger.error(f"Overview generation error: {e}")
        return {
            "overview": f"Error: {str(e)}",
            "current_stage": "overview",
            "user_feedback": ""
        }

def feature_extraction_node(state):
    """Extract features using LLM"""
    user_feedback = getattr(state, "user_feedback", "")
    
    try:
        prompt = ChatPromptTemplate.from_template(feature_suggestion_prompt.template)
        chain = prompt | LLM
        
        llm_input = {
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "user_feedback": user_feedback
        }
        
        logger.info(f"Invoking LLM for features with input size: {len(llm_input['parsed_data'])} characters")
        output = chain.invoke(llm_input)
        logger.info("Features extracted")
        
        return {
            "extracted_features": output.content.strip(),
            "current_stage": "features",
            "user_feedback": ""
        }
        
    except Exception as e:
        logger.error(f"Feature extraction error: {e}")
        return {
            "extracted_features": f"Error: {str(e)}",
            "current_stage": "features",
            "user_feedback": ""
        }

def generate_tech_stack_node(state):
    """Generate tech stack using LLM"""
    user_feedback = getattr(state, "user_feedback", "")
    
    try:
        prompt = ChatPromptTemplate.from_template(tech_stack_prompt.template)
        chain = prompt | LLM
        
        llm_input = {
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "approved_features": state.extracted_features,
            "user_feedback": user_feedback
        }
        
        logger.info(f"Invoking LLM for tech stack with input size: {len(llm_input['parsed_data'])} characters")
        output = chain.invoke(llm_input)
        logger.info("Tech stack generated")
        
        return {
            "tech_stack": output.content,
            "current_stage": "tech_stack",
            "user_feedback": ""
        }
        
    except Exception as e:
        logger.error(f"Tech stack generation error: {e}")
        return {
            "tech_stack": f"Error: {str(e)}",
            "current_stage": "tech_stack",
            "user_feedback": ""
        }

def generate_scope_of_work_node(state):
    """Generate scope of work using LLM"""
    user_feedback = getattr(state, "user_feedback", "")
    
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
        
        logger.info(f"Invoking LLM for scope of work with input size: {len(llm_input['parsed_data'])} characters")
        output = chain.invoke(llm_input)
        logger.info("Scope of work generated")
        
        return {
            "scope_of_work": output.content,
            "current_stage": "scope_of_work",
            "user_feedback": ""
        }
        
    except Exception as e:
        logger.error(f"Scope of work generation error: {e}")
        return {
            "scope_of_work": f"Error: {str(e)}",
            "current_stage": "scope_of_work",
            "user_feedback": ""
        }

def regenerate_current(state):
    """
    Function to trigger regeneration of the current stage based on user feedback.
    This acts as a router within the nodes, calling the appropriate generator node.
    """
    current_stage = getattr(state, "current_stage", "overview")
    logger.info(f"Regenerating current stage: {current_stage}")

    if current_stage == "overview":
        result = generate_overview_node(state)
    elif current_stage == "features":
        result = feature_extraction_node(state)
        logger.info(f"Regenerated features: {result.get('extracted_features', 'No features generated')}")
    elif current_stage == "tech_stack":
        result = generate_tech_stack_node(state)
    elif current_stage == "scope_of_work":
        result = generate_scope_of_work_node(state)
    else:
        logger.warning(f"Unknown stage for regeneration: {current_stage}. Returning current state unchanged.")
        return state

    return result

def pause_node(state):
    """A node that pauses the graph to wait for user input."""
    logger.info(f"Paused at stage {state.current_stage}. Waiting for user input via Streamlit.")
    return state.copy(
        update={
            "routing_decision": None,
            "user_input": "",
            "user_feedback": ""
        }
    )


def should_continue_from_router(state):
    """Determine next action based on router decision"""
    routing_decision = getattr(state, "routing_decision", None)
    current_stage = getattr(state, "current_stage", "overview")
    
    logger.info(f"should_continue_from_router: Router decision: '{routing_decision}', Current stage: {current_stage}")
    
    if routing_decision == "APPROVE":
        if current_stage == "overview":
            return "feature_extraction"
        elif current_stage == "features":
            return "generate_tech_stack"
        elif current_stage == "tech_stack":
            return "generate_scope_of_work"
        elif current_stage == "scope_of_work":
            return END
        else:
            logger.warning(f"Unexpected current_stage for APPROVE: {current_stage}. Ending workflow.")
            return END
    elif routing_decision == "EDIT":
        return "regenerate_current"
    elif routing_decision is None:
        logger.info(f"Router has no decision; waiting for user input. Transitioning to pause_node.")
        return "pause_node"
    else:
        logger.error(f"Unknown routing decision encountered: '{routing_decision}'. Ending workflow unexpectedly.")
        return END