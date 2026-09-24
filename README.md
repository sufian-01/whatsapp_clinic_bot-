# Telegram AI Clinic Assistant

This phase provides the production foundation for one clinic:

```text
Telegram update -> FastAPI webhook -> LangGraph -> Gemini -> optional RAG -> Telegram response
```

## Run locally

1. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY`.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Start the API: `uvicorn app.main:app --reload`.
4. Expose the local port with an HTTPS tunnel such as `ngrok http 8000`.
5. Set `TELEGRAM_WEBHOOK_URL` to the HTTPS tunnel origin.
6. Register the webhook: `python -m app.register_webhook`.
7. Send a message to the bot in Telegram.

The health endpoint is `/health`. Set `TELEGRAM_WEBHOOK_SECRET` to require
Telegram's secret header on webhook requests.

The webhook endpoint is `POST /webhook/telegram`. The registration command
uses `TELEGRAM_WEBHOOK_URL` and appends `/webhook/telegram`; no public URL is
hardcoded in the application.

## Clinic knowledge

Place `.txt` or `.md` clinic documents under `data/knowledge/uploads` or
`data/knowledge`. The initial service uses deterministic local retrieval so
the application is runnable without a hosted vector database. The RAG service
is isolated behind `app/rag/service.py` and can be replaced with a persistent
vector store later.

## Structure

- `app/api`: FastAPI webhook endpoints.
- `app/graph`: LangGraph state, routing, and nodes.
- `app/llm`: Gemini adapter.
- `app/rag` and `app/tools`: clinic knowledge retrieval.
- `app/telegram`: Telegram transport and keyboards.
- `calendar_tools.py`, `sheet_tools.py`, `gmail_tools.py`, and `google_auth.py`:
	preserved reusable Google integrations for later adapter work.

Appointment booking, payments, invoicing, CRM writes, and email notifications
are intentionally out of scope for this phase.