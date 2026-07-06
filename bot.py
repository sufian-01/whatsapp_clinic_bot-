from fastapi import FastAPI, Request
import uvicorn

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from typing import TypedDict, Annotated

from dotenv import load_dotenv

import sqlite3
import requests
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(
    title="AI Telegram Secretary",
    version="1.0.0"
)

#LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash"
)


#***************State***************************#
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

#function
def chat_node(state : ChatState):
    response = llm.invoke(state["messages"])

    return {
        "messages":[response]
    }
#database
conn = sqlite3.connect(
    "telegram.db",
    check_same_thread=False
)

memory = SqliteSaver(conn)

#Graph
graph = StateGraph(ChatState)
graph.add_node("chatbot", chat_node)

graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

chatbot = graph.compile(
    checkpointer=memory
)

def send_message(chat_id: int, text: str):

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    response = requests.post(url, json=payload)

    print("\n===== Telegram API Response =====")
    print("Status Code:", response.status_code)
    print("Response:", response.text)

    return response
@app.post("/webhook")
async def telegram_webhook(request: Request):

    print("\n================ WEBHOOK HIT ================\n")

    data = await request.json()

    print("Telegram Update:")
    print(data)

    # Ignore non-message updates
    if "message" not in data:
        print("No message found.")
        return {"status": "ignored"}

    message = data["message"]

    chat_id = message["chat"]["id"]
    user_text = message.get("text")

    print(f"Chat ID : {chat_id}")
    print(f"User Msg: {user_text}")

    # Ignore stickers/photos etc.
    if user_text is None:
        send_message(chat_id, "Please send a text message.")
        return {"status": "ignored"}

    try:

        config = {
            "configurable": {
                "thread_id": str(chat_id)
            }
        }

        print("Calling LangGraph...")

        response = chatbot.invoke(
            {
                "messages": [
                    HumanMessage(content=user_text)
                ]
            },
            config=config
        )

        print("LangGraph Response:")
        print(response)

        ai_reply = response["messages"][-1].content

        print("AI Reply:")
        print(ai_reply)

        print("Sending Telegram Message...")

        send_message(chat_id, ai_reply)

        print("Message Sent Successfully.")

    except Exception as e:

        print("\n========== ERROR ==========")
        import traceback
        traceback.print_exc()

        send_message(
            chat_id,
            "Something went wrong. Please try again."
        )

    return {"status": "ok"}
@app.get("/")
def home():
    return {"message": "working"}


print(BOT_TOKEN)
print(BASE_URL)