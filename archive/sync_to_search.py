import os
import json
import argparse
import requests
import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Setup & Auth
# ---------------------------------------------------------------------------
def setup_credentials():
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set.")
        exit(1)
        
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/cloud-platform"
    ]
    credentials, project_id = google.auth.default(scopes=scopes)
    credentials.refresh(Request())
    return credentials, project_id

# ---------------------------------------------------------------------------
# Sheets Reader
# ---------------------------------------------------------------------------
def get_sheet_data(sheets_service, spreadsheet_id, range_name):
    print(f"Reading data from Google Sheet ({range_name})...")
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    rows = result.get('values', [])
    
    if not rows:
        print("No data found in sheet.")
        return []
        
    headers = rows[0]
    data = []
    for row in rows[1:]:
        # Create a dictionary mapping headers to values
        item = {}
        for i, header in enumerate(headers):
            # Clean up header to be a valid JSON key (alphanumeric only)
            safe_header = "".join(c for c in header if c.isalnum() or c == '_').lower()
            if not safe_header:
                continue
                
            val = row[i] if i < len(row) else ""
            item[safe_header] = val
            
        if item.get('from'): # Must have an ID
            # Vertex AI Search requires an 'id' field for structured data
            item['id'] = "".join(c for c in item['from'] if c.isalnum() or c in '-_')
            data.append(item)
            
    print(f"Found {len(data)} valid rows.")
    return data

# ---------------------------------------------------------------------------
# Vertex AI Search Importer
# ---------------------------------------------------------------------------
def import_to_vertex_search(credentials, project_number, data_store_id, data):
    print(f"Importing {len(data)} documents to Vertex AI Search...")
    
    # Discovery Engine API uses project number, not ID
    url = f"https://discoveryengine.googleapis.com/v1/projects/{project_number}/locations/global/collections/default_collection/dataStores/{data_store_id}/branches/default_branch/documents:import"
    
    # Format data for the import API (inline JSON)
    inline_source = {
        "documents": []
    }
    
    for item in data:
        # Each document must have an ID and a JSON struct
        doc = {
            "id": item['id'],
            "jsonData": json.dumps(item)
        }
        inline_source["documents"].append(doc)
        
    payload = {
        "inlineSource": inline_source,
        "reconciliationMode": "INCREMENTAL" # Update existing, add new
    }
    
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        operation_name = response.json().get('name')
        print(f"Import started successfully! Operation: {operation_name}")
        print("Note: It may take a few minutes for the data to be fully indexed and searchable.")
        return True
    else:
        print(f"Error ({response.status_code}): {response.text}")
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Sync Google Sheet to Vertex AI Search")
    parser.add_argument("--sheet-id", required=True, help="Google Spreadsheet ID")
    parser.add_argument("--tab-name", required=True, help="Name of the tab (e.g. LifeFitness)")
    parser.add_argument("--store-id", required=True, help="Vertex AI Data Store ID")
    args = parser.parse_args()
    
    credentials, _ = setup_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    # Get project number from the service account key
    project_number = "952613857720" # Hardcoded from previous API calls
    
    # 1. Read data
    data = get_sheet_data(sheets_service, args.sheet_id, args.tab_name)
    if not data:
        return
        
    # 2. Import to Vertex AI Search
    import_to_vertex_search(credentials, project_number, args.store_id, data)

if __name__ == "__main__":
    main()
