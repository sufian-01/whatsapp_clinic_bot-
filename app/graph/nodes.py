"""Pure graph nodes with injected collaborators."""

from ..core.prompts import load_system_prompt
from ..llm.gemini import GeminiClient
from ..rag.service import RagService
from ..tools.rag_tool import search_clinic_knowledge
from .state import GraphState
import logging


logger = logging.getLogger(__name__)


class GraphNodes:
    def __init__(self, clinic_name: str, llm: GeminiClient, rag: RagService) -> None:
        self._clinic_name = clinic_name
        self._llm = llm
        self._rag = rag

    def retrieve(self, state: GraphState) -> GraphState:
        logger.info("RAG tool invoked")
        context = search_clinic_knowledge(self._rag, state.get("user_text", ""))
        logger.info("Retrieved %d chunks", len(context))
        return {**state, "clinic_context": context}

    def answer(self, state: GraphState) -> GraphState:
        context = state.get("clinic_context", [])
        try:
            response = self._llm.answer(load_system_prompt(self._clinic_name), state.get("user_text", ""), context)
        except Exception:
            logger.exception("Gemini completion failed")
            response = "I’m sorry, I’m unable to answer right now. Please try again shortly."
        logger.info("Gemini response generated")
        return {**state, "response": response}