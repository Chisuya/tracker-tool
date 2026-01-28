# purpose of this:
# handle OAuth auth (one time auth)
# create cal events from time sessions
# updates events if sessions are edited
# deletes events of sesions deleted

"""
Google Calendar Integration for Art Time Tracker
Automatically syncs time sessions to Google Calendar in real-time.
"""

import os
import pickle
from datetime import datetime, timezone
import pytz
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

# Scopes define what permissions we're requesting
# We need full calendar access to create a dedicated calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
def get_local_timezone():
    """Get configured timezone"""
    return pytz.timezone(config.get_timezone())


class CalendarSync:
    """Manages syncing time sessions to Google Calendar."""
    
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle', 
                 calendar_name='Art Time Tracker'):
        """
        Initialize calendar sync.
        
        Args:
            credentials_file: Path to your OAuth credentials JSON
            token_file: Path to save/load the authorized token
            calendar_name: Name of the dedicated calendar to use/create
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.calendar_name = calendar_name
        self.calendar_id = None  # Will be set after finding/creating calendar
        
    def authenticate(self):
        """
        Authenticate with Google Calendar API.
        
        The first time you run this, it will:
        1. Open a browser window
        2. Ask you to sign in to Google
        3. Ask you to authorize the app
        4. Save the token for future use
        
        After the first time, it will use the saved token.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        creds = None
        
        # Check if we have a saved token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    # Token refresh failed, need to re-authenticate
                    creds = None
            
            if not creds:
                # No valid token, need to authenticate
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during authentication: {e}")
                    return False
            
            # Save the credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        try:
            # Build the calendar service
            self.service = build('calendar', 'v3', credentials=creds)
            
            # Find or create the dedicated calendar
            if not self._setup_calendar():
                print("Error setting up calendar")
                return False
            
            return True
        except Exception as e:
            print(f"Error building calendar service: {e}")
            return False
    
    # setup call instead of using primary
    def _setup_calendar(self) -> bool:
        """
        Find the Art Time Tracker calendar, or create it if it doesn't exist.
        
        Returns:
            bool: True if calendar is ready, False otherwise
        """
        try:
            # List all calendars
            calendar_list = self.service.calendarList().list().execute()
            
            # Look for our calendar
            for calendar in calendar_list.get('items', []):
                if calendar['summary'] == self.calendar_name:
                    self.calendar_id = calendar['id']
                    print(f"Found existing calendar: {self.calendar_name}")
                    return True
            
            # Calendar doesn't exist, create it
            print(f"Creating new calendar: {self.calendar_name}")
            calendar = {
                'summary': self.calendar_name,
                'description': 'Automatic time tracking',
                'timeZone': config.get_timezone(),
            }
            
            created_calendar = self.service.calendars().insert(body=calendar).execute()
            self.calendar_id = created_calendar['id']
            print(f"Created new calendar: {self.calendar_name}")
            return True
            
        except HttpError as e:
            print(f"Error setting up calendar: {e}")
            return False
    
    def create_event_from_session(self, session_data: dict) -> Optional[str]:
        """
        Create a calendar event from a time session.
        
        Args:
            session_data: Dictionary with keys:
                - project_name: Name of the project
                - app_name: Name of the application
                - start_time: datetime object
                - end_time: datetime object
                - duration_seconds: Total seconds (for display)
        
        Returns:
            event_id: Google Calendar event ID, or None if failed
        """
        if not self.service:
            print("Not authenticated. Call authenticate() first.")
            return None
        
        try:
            # Format times for Google Calendar (RFC3339)
            start_time = session_data['start_time']
            end_time = session_data['end_time']
            
            # Ensure times are timezone-aware (use local timezone)
            LOCAL_TZ = get_local_timezone()
            if start_time.tzinfo is None:
                start_time = LOCAL_TZ.localize(start_time)
            if end_time.tzinfo is None:
                end_time = LOCAL_TZ.localize(end_time)
            # Calculate duration for display
            duration_minutes = session_data['duration_seconds'] / 60
            
            # Colour code by app
            app_colors = {
                'Photoshop.exe': '9', # blueberry
                'PureRef.exe': '4', # flamingo
                'chrome.exe': '10', # basil
                'code.exe': '1', # lavender
                'Idle': '8', # graphite
            }
            color_id = app_colors.get(session_data['app_name'], '8') # default to graphite

            # Create event
            emoji = "💤" if session_data['app_name'] == 'Idle' else "🎨"
            app_display = session_data['app_name'].replace('.exe', '')
            event = {
                # Clean up app name for display
                'summary': f"{emoji} {session_data['project_name']} - {app_display}",
                'description': f"Art time tracked in {session_data['app_name']}\n"
                              f"Duration: {duration_minutes:.1f} minutes",
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': config.get_timezone(),  # Adjust to your timezone
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': config.get_timezone(),
                },
                'colorId': color_id,
            }
            
            # Insert event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            print(f"Created calendar event: {created_event.get('htmlLink')}")
            return created_event['id']
            
        except HttpError as e:
            print(f"Error creating calendar event: {e}")
            return None
    
    def update_event(self, event_id: str, session_data: dict) -> bool:
        """
        Update an existing calendar event.
        
        Args:
            event_id: Google Calendar event ID
            session_data: Updated session data (same format as create_event_from_session)
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.service:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        try:
            # Get the existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update event fields
            start_time = session_data['start_time']
            end_time = session_data['end_time']
            
            LOCAL_TZ = get_local_timezone()
            if start_time.tzinfo is None:
                start_time = LOCAL_TZ.localize(start_time)
            if end_time.tzinfo is None:
                end_time = LOCAL_TZ.localize(end_time)
            
            duration_minutes = session_data['duration_seconds'] / 60
            
            event['summary'] = f"🎨 {session_data['project_name']} - {session_data['app_name']}"
            event['description'] = f"Art time tracked in {session_data['app_name']}\n" \
                                  f"Duration: {duration_minutes:.1f} minutes"
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': config.get_timezone(),
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': config.get_timezone(),
            }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            print(f"✓ Updated calendar event: {updated_event.get('htmlLink')}")
            return True
            
        except HttpError as e:
            print(f"Error updating calendar event: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: Google Calendar event ID
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.service:
            print("Not authenticated. Call authenticate() first.")
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            print(f"Deleted calendar event")
            return True
            
        except HttpError as e:
            print(f"Error deleting calendar event: {e}")
            return False


# Example usage (for testing)
if __name__ == "__main__":
    from datetime import timedelta
    
    # Create sync object
    sync = CalendarSync()
    
    # Authenticate (will open browser first time)
    if sync.authenticate():
        print("Successfully authenticated with Google Calendar!")
        
        # Test creating an event
        test_session = {
            'project_name': 'Test Commission',
            'app_name': 'Photoshop',
            'start_time': datetime.now() - timedelta(hours=1),
            'end_time': datetime.now(),
            'duration_seconds': 3600
        }
        
        event_id = sync.create_event_from_session(test_session)
        if event_id:
            print(f"Created test event with ID: {event_id}")
            print("Check your Google Calendar!")
    else:
        print("Authentication failed")