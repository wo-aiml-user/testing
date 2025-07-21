import logging
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from src.nodes import (
    load_initial_state_node,
    generate_initial_summary_node,  
    router_node,
    generate_overview_node,
    feature_extraction_node,
    generate_tech_stack_node,
    generate_scope_of_work_node,
    should_continue_from_router,
    regenerate_current,
    pause_node
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class State(BaseModel):
    file_content: str = ""
    initial_summary: str = ""
    overview: str = ""
    extracted_features: str = ""
    tech_stack: str = ""
    scope_of_work: str = ""
    current_stage: str = "initial_summary"
    user_input: str = ""
    user_feedback: str = ""
    routing_decision: str | None = None

memory = MemorySaver()
workflow = StateGraph(State)

workflow.add_node("load_initial_state", load_initial_state_node)
workflow.add_node("generate_initial_summary", generate_initial_summary_node)
workflow.add_node("generate_overview", generate_overview_node)
workflow.add_node("router", router_node)
workflow.add_node("feature_extraction", feature_extraction_node)
workflow.add_node("generate_tech_stack", generate_tech_stack_node)
workflow.add_node("generate_scope_of_work", generate_scope_of_work_node)
workflow.add_node("regenerate_current", regenerate_current)
workflow.add_node("pause_node", pause_node)


workflow.set_entry_point("load_initial_state")

workflow.add_conditional_edges(
    "load_initial_state",
    lambda state: "router" if getattr(state, "user_input", None) else "generate_initial_summary",
    {
        "generate_initial_summary": "generate_initial_summary",
        "router": "router"
    }
)

workflow.add_edge("generate_initial_summary", "pause_node")
workflow.add_edge("generate_overview", "pause_node")
workflow.add_edge("feature_extraction", "pause_node")
workflow.add_edge("generate_tech_stack", "pause_node")
workflow.add_edge("generate_scope_of_work", "pause_node")

workflow.add_conditional_edges(
    "router",
    should_continue_from_router,
    {
        "generate_overview": "generate_overview",
        "feature_extraction": "feature_extraction",
        "generate_tech_stack": "generate_tech_stack",
        "generate_scope_of_work": "generate_scope_of_work",
        "regenerate_current": "regenerate_current",
        "pause_node": "pause_node",  
        END: END
    }
)

workflow.add_edge("regenerate_current", "pause_node")

try:
    graph = workflow.compile(checkpointer=memory)
    logger.info("Workflow compiled successfully with new 'initial_summary' stage.")
except Exception as e:
    logger.error(f"Error compiling workflow: {e}", exc_info=True)
    raise