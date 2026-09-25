from langchain_core.tools import tool

from googleapiclient.discovery import build
import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from google_auth import get_credentials
creds = get_credentials()

gmail_service = build(
    "gmail",
    "v1",
    credentials=creds
)

# gmail_service = build(
#     "gmail",
#     "v1",
#     credentials=creds
# )


#send email
@tool
def send_email(
    to: str,
    subject: str,
    body: str
) -> str:
    """
    Send an email.

    Example:
    to="abc@gmail.com"
    subject="Meeting"
    body="Hello"
    """

    message = f"""To: {to}
Subject: {subject}

{body}
"""

    raw = base64.urlsafe_b64encode(
        message.encode()
    ).decode()

    gmail_service.users().messages().send(
        userId="me",
        body={
            "raw": raw
        }
    ).execute()
    return "Email sent successfully."


@tool
def send_email_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment_path: str,
) -> str:
    """Send an email with one local PDF attachment."""
    message = MIMEMultipart()
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    path = Path(attachment_path)
    with path.open("rb") as attachment:
        part = MIMEApplication(attachment.read(), _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=path.name)
    message.attach(part)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return "Email sent successfully."

#Read Latest Emails
@tool
def read_latest_emails(limit: int = 5):
    """
    Read latest emails.
    """

    result = gmail_service.users().messages().list(
        userId="me",
        maxResults=limit
    ).execute()

    messages = result.get("messages", [])

    emails = []

    for msg in messages:

        mail = gmail_service.users().messages().get(
            userId="me",
            id=msg["id"]
        ).execute()

        headers = mail["payload"]["headers"]

        subject = ""
        sender = ""

        for h in headers:

            if h["name"] == "Subject":
                subject = h["value"]

            if h["name"] == "From":
                sender = h["value"]

        emails.append(
            {
                "from": sender,
                "subject": subject
            }
        )

    return emails

#Search Email
@tool
def search_email(query: str):
    """
    Search emails.

    Example:

    from:amazon

    internship

    subject:meeting
    """

    result = gmail_service.users().messages().list(
        userId="me",
        q=query,
        maxResults=5
    ).execute()

    messages = result.get(
        "messages",
        []
    )

    emails = []

    for msg in messages:

        mail = gmail_service.users().messages().get(
            userId="me",
            id=msg["id"]
        ).execute()

        headers = mail["payload"]["headers"]

        subject = ""

        sender = ""

        for h in headers:

            if h["name"] == "Subject":
                subject = h["value"]

            if h["name"] == "From":
                sender = h["value"]

        emails.append(
            {
                "from": sender,
                "subject": subject
            }
        )

    return emails

#Unread Emails
@tool
def unread_emails():
    """
    Get unread emails.
    """

    result = gmail_service.users().messages().list(
        userId="me",
        q="is:unread"
    ).execute()

    return result.get(
        "messages",
        []
    )