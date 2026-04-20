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
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
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
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

def list_upcoming_events(max_results=10):
    """
    Lists the next 10 events on the user's primary calendar.
    
    Args:
        max_results (int): Number of events to return. Default is 10.
    """
    try:
        service = get_calendar_service()

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
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

    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as e:
        return str(e)

def add_calendar_event(summary, start_time, end_time=None, description=None, location=None):
    """
    Adds an event to the user's primary calendar.
    
    Args:
        summary (str): The title of the event.
        start_time (str): ISO format start time (e.g., '2026-04-20T10:00:00Z').
        end_time (str, optional): ISO format end time. If not provided, defaults to 1 hour after start.
        description (str, optional): Event description.
        location (str, optional): Event location.
    """
    try:
        service = get_calendar_service()

        if not end_time:
            # Default to 1 hour later
            start_dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = start_dt + datetime.timedelta(hours=1)
            end_time = end_dt.isoformat()

        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"

    except HttpError as error:
        return f"An error occurred: {error}"
    except Exception as e:
        return str(e)
