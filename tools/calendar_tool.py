import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Gets an authorized Google Calendar API service instance."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found. Please follow the instructions in docs/CALENDAR_SETUP.md"
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

def list_upcoming_events(max_results: int = 10) -> str:
    """
    Lists upcoming events on the user's primary calendar.
    
    Args:
        max_results: Number of events to return.
    """
    try:
        service = get_calendar_service()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return "No upcoming events found."

        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_list.append(f"{start} - {event['summary']}")
        
        return "\n".join(event_list)
    except Exception as e:
        return f"Error listing events: {str(e)}"

def add_calendar_event(summary: str, start_time: str, end_time: str = None, description: str = None, location: str = None) -> str:
    """
    Adds a new event to the user's primary calendar.
    
    Args:
        summary: The title of the event.
        start_time: ISO format start time (e.g., '2026-04-20T10:00:00Z').
        end_time: ISO format end time. Defaults to 1 hour after start.
        description: Event description.
        location: Event location.
    """
    try:
        service = get_calendar_service()

        if not end_time:
            start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = start_dt + datetime.timedelta(hours=1)
            end_time = end_dt.isoformat()

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error adding event: {str(e)}"
