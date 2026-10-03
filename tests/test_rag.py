import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.rag.service import RagService
from app.rag.vectorstore import is_faiss_available, reset_faiss_state


class RagTests(unittest.TestCase):
    def setUp(self):
        reset_faiss_state()

    def tearDown(self):
        reset_faiss_state()

    # -------------------------------------------------------------------------
    # 1. Normal RAG behavior when FAISS is available
    # -------------------------------------------------------------------------

    def test_retrieves_matching_clinic_document(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "faq.md").write_text("The clinic is open on Monday.", encoding="utf-8")
            results = RagService(Path(directory)).search("When is the clinic open?")
        self.assertEqual(len(results), 1)

    def test_does_not_return_unrelated_document(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "faq.md").write_text("The clinic is open on Monday.", encoding="utf-8")
            results = RagService(Path(directory)).search("What is the parking policy?")
        self.assertEqual(results, [])

    def test_normal_rag_is_available_when_faiss_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            service = RagService(Path(directory))
            self.assertTrue(service.is_available())

    # -------------------------------------------------------------------------
    # 2. Application startup and lazy loading verification
    # -------------------------------------------------------------------------

    def test_app_starts_when_faiss_is_unavailable(self):
        """Simulate Windows Application Control blocking _swigfaiss DLL."""
        dll_error = ImportError(
            "DLL load failed while importing _swigfaiss: An Application Control policy has blocked this file."
        )

        with patch("app.rag.vectorstore.get_faiss", return_value=None), \
             patch("app.rag.vectorstore.get_faiss_load_error", return_value=dll_error):
            from app.main import create_app
            app = create_app()
            client = TestClient(app)

            # Health check succeeds
            health_res = client.get("/health")
            self.assertEqual(health_res.status_code, 200)
            self.assertEqual(health_res.json(), {"status": "ok"})

            # Detailed health check shows degraded RAG
            det_res = client.get("/health?details=true")
            self.assertEqual(det_res.status_code, 200)
            self.assertFalse(det_res.json().get("rag_available"))

            # CRM endpoints continue working normally
            auth_res = client.post("/api/admin/auth/login", json={"username": "wrong", "password": "bad"})
            self.assertEqual(auth_res.status_code, 401)

    # -------------------------------------------------------------------------
    # 3. RAG service graceful degradation when FAISS is unavailable
    # -------------------------------------------------------------------------

    def test_rag_service_search_returns_empty_when_faiss_unavailable(self):
        """Search returns empty list without raising an unhandled exception."""
        dll_error = ImportError(
            "DLL load failed while importing _swigfaiss: An Application Control policy has blocked this file."
        )

        with patch("app.rag.vectorstore.get_faiss", return_value=None), \
             patch("app.rag.vectorstore.get_faiss_load_error", return_value=dll_error):
            with tempfile.TemporaryDirectory() as directory:
                Path(directory, "faq.md").write_text("The clinic is open on Monday.", encoding="utf-8")
                service = RagService(Path(directory))
                self.assertFalse(service.is_available())
                results = service.search("When is the clinic open?")
                self.assertEqual(results, [])

    def test_rag_service_ingest_pdf_raises_clear_error_when_faiss_unavailable(self):
        """PDF ingestion raises a clear RuntimeError indicating FAISS is unavailable."""
        dll_error = ImportError(
            "DLL load failed while importing _swigfaiss: An Application Control policy has blocked this file."
        )

        with patch("app.rag.vectorstore.get_faiss", return_value=None), \
             patch("app.rag.vectorstore.get_faiss_load_error", return_value=dll_error):
            with tempfile.TemporaryDirectory() as directory:
                service = RagService(Path(directory), vectorstore_dir=Path(directory) / "vs")
                fake_pdf = Path(directory) / "test.pdf"
                fake_pdf.write_bytes(b"%PDF-fake")
                with self.assertRaises(RuntimeError) as ctx:
                    service.ingest_pdf(fake_pdf)
                self.assertIn("FAISS", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 4. Knowledge API endpoint handles missing FAISS gracefully
    # -------------------------------------------------------------------------

    def test_knowledge_status_endpoint_reports_unavailable_when_faiss_missing(self):
        with patch("app.rag.vectorstore.get_faiss", return_value=None):
            from app.main import create_app
            app = create_app()
            client = TestClient(app)

            status_res = client.get("/api/v1/knowledge/status")
            self.assertEqual(status_res.status_code, 200)
            data = status_res.json()
            self.assertEqual(data["status"], "unavailable")
            self.assertFalse(data["faiss_available"])

    def test_knowledge_upload_returns_503_when_faiss_unavailable(self):
        """Upload endpoint returns HTTP 503 instead of crashing or raising unhandled 500."""
        with patch("app.rag.vectorstore.get_faiss", return_value=None):
            from app.main import create_app
            app = create_app()
            client = TestClient(app)

            fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
            response = client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("guide.pdf", fake_pdf, "application/pdf")},
            )
            self.assertEqual(response.status_code, 503)
            self.assertIn("unavailable", response.json()["detail"].lower())

    # -------------------------------------------------------------------------
    # 5. Telegram conversational graph handles missing FAISS without crashing
    # -------------------------------------------------------------------------

    def test_telegram_graph_retrieve_handles_missing_faiss(self):
        from app.graph.nodes import GraphNodes
        from app.tools.rag_tool import search_clinic_knowledge

        with patch("app.rag.vectorstore.get_faiss", return_value=None):
            with tempfile.TemporaryDirectory() as directory:
                service = RagService(Path(directory))
                # Tool call directly
                results = search_clinic_knowledge(service, "What are the timings?")
                self.assertEqual(results, [])

                # Graph node call
                mock_llm = MagicMock()
                nodes = GraphNodes(clinic_name="Test Clinic", llm=mock_llm, rag=service)
                state = {"user_text": "What are the timings?"}
                updated_state = nodes.retrieve(state)
                self.assertEqual(updated_state["clinic_context"], [])
        self.assertEqual(results, [])