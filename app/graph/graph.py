"""Build the clinic conversation graph."""

from langgraph.graph import END, START, StateGraph

from .nodes import GraphNodes
from .router import should_retrieve
from .state import GraphState


def build_graph(nodes: GraphNodes):
    graph = StateGraph(GraphState)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("answer", nodes.answer)
    graph.add_edge(START, "route")
    graph.add_node("route", lambda state: state)
    graph.add_conditional_edges("route", should_retrieve, {"retrieve": "retrieve", "answer": "answer"})
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()