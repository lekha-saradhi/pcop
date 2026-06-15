from langgraph.graph import StateGraph, END
from ..state import HeraldState
from ..nodes.brief import brief_node
from ..nodes.scribe import scribe_node
from ..nodes.sentinel import sentinel_node
from ..nodes.dispatch import dispatch_node
from ..nodes.chronicle import chronicle_node


def build_herald_graph():
    workflow = StateGraph(HeraldState)

    workflow.add_node("briefing", brief_node)
    workflow.add_node("scribe", scribe_node)
    workflow.add_node("sentinel", sentinel_node)
    workflow.add_node("dispatch", dispatch_node)
    workflow.add_node("chronicle", chronicle_node)

    workflow.set_entry_point("briefing")
    workflow.add_edge("briefing", "scribe")
    workflow.add_edge("scribe", "sentinel")
    workflow.add_edge("sentinel", "dispatch")
    workflow.add_edge("dispatch", "chronicle")
    workflow.add_edge("chronicle", END)

    return workflow.compile()
