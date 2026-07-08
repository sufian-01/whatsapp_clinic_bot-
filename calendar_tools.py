from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from langchain_core.tools import tool

from google_auth import get_credentials

# -----------------------------------
# Google Calendar Service
# -----------------------------------

creds = get_credentials()

calendar_service = build(
    "calendar",
    "v3",
    credentials=creds
)

#today
@tool
def today_events():
    """
    Get today's calendar events.
    """

    now = datetime.now().astimezone()

    start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    end = start + timedelta(days=1)

    events = calendar_service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    items = events.get("items", [])

    if not items:
        return "No events today."

    result = []

    for event in items:

        start_time = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        result.append({
            "title": event["summary"],
            "start": start_time
        })

    return result
#upcoming event
@tool
def upcoming_events(limit: int = 5):
    """
    Get upcoming calendar events.

    Example:
    limit=5
    """

    now = datetime.now(timezone.utc).isoformat()

    events = calendar_service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=limit,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    items = events.get("items", [])

    if not items:
        return "No upcoming events."

    result = []

    for event in items:

        start_time = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        result.append({
            "title": event["summary"],
            "start": start_time
        })

    return result
#create event
@tool
def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str
):
    """
    Create a calendar event.

    Datetime format:

    2026-07-09T15:00:00+05:30
    """

    event = {

        "summary": title,

        "start": {
            "dateTime": start_datetime,
            "timeZone": "Asia/Kolkata"
        },

        "end": {
            "dateTime": end_datetime,
            "timeZone": "Asia/Kolkata"
        }

    }

    created = calendar_service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return {
        "status": "success",
        "title": created["summary"],
        "event_link": created["htmlLink"]
    }
#delete event
@tool
def delete_event(event_id: str):
    """
    Delete a calendar event.

    Example:

    event_id="abc123"
    """

    calendar_service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()

    return "Event deleted successfully."

#update event
@tool
def update_event(
    event_id: str,
    new_title: str
):
    """
    Update event title.

    Example:

    event_id="abc123"

    new_title="AI Meeting"
    """

    event = calendar_service.events().get(
        calendarId="primary",
        eventId=event_id
    ).execute()

    event["summary"] = new_title

    calendar_service.events().update(
        calendarId="primary",
        eventId=event_id,
        body=event
    ).execute()

    return "Event updated successfully."