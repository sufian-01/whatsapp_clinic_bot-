"""Build the clinic conversation graph."""

from langgraph.graph import END, START, StateGraph

from .nodes import GraphNodes
from .state import GraphState


def build_graph(nodes: GraphNodes):
    graph = StateGraph(GraphState)
    graph.add_node("classify_intent", nodes.classify)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("doctor_lookup", nodes.doctor_lookup)
    graph.add_node("doctor_list", nodes.doctor_list_node)
    graph.add_node("appointment_start", nodes.appointment_start)
    graph.add_node("appointment_progress", nodes.appointment_progress)
    graph.add_node("appointment_reschedule", nodes.reschedule_node)
    graph.add_node("appointment_cancel", nodes.cancel_node)
    graph.add_node("patient_appointments", nodes.my_appointments_node)
    graph.add_node("report_response", nodes.report_response)
    graph.add_node("human_support", nodes.human_support)
    graph.add_node("answer", nodes.answer)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges("classify_intent", lambda state: state["intent"], {
        "clinic_information": "retrieve",
        "doctor_information": "doctor_lookup",
        "doctor_list": "doctor_list",
        "appointment_booking": "appointment_start",
        "appointment_flow": "appointment_progress",
        "appointment_reschedule": "appointment_reschedule",
        "appointment_cancel": "appointment_cancel",
        "patient_appointments": "patient_appointments",
        "report_enquiry": "report_response",
        "human_support": "human_support",
        "other_help": "answer",
    })
    graph.add_edge("retrieve", "answer")
    graph.add_edge("doctor_lookup", "answer")
    graph.add_edge("doctor_list", END)
    graph.add_edge("appointment_start", END)
    graph.add_edge("appointment_progress", END)
    graph.add_edge("appointment_reschedule", END)
    graph.add_edge("appointment_cancel", END)
    graph.add_edge("patient_appointments", END)
    graph.add_edge("report_response", END)
    graph.add_edge("human_support", END)
    graph.add_edge("answer", END)
    return graph.compile()