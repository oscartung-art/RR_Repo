import os
import json
import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def setup_credentials():
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    credentials, _ = google.auth.default(scopes=scopes)
    credentials.refresh(Request())
    return credentials

def create_and_populate_sheet():
    creds = setup_credentials()
    sheets_service = build('sheets', 'v4', credentials=creds)

    # 1. Create Spreadsheet
    spreadsheet_body = {
        'properties': {
            'title': 'RealRendering_MasterIndex_2026-03-27'
        },
        'sheets': [
            {'properties': {'title': 'Project Index'}},
            {'properties': {'title': 'Master CRM'}}
        ]
    }
    
    print("Creating new Google Sheet...")
    request = sheets_service.spreadsheets().create(body=spreadsheet_body)
    response = request.execute()
    spreadsheet_id = response.get('spreadsheetId')
    spreadsheet_url = response.get('spreadsheetUrl')
    
    print(f"Spreadsheet created: {spreadsheet_url}")

    # 2. Prepare Data
    project_data = [
        ["Code", "Project Name", "Client", "F: Drive Path", "Share Link"],
        ["KL1", "Unknown", "Unknown", "F:/KL1", "-"],
        ["PLS", "PLS", "NewMeritLimited", "F:/PLS", "https://realrendering.synology.me:5001/d/s/wFsOMrykg0XdP9C21toBTge1kQiviIG4/iV5Lck2dFFS3VCpF8NJc-GhWe_fdGVfX-T7mAKhjR-Ao"],
        ["MWR", "Unknown", "Unknown", "F:/MWR mawo road", "-"],
        ["MLS", "Unknown", "Unknown", "F:/MLS", "-"],
        ["YKS", "Unknown", "Unknown", "F:/YKS", "-"]
    ]

    crm_data = [
        ["Company", "Person", "Email", "Phone", "Address"],
        ["NewMeritLimited", "Bella Fung", "bella.kp.fung@woproperties.com", "(852)23128288", "Suite 3201..."],
        ["Axxa Group Ltd", "Jason TEO", "jasonteo@axxagroup.com.hk", "2893 8586", "Unit 301-02..."],
        ["Vanke", "Alvin Leung", "alvinleung@vanke.com", "(852)2312 8288", "Bank of China Tower..."]
    ]

    # 3. Write Data
    print("Populating 'Project Index' tab...")
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Project Index!A1',
        valueInputOption='USER_ENTERED',
        body={'values': project_data}
    ).execute()

    print("Populating 'Master CRM' tab...")
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Master CRM!A1',
        valueInputOption='USER_ENTERED',
        body={'values': crm_data}
    ).execute()

    print("\nSUCCESS! Your data has been migrated to Google Sheets.")
    print(f"Link: {spreadsheet_url}")

if __name__ == '__main__':
    create_and_populate_sheet()
