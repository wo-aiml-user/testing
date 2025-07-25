import logging
import json
from langchain.prompts import ChatPromptTemplate
from utils.prompts import (
    summary_prompt,
    overview_prompt,
    feature_suggestion_prompt,
    tech_stack_prompt,
    work_scope_prompt,
    router_prompt,
)
from utils.helper import time_logger
import re

logger = logging.getLogger(__name__)


@time_logger
def load_initial_state_node(state):
    logger.info("Loading initial state.")
    return state


@time_logger
def generate_initial_summary_node(state):
    user_feedback = state.user_feedback or ""
    try:
        prompt = ChatPromptTemplate.from_template(summary_prompt.template)
        chain = prompt | state.LLM
        output = chain.invoke({"parsed_data": state.file_content, "user_feedback": user_feedback})

        raw = output.content.strip()
        logger.info(f"Raw LLM output for initial summary: {raw}")
        
        if raw.startswith("```json") or raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

        try:
            result = json.loads(raw)
            logger.info(f"Parsed initial summary result: {result}")
            follow_up = result.get("follow_up_question", "") 
            logger.info(f"Follow-up question for initial summary: {follow_up}")
            return {
                "initial_summary": result["summary"],
                "follow_up_questions": str(follow_up).strip(),  
                "current_stage": "initial_summary",
                "user_feedback": ""
            }
        except json.JSONDecodeError:
            logger.warning(f"Initial summary output not JSON:\n{raw}")
            return {
                "initial_summary": raw.strip(),
                "follow_up_questions": "",
                "current_stage": "initial_summary",
                "user_feedback": ""
            }

    except Exception as e:
        logger.error(f"Initial summary generation error: {e}", exc_info=True)
        return {
            "initial_summary": f"Error: {str(e)}",
            "current_stage": "initial_summary",
            "follow_up_questions": ""
        }

@time_logger
def router_node(state):
    user_input = state.user_input.strip()
    current_stage = state.current_stage
    state_updates = {"user_input": "", "user_feedback": "", "routing_decision": None}

    if not user_input:
        return {**state_updates, "routing_decision": "PAUSE", "current_stage": current_stage}

    stage_to_key = {
        "initial_summary": "initial_summary",
        "overview": "overview",
        "features": "extracted_features",
        "tech_stack": "tech_stack",
        "scope_of_work": "scope_of_work"
    }
    current_content = getattr(state, stage_to_key.get(current_stage, ""), "")

    try:
        prompt = ChatPromptTemplate.from_template(router_prompt.template)
        chain = prompt | state.LLM
        output = chain.invoke({
            "user_input": user_input,
            "current_stage": current_stage,
            "current_content": current_content
        })

        action, feedback = "", ""
        for line in output.content.strip().splitlines():
            if line.startswith("ACTION:"):
                action = line.split("ACTION:")[1].strip().upper()
            elif line.startswith("FEEDBACK:"):
                feedback = line.split("FEEDBACK:")[1].strip()

        if action not in {"APPROVE", "EDIT"}:
            action, feedback = "EDIT", user_input

        return {
            **state_updates,
            "routing_decision": action,
            "user_feedback": feedback if action == "EDIT" else "",
            "current_stage": current_stage
        }

    except Exception as e:
        logger.error(f"Router error: {e}", exc_info=True)
        return {
            **state_updates,
            "routing_decision": "EDIT",
            "user_feedback": user_input,
            "current_stage": current_stage
        }


@time_logger
def generate_overview_node(state):
    try:
        prompt = ChatPromptTemplate.from_template(overview_prompt.template)
        chain = prompt | state.LLM
        output = chain.invoke({
            "parsed_data": state.file_content,
            "approved_summary": state.initial_summary,
            "user_feedback": state.user_feedback
        })

        raw = output.content.strip()
        logger.info(f"Raw LLM output for overview: {raw}")
        
        if raw.startswith("```json") or raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

        try:
            result = json.loads(raw)
            logger.info(f"Parsed overview result: {result}")
            follow_up = result.get("follow_up_question", "")  
            logger.info(f"Follow-up question for overview: {follow_up}")
            return {
                "overview": result["overview"],
                "follow_up_questions": str(follow_up).strip(),  
                "current_stage": "overview",
                "user_feedback": ""
            }
        except json.JSONDecodeError:
            logger.warning(f"Overview output not JSON:\n{raw}")
            return {
                "overview": raw.strip(),
                "follow_up_questions": "",
                "current_stage": "overview",
                "user_feedback": ""
            }

    except Exception as e:
        logger.error(f"Overview generation error: {e}", exc_info=True)
        return {
            "overview": f"Error: {str(e)}",
            "current_stage": "overview",
            "follow_up_questions": ""
        }


@time_logger
def feature_extraction_node(state):
    try:
        prompt = ChatPromptTemplate.from_template(feature_suggestion_prompt.template)
        chain = prompt | state.LLM
        output = chain.invoke({
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "user_feedback": state.user_feedback
        })

        raw = output.content.strip()
        logger.info(f"Raw LLM output for features: {raw}")
        
        if raw.startswith("```json") or raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

        try:
            result = json.loads(raw)
            logger.info(f"Parsed feature result: {result}")
            
            features = result.get("features", "")
            follow_up = result.get("follow_up_question", "")  
            
            logger.info(f"Follow-up questions for features: {follow_up}")

            if isinstance(features, list):
                features_str = "\n".join(f"- {f.strip()}" for f in features)
            else:
                features_str = str(features).strip()

            return {
                "extracted_features": features_str,
                "follow_up_questions": str(follow_up).strip(),  
                "current_stage": "features",
                "user_feedback": ""
            }

        except json.JSONDecodeError:
            logger.warning(f"Feature extraction output not JSON:\n{raw}")
            return {
                "extracted_features": raw,
                "follow_up_questions": "", 
                "current_stage": "features",
                "user_feedback": ""
            }

    except Exception as e:
        logger.error(f"Feature extraction error: {e}", exc_info=True)
        return {
            "extracted_features": f"Error: {str(e)}",
            "follow_up_questions": "",  
            "current_stage": "features",
            "user_feedback": ""
        }

@time_logger
def generate_tech_stack_node(state):
    try:
        prompt = ChatPromptTemplate.from_template(tech_stack_prompt.template)
        chain = prompt | state.LLM

        output = chain.invoke({
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "approved_features": state.extracted_features,
            "user_feedback": state.user_feedback
        })

        raw = output.content.strip()
        logger.info(f"Raw LLM output for tech stack: {raw}")

        if raw.startswith("```json") or raw.startswith("```"):
            raw = raw.strip("```json").strip("```").strip()

        try:
            result = json.loads(raw)
            logger.info(f"Parsed tech stack result: {result}")

            tech_stack_dict = result.get("tech_stack", {})
            follow_up_questions = result.get("follow_up_question", "")  
            
            logger.info(f"Follow-up questions for tech stack: {follow_up_questions}")

            for key, value in tech_stack_dict.items():
                if isinstance(value, list):
                    tech_stack_dict[key] = "\n".join(value)

            return {
                "tech_stack": json.dumps(tech_stack_dict, indent=2),
                "follow_up_questions": follow_up_questions,
                "current_stage": "tech_stack",
                "user_feedback": ""
            }

        except json.JSONDecodeError:
            logger.warning("Tech stack output not JSON:\n%s", raw)
            return {
                "tech_stack": raw,
                "follow_up_questions": "",  
                "current_stage": "tech_stack",
                "user_feedback": ""
            }

    except Exception as e:
        logger.error(f"Tech stack generation error: {e}", exc_info=True)
        return {
            "tech_stack": f"Error: {str(e)}",
            "follow_up_questions": "", 
            "current_stage": "tech_stack",
            "user_feedback": ""
        }
    

@time_logger
def generate_scope_of_work_node(state):
    try:
        prompt = ChatPromptTemplate.from_template(work_scope_prompt.template)
        chain = prompt | state.LLM
        output = chain.invoke({
            "parsed_data": state.file_content,
            "approved_summary": state.overview,
            "approved_features": state.extracted_features,
            "approved_tech_stack": state.tech_stack,
            "user_feedback": state.user_feedback
        })

        raw = output.content.strip()
        if raw.startswith("```json") or raw.startswith("```"):
            raw = raw.strip("```json").strip("```").strip()

        try:
            result = json.loads(raw)

            return {
                "scope_of_work": json.dumps(result, indent=2),
                "follow_up_questions": result.get("follow_up_question", ""),
                "current_stage": "scope_of_work",
                "user_feedback": ""
            }

        except json.JSONDecodeError:
            logger.warning(f"Scope of work output not JSON:\n{raw}")
            return {
                "scope_of_work": raw,
                "follow_up_questions": "",
                "current_stage": "scope_of_work",
                "user_feedback": ""
            }

    except Exception as e:
        logger.error(f"Scope of work generation error: {e}", exc_info=True)
        return {
            "scope_of_work": f"Error: {str(e)}",
            "follow_up_questions": "",
            "current_stage": "scope_of_work"
        }

@time_logger
def regenerate_current(state):
    stage_map = {
        "initial_summary": generate_initial_summary_node,
        "overview": generate_overview_node,
        "features": feature_extraction_node,
        "tech_stack": generate_tech_stack_node,
        "scope_of_work": generate_scope_of_work_node
    }
    handler = stage_map.get(state.current_stage)
    return handler(state) if handler else state


@time_logger
def pause_node(state):
    logger.info(f"Paused at stage {state.current_stage}")
    return state


@time_logger
def should_continue_from_router(state):
    decision = state.routing_decision
    stage = state.current_stage
    if decision == "APPROVE":
        return {
            "initial_summary": "generate_overview",
            "overview": "feature_extraction",
            "features": "generate_tech_stack",
            "tech_stack": "generate_scope_of_work",
            "scope_of_work": "END"
        }.get(stage, "pause_node")
    elif decision == "EDIT":
        return "regenerate_current"
    return "pause_node"