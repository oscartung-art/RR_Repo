import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuration
SPREADSHEET_ID = '1kvXmUldDFyiXMJLQb2yPclFnHZOTsFHom7uGS7GGLPk'
CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

def main():
    if not CREDENTIALS_FILE:
        print("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        return

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet = service.spreadsheets()

    # 1. Get Metadata to find existing sheets
    meta = spreadsheet.get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_titles = [s['properties']['title'] for s in meta['sheets']]

    # 2. Create MASTER_ARCHIVE if it doesn't exist
    if 'MASTER_ARCHIVE' not in sheet_titles:
        print("Creating MASTER_ARCHIVE sheet...")
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {'title': 'MASTER_ARCHIVE'}
                }
            }]
        }
        spreadsheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
    else:
        print("MASTER_ARCHIVE already exists. Clearing content...")
        spreadsheet.values().clear(spreadsheetId=SPREADSHEET_ID, range='MASTER_ARCHIVE!A1:Z5000').execute()

    # 3. Setup Headers
    headers = [['Category', 'Botanical Name', 'Chinese Name', 'Height (mm)', 'Spread (mm)', '3D Asset Brand', 'Model/Bundle', 'Status/Notes', 'Source Sheet']]
    spreadsheet.values().update(
        spreadsheetId=SPREADSHEET_ID, range='MASTER_ARCHIVE!A1',
        valueInputOption='RAW', body={'values': headers}
    ).execute()

    # 4. Extract and Clean Data from each sheet
    master_data = []
    
    for sheet_name in sheet_titles:
        if sheet_name in ['MASTER_ARCHIVE', 'Working', 'Sheet1']:
            continue
        
        print(f"Processing sheet: {sheet_name}...")
        result = spreadsheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{sheet_name}'!A1:Z1000").execute()
        values = result.get('values', [])
        
        if not values:
            continue

        # Simple logic to map columns based on sheet name
        for row in values[1:]: # Skip header
            if not any(row): continue # Skip empty rows
            
            clean_row = [""] * 9
            clean_row[8] = sheet_name # Source Sheet
            
            if sheet_name == 'VG':
                # Map VG columns: Botanical Name(18), Chinese Name(19), Brand(20), Bundle(21), Model(22), H(8), S(10)
                try:
                    clean_row[1] = row[18] if len(row) > 18 else ""
                    clean_row[2] = row[19] if len(row) > 19 else ""
                    clean_row[3] = row[8].replace("-", "") if len(row) > 8 else ""
                    clean_row[4] = row[10].replace("-", "") if len(row) > 10 else ""
                    clean_row[5] = row[20] if len(row) > 20 else ""
                    clean_row[6] = f"{row[21]} {row[22]}" if len(row) > 22 else (row[21] if len(row) > 21 else "")
                except Exception: pass
            
            elif sheet_name in ['Trees', 'Shrubs', 'Large Shrubs']:
                # Standard format: Botanical(0), Chinese(1), H(2), S(3), Spacing/Location(4)
                try:
                    clean_row[1] = row[0] if len(row) > 0 else ""
                    clean_row[2] = row[1] if len(row) > 1 else ""
                    clean_row[3] = row[2] if len(row) > 2 else ""
                    clean_row[4] = row[3] if len(row) > 3 else ""
                    clean_row[7] = row[4] if len(row) > 4 else ""
                    clean_row[0] = sheet_name[:-1] if sheet_name.endswith('s') else sheet_name
                except Exception: pass
            
            elif sheet_name == 'TOPIARY PLANTING':
                # IDs(0), Chi(3), Bot(2), H(5), S(7), Notes(10)
                try:
                    clean_row[1] = row[2] if len(row) > 2 else ""
                    clean_row[2] = row[3] if len(row) > 3 else ""
                    clean_row[3] = row[5] if len(row) > 5 else ""
                    clean_row[4] = row[7] if len(row) > 7 else ""
                    clean_row[7] = row[10] if len(row) > 10 else ""
                    clean_row[0] = "Topiary"
                except Exception: pass

            if clean_row[1] or clean_row[2]: # Only add if has a name
                master_data.append(clean_row)

    # 5. Append to Master Archive
    if master_data:
        print(f"Appending {len(master_data)} rows to MASTER_ARCHIVE...")
        spreadsheet.values().append(
            spreadsheetId=SPREADSHEET_ID, range='MASTER_ARCHIVE!A2',
            valueInputOption='RAW', insertDataOption='INSERT_ROWS',
            body={'values': master_data}
        ).execute()
        print("Success!")
    else:
        print("No data found to migrate.")

if __name__ == '__main__':
    main()
