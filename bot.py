from fastapi import FastAPI, Request
import uvicorn
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import sqlite3
import requests
import os
from gmail_tools import (
    send_email,
    read_latest_emails,
    search_email,
    unread_emails
)
from calendar_tools import (
    today_events,
    upcoming_events,
    create_event,
    update_event,
    delete_event
)
from sheet_tools import (
    create_spreadsheet,
    read_sheet,
    append_row,
    update_cells,
    list_sheet_names,
    search_row_by_value,
    update_row_by_search,
    delete_row_by_search
)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(
    title="AI Telegram Secretary",
    version="1.0.0"
)
#LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    system_instruction="""

You are an AI Telegram Secretary.

You have access to external tools.

Whenever a user's request matches a tool, ALWAYS call the appropriate tool.

Never say you cannot perform an action if a tool exists.

Available tools:

- calculator -> perform calculations
- get_weather -> current weather
- currency_converter -> currency conversion
- search_tool -> latest internet search

- send_email -> send emails
- read_latest_emails -> read latest emails
- search_email -> search emails
- unread_emails -> unread emails

- create_calendar_event -> create Google Calendar event
- today_events -> today's events
- upcoming_events -> upcoming events

- create_spreadsheet -> create a Google Spreadsheet
- read_sheet -> read sheet data
- append_row -> append rows
- update_cells -> update cells
- list_sheet_names -> list worksheet names

Never answer "I cannot..." if a tool is available.
Always call the tool first.
"""
)

#@Tool
search_tool = DuckDuckGoSearchRun(region="us-en")
@tool
def currency_converter(
    amount: float,
    from_currency: str,
    to_currency: str
) -> dict:
    """
    Convert currency.

    Example:
    amount=100
    from_currency="USD"
    to_currency="INR"
    """

    url = f"https://open.er-api.com/v6/latest/{from_currency.upper()}"

    data = requests.get(url).json()

    if data["result"] != "success":
        return {"error": "Currency not found"}

    rate = data["rates"].get(to_currency.upper())

    if rate is None:
        return {"error": "Currency not found"}

    converted = amount * rate

    return {
        "amount": amount,
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "exchange_rate": rate,
        "converted_amount": round(converted,2)
    }
@tool
def get_weather(city: str) -> dict:
    """
    Get the current weather of any city.

    Examples:
    Delhi
    London
    Dubai
    """

    try:

        url = "https://api.openweathermap.org/data/2.5/weather"

        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"      # Celsius
        }

        response = requests.get(url, params=params, timeout=10)

        data = response.json()

        if response.status_code != 200:
            return {
                "error": data.get("message", "Unable to fetch weather")
            }

        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"]
        }

    except Exception as e:

        return {
            "error": str(e)
        }
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

tools = [
    search_tool,
    calculator,
    get_weather,
    currency_converter,
    send_email,
    read_latest_emails,
    search_email,
    unread_emails,
    today_events,
    upcoming_events,
    create_event,
    update_event,
    delete_event,
    create_spreadsheet,
    read_sheet,
    append_row,
    update_cells,
    list_sheet_names,
    search_row_by_value,
    update_row_by_search,
    delete_row_by_search
]
llm_with_tools = llm.bind_tools(tools)
#***************State***************************#

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

#function
def chat_node(state: ChatState):

    response = llm_with_tools.invoke(
        state["messages"]
    )

    print("\n========== LLM RESPONSE ==========")
    print(response)
    print("Tool Calls:", response.tool_calls)

    return {
        "messages": [response]
    }
#database
conn = sqlite3.connect(
    "telegram.db",
    check_same_thread=False
)

memory = SqliteSaver(conn)

#Graph
tool_node = ToolNode(tools)
graph = StateGraph(ChatState)

graph.add_node("chatbot", chat_node)

graph.add_node(
    "tools",
    tool_node
)

graph.add_edge(
    START,
    "chatbot"
)

graph.add_conditional_edges(
    "chatbot",
    tools_condition
)

graph.add_edge(
    "tools",
    "chatbot"
)
# graph.add_edge(
#     "chatbot",
#     END
# )

chatbot = graph.compile(
    checkpointer=memory
)
#*************webhook part***************#
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

def extract_text(message):
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )

    return str(content)
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

        ai_reply = extract_text(
        response["messages"][-1]
)

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

