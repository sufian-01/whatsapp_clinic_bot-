# Telegram AI Clinic Assistant

This phase provides the production foundation for one clinic:

```text
Telegram update -> FastAPI webhook -> LangGraph -> Gemini -> optional RAG -> Telegram response
```

Voice messages follow the same path after secure transcription:

```text
Telegram OGG voice -> temporary private file -> Sarvam STT -> LangGraph -> text or Sarvam TTS reply
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

## Voice interaction (Sarvam AI)

Voice support is optional: the text bot starts and operates normally without a
Sarvam key. Add these values to `.env` to enable it (never commit the file):

```dotenv
SARVAM_API_KEY=
SARVAM_STT_MODEL=saaras:v3
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=shubh
SARVAM_STT_URL=https://api.sarvam.ai/speech-to-text
SARVAM_TTS_URL=https://api.sarvam.ai/text-to-speech
```

Patients can use **Voice Settings** in the main menu to select Hindi or English
and turn voice replies on or off. Hindi/English controls TTS only; voice input
uses Sarvam's `codemix` mode so supported models can recognize Hinglish without
translating the booking or clinical information before LangGraph processes it.

Telegram voice files are accepted only when they are at most 30 seconds and
10 MiB (both limits are configurable with the additional `SARVAM_*` variables
in `.env.example`). Source files are kept in a private temporary directory and
removed after every attempt. Sarvam receives the original OGG audio, which its
current STT REST API supports; Sarvam TTS is explicitly requested as Opus so it
can be sent to Telegram as a voice message without a converter dependency.

When voice replies are enabled, the bot sends only a voice response. If TTS or
voice delivery fails, it sends the original text response instead. Voice and
language preferences use the existing in-process conversation session, so they
survive messages during one running application but reset when the process
restarts; a durable patient/session store is the appropriate future upgrade.

No live Sarvam request is made by the automated tests. Obtain a key from
[Sarvam AI](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/rest-api)
before testing voice functionality in Telegram.

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

The existing appointment booking, payments, invoicing, CRM writes, and email
notifications remain independent of the voice transport layer.
