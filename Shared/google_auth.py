import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuration
CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

def get_sheets_service():
    if not CREDENTIALS_FILE:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)
