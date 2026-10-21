"""Build the clinic conversation graph with deterministic threading and checkpoints."""

import re
import uuid
from typing import Any, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import GraphNodes
from .state import GraphState


def build_whatsapp_thread_id(clinic_id: str, phone: str) -> str:
    """Generate deterministic LangGraph thread_id for multi-tenant isolation.
    
    Format: clinic:{clinic_id}:whatsapp:{phone_e164}
    Guarantees that conversations for the same patient across different clinics never leak,
    and same patient within the same clinic preserves state deterministically.
    """
    cid = str(clinic_id or "default").strip()
    clean_phone = re.sub(r"[^\d+]", "", str(phone or "").strip())
    if not clean_phone:
        clean_phone = "anonymous"
    return f"clinic:{cid}:whatsapp:{clean_phone}"


class CheckpointedGraph:
    """Runnable wrapper providing automatic thread_id configuration for checkpointers.
    
    Ensures that multi-turn conversations retain LangGraph checkpoints across turns
    keyed by tenant and patient phone, while also gracefully handling one-shot calls.
    """

    def __init__(self, inner: Any, checkpointer: Optional[Any] = None) -> None:
        self._inner = inner
        self._checkpointer = checkpointer

    def invoke(self, state: Any, config: Optional[dict] = None, **kwargs: Any) -> Any:
        if not isinstance(state, dict):
            return self._inner.invoke(state, config=config, **kwargs)

        cfg = dict(config) if config else {}
        configurable = dict(cfg.get("configurable", {}))

        if "thread_id" not in configurable:
            cid = state.get("tenant_id") or state.get("clinic_id") or "default"
            phone = state.get("phone") or state.get("patient_phone") or state.get("chat_id")
            configurable["thread_id"] = build_whatsapp_thread_id(cid, phone)

        cfg["configurable"] = configurable
        return self._inner.invoke(state, config=cfg, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def build_graph(nodes: GraphNodes, checkpointer: Optional[Any] = None) -> CheckpointedGraph:
    graph = StateGraph(GraphState)
    graph.add_node("classify_intent", nodes.classify)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("doctor_lookup", nodes.doctor_lookup)
    graph.add_node("doctor_list", nodes.doctor_list_node)
    graph.add_node("appointment_start", nodes.appointment_start)
    graph.add_node("appointment_progress", nodes.appointment_progress)
    graph.add_node("appointment_draft_cancel", nodes.appointment_draft_cancel)
    graph.add_node("appointment_reschedule", nodes.reschedule_node)
    graph.add_node("appointment_cancel", nodes.cancel_node)
    graph.add_node("patient_appointments", nodes.my_appointments_node)
    graph.add_node("report_response", nodes.report_response)
    graph.add_node("human_support", nodes.human_support)
    graph.add_node("answer", nodes.answer)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges("classify_intent", lambda state: state["intent"], {
        "greeting": "answer",
        "clinic_information": "retrieve",
        "doctor_information": "doctor_lookup",
        "doctor_list": "doctor_list",
        "appointment_booking": "appointment_start",
        "appointment_flow": "appointment_progress",
        "appointment_draft_cancel": "appointment_draft_cancel",
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
    graph.add_edge("appointment_draft_cancel", END)
    graph.add_edge("appointment_reschedule", END)
    graph.add_edge("appointment_cancel", END)
    graph.add_edge("patient_appointments", END)
    graph.add_edge("report_response", END)
    graph.add_edge("human_support", END)
    graph.add_edge("answer", END)

    cp = checkpointer if checkpointer is not None else MemorySaver()
    compiled = graph.compile(checkpointer=cp)
    return CheckpointedGraph(compiled, checkpointer=cp)
