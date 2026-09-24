"""FastAPI application factory."""

from fastapi import FastAPI

from .api.knowledge import create_knowledge_router
from .api.webhook import create_webhook_router
from .core.config import get_settings, validate_settings
from .core.logging import configure_logging
from .graph.graph import build_graph
from .graph.nodes import GraphNodes
from .llm.gemini import GeminiClient
from .rag.service import RagService
from .telegram.bot import TelegramBot


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    validate_settings(settings)
    rag = RagService(settings.knowledge_dir, settings.vectorstore_dir)
    llm = GeminiClient(settings.gemini_api_key, settings.gemini_model)
    graph = build_graph(GraphNodes(settings.clinic_name, llm, rag))
    bot = TelegramBot(settings.telegram_bot_token)
    app = FastAPI(title=f"{settings.clinic_name} AI Assistant")
    app.include_router(create_webhook_router(settings, graph, bot))
    app.include_router(create_knowledge_router(settings.knowledge_dir / "uploads", rag))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()