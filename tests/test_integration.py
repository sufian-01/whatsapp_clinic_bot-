import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from telegram import Bot, Update

from app.api.knowledge import create_knowledge_router
from app.api.webhook import create_webhook_router
from app.core.auth import create_session
from app.core.config import Settings
from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.rag.service import RagService
from app.telegram.handlers import handle_update


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, content in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + content + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


class FakeLlm:
    def answer(self, system_prompt, user_text, context):
        return f"answer:{user_text}:{context[0] if context else 'none'}"


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append((chat_id, text, reply_markup))


class BrokenBot(FakeBot):
    raw = Bot("123456:TEST")

    async def send_message(self, chat_id, text, reply_markup=None):
        raise RuntimeError("telegram unavailable")


class IntegrationTests(unittest.TestCase):
    def test_upload_without_admin_auth_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rag = RagService(root / "knowledge", root / "vectorstore")
            app = FastAPI()
            app.include_router(create_knowledge_router(root / "knowledge" / "uploads", rag))
            response = TestClient(app).post(
                "/api/v1/knowledge/upload",
                files={"file": ("clinic.pdf", make_pdf("Clinic timing."), "application/pdf")},
            )
            self.assertEqual(response.status_code, 401)

    def test_pdf_upload_is_searchable_without_restart(self):
        token = create_session("admin", role="admin")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rag = RagService(root / "knowledge", root / "vectorstore")
            app = FastAPI()
            app.include_router(create_knowledge_router(root / "knowledge" / "uploads", rag))
            response = TestClient(app).post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("clinic.pdf", make_pdf("Clinic timing is Monday to Saturday 9 AM to 8 PM."), "application/pdf")},
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(rag.search("What is the clinic timing?"))

    def test_invalid_upload_is_rejected(self):
        token = create_session("admin", role="admin")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rag = RagService(root / "knowledge", root / "vectorstore")
            app = FastAPI()
            app.include_router(create_knowledge_router(root / "knowledge", rag))
            response = TestClient(app).post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("notes.txt", b"not pdf", "text/plain")},
            )
            self.assertEqual(response.status_code, 415)

    def test_pdf_without_text_is_rejected(self):
        token = create_session("admin", role="admin")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rag = RagService(root / "knowledge", root / "vectorstore")
            app = FastAPI()
            app.include_router(create_knowledge_router(root / "knowledge", rag))
            response = TestClient(app).post(
                "/api/v1/knowledge/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("empty.pdf", make_pdf(""), "application/pdf")},
            )
            self.assertEqual(response.status_code, 422)

    def test_telegram_handler_runs_graph_and_replies(self):
        graph = build_graph(GraphNodes("Test Clinic", FakeLlm(), RagService(Path(tempfile.mkdtemp()))))
        bot = FakeBot()
        update = Update.de_json({"update_id": 1, "message": {"message_id": 1, "date": 1, "chat": {"id": 42, "type": "private"}, "text": "Hello"}}, Bot("123456:TEST"))
        asyncio.run(handle_update(update, "Test Clinic", graph, bot))
        self.assertEqual(bot.messages[0][0], 42)
        self.assertIn("answer:Hello", bot.messages[0][1])

    def test_webhook_rejects_invalid_secret(self):
        settings = Settings("Test Clinic", "token", "secret", "key", "model", Path("knowledge"), Path("vectorstore"), "")
        app = FastAPI()
        app.include_router(create_webhook_router(settings, object(), object()))
        response = TestClient(app).post("/webhook/telegram", json={})
        self.assertEqual(response.status_code, 403)

    def test_gemini_failure_returns_safe_message(self):
        class BrokenLlm:
            def answer(self, system_prompt, user_text, context):
                raise RuntimeError("provider unavailable")

        graph = build_graph(GraphNodes("Test Clinic", BrokenLlm(), RagService(Path(tempfile.mkdtemp()))))
        result = graph.invoke({"user_text": "Hello"})
        self.assertIn("unable to answer", result["response"])

    def test_telegram_failure_does_not_fail_webhook(self):
        settings = Settings("Test Clinic", "token", "", "key", "model", Path("knowledge"), Path("vectorstore"), "")
        graph = build_graph(GraphNodes("Test Clinic", FakeLlm(), RagService(Path(tempfile.mkdtemp()))))
        app = FastAPI()
        app.include_router(create_webhook_router(settings, graph, BrokenBot()))
        payload = {"update_id": 1, "message": {"message_id": 1, "date": 1, "chat": {"id": 42, "type": "private"}, "text": "Hello"}}
        response = TestClient(app).post("/webhook/telegram", json=payload)
        self.assertEqual(response.status_code, 200)