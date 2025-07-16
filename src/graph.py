import logging
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from src.nodes import (
    read_file_node, router_node, generate_overview_node, feature_extraction_node,
    generate_tech_stack_node, generate_scope_of_work_node, should_continue_from_router,
    regenerate_current, pause_node
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class State(BaseModel):
    file_content: str = ""
    overview: str = ""
    extracted_features: str = ""
    tech_stack: str = ""
    scope_of_work: str = ""
    current_stage: str = "overview"
    user_input: str = ""
    user_feedback: str = ""
    routing_decision: str | None = None

memory = MemorySaver()
workflow = StateGraph(State)

workflow.add_node("read_file", read_file_node)
workflow.add_node("generate_overview", generate_overview_node)
workflow.add_node("feature_extraction", feature_extraction_node)
workflow.add_node("generate_tech_stack", generate_tech_stack_node)
workflow.add_node("generate_scope_of_work", generate_scope_of_work_node)
workflow.add_node("router", router_node)
workflow.add_node("regenerate_current", regenerate_current)
workflow.add_node("pause_node", pause_node)

workflow.add_edge(START, "read_file")
workflow.add_edge("read_file", "generate_overview")

workflow.add_conditional_edges(
    "router",
    should_continue_from_router,
    {
        "feature_extraction": "feature_extraction",
        "generate_tech_stack": "generate_tech_stack",
        "generate_scope_of_work": "generate_scope_of_work",
        "regenerate_current": "regenerate_current",
        "pause_node": "pause_node",
        END: END
    }
)


workflow.add_edge("generate_overview", "router")
workflow.add_edge("feature_extraction", "router")
workflow.add_edge("generate_tech_stack", "router")
workflow.add_edge("generate_scope_of_work", "router")
workflow.add_edge("regenerate_current", "pause_node")
workflow.add_edge("pause_node", "router")

try:
    graph = workflow.compile(checkpointer=memory)
    logger.info("Workflow compiled successfully")
except Exception as e:
    logger.error(f"Error compiling workflow: {e}")
    raise