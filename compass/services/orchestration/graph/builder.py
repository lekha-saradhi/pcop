from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..state import CompassState
from ..nodes.intake import intake_node
from ..nodes.cognition import cognition_node
from ..nodes.verify import verify_node
from ..nodes.merge import merge_node
from ..nodes.compass_nba import compass_nba_node
from ..nodes.gate import gate_node
from ..nodes.dispatch import dispatch_node
from .edges import route_after_intake, route_after_gate


def build_compass_graph(checkpointer=None):
    graph = StateGraph(CompassState)

    graph.add_node("intake", intake_node)
    graph.add_node("cognition", cognition_node)
    graph.add_node("verify", verify_node)
    graph.add_node("merge", merge_node)
    graph.add_node("compass_nba", compass_nba_node)
    graph.add_node("gate", gate_node)
    graph.add_node("dispatch", dispatch_node)

    graph.add_edge(START, "intake")

    graph.add_conditional_edges("intake", route_after_intake, {
        "cognition": "cognition",
        "verify": "verify",
    })

    graph.add_edge("cognition", "merge")
    graph.add_edge("verify", "merge")

    graph.add_edge("merge", "compass_nba")
    graph.add_edge("compass_nba", "gate")

    graph.add_conditional_edges("gate", route_after_gate, {
        "dispatch": "dispatch",
        "suppressed": END,
    })

    graph.add_edge("dispatch", END)

    return graph.compile(checkpointer=checkpointer)


def build_demo_graph():
    return build_compass_graph(checkpointer=None)
