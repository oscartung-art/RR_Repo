import os
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Required packages:
# pip install google-auth google-auth-httplib2 google-auth-oauthlib google-api-python-client google-genai

import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_WORKERS = 5  # Number of parallel requests (adjust based on API limits)
OUTPUT_SPREADSHEET_ID = "1M7jMK0dlLqv3VnW7TxSk_Qk7xdqCgpjllFfgnlpO8kQ"  # Your output spreadsheet

def setup_credentials():
    """Set up Google Cloud credentials using the service account JSON file."""
    # Ensure the service account JSON path is set
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your service account JSON file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gen-lang-client-0816223034-99c999088170.json")
        exit(1)
        
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    credentials, _ = google.auth.default(scopes=scopes)
    credentials.refresh(Request())
    return credentials

def get_gemini_client():
    """Set up the Gemini API client."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("Example: export GEMINI_API_KEY=<your-gemini-api-key>")
        exit(1)
    return genai.Client(api_key=api_key)

# ---------------------------------------------------------------------------
# Google Drive Operations
# ---------------------------------------------------------------------------
def get_folder_id(drive_service, folder_name):
    """Find the ID of a folder by its name."""
    print(f"Searching for folder '{folder_name}'...")
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        print(f"ERROR: Folder '{folder_name}' not found. Make sure it is shared with the service account.")
        exit(1)
        
    # Return the first match
    return items[0]['id']

def list_images_in_folder(drive_service, folder_id, folder_name=""):
    """Recursively list all image files in the given folder ID and its subfolders."""
    print(f"Scanning folder: {folder_name}...")
    images = []
    
    # 1. Find images in current folder
    page_token = None
    while True:
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        results = drive_service.files().list(
            q=query, 
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        
        # Add folder_name to each file info so we know where it came from
        for file in results.get('files', []):
            file['parent_folder_name'] = folder_name
            images.append(file)
            
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    # 2. Find subfolders in current folder
    page_token = None
    subfolders = []
    while True:
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(
            q=query, 
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            pageSize=1000
        ).execute()
        
        subfolders.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
            
    # 3. Recursively process subfolders
    for subfolder in subfolders:
        subfolder_path = f"{folder_name}/{subfolder['name']}" if folder_name else subfolder['name']
        images.extend(list_images_in_folder(drive_service, subfolder['id'], subfolder_path))
        
    return images

def download_image_to_memory(credentials, file_id):
    """Download the file directly into memory using the REST API."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        print(f"Failed to download file {file_id}: {response.text}")
        return None

# ---------------------------------------------------------------------------
# Gemini Processing
# ---------------------------------------------------------------------------
def process_single_image(client, credentials, file_info, root_folder_name):
    """Download and process a single image with Gemini."""
    file_id = file_info['id']
    file_name = file_info['name']
    mime_type = file_info['mimeType']
    
    # Use the subfolder name as the folder_name if it's nested, otherwise use root
    actual_folder = file_info.get('parent_folder_name')
    if not actual_folder or actual_folder == root_folder_name:
        actual_folder = root_folder_name
    else:
        # Just use the deepest folder name for the tab/source
        actual_folder = actual_folder.split('/')[-1]
    
    print(f"  [{file_name}] Downloading...")
    image_bytes = download_image_to_memory(credentials, file_id)
    if not image_bytes:
        return None
        
    print(f"  [{file_name}] Analyzing with Gemini...")
    try:
        prompt = """Analyze this image and identify what it contains. Then extract the following metadata:
1. Category (e.g. Furniture, Gym Equipment, Plant, Material/Texture, Architecture, Vehicle, etc.)
2. Subcategory (more specific type within the category)
3. Brand (if visible, otherwise "Unknown")
4. Primary Material
5. Visual Style (e.g. Modern, Industrial, Natural, Minimalist, etc.)
6. Color (dominant color or color family)
7. Description (Write a 2-3 sentence description of this asset covering: what it is and its primary function, key visual characteristics like colour/material/style, and ideal use case or setting. Keep it under 80 words.)

Return as a clean JSON object with these 7 keys: Category, Subcategory, Brand, Primary Material, Visual Style, Color, Description."""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        # Parse response
        result_json = json.loads(response.text)
        print(f"  [{file_name}] Success!")
        
        return {
            "image": file_name,
            "folder": actual_folder,
            "metadata": result_json
        }
    except Exception as e:
        print(f"  [{file_name}] Error: {e}")
        return None

# ---------------------------------------------------------------------------
# Google Sheets Operations
# ---------------------------------------------------------------------------
def prepare_sheet_tab(sheets_service, spreadsheet_id, tab_name):
    """Create a new tab in the existing spreadsheet, or clear it if it already exists."""
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    
    if tab_name in existing_sheets:
        print(f"Tab '{tab_name}' already exists. Clearing old data...")
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1:Z10000"
        ).execute()
    else:
        print(f"Creating new tab '{tab_name}'...")
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
        ).execute()

def make_row(img_name, meta, folder_name):
    """Format the Gemini results into a database row."""
    category = meta.get("Category", "Unknown")
    subcategory = meta.get("Subcategory", "")
    brand = meta.get("Brand", "")
    if brand.lower() == "unknown":
        brand = ""
    
    # Format brand to PascalCase if it exists
    if brand:
        brand = "".join(word.capitalize() for word in brand.split())
        
    material = meta.get("Primary Material", "")
    style = meta.get("Visual Style", "")
    color = meta.get("Color", "")
    description = meta.get("Description", "")
    
    # Build a unique ID from the filename
    base = img_name.rsplit(".", 1)[0].replace(" ", "").replace("_", "")
    unique_id = f"{subcategory.replace(' ', '')}{base}{folder_name.replace(' ', '')}"
    
    # Tags: include Category, Color, and Brand (if any)
    tags = [category, color]
    if brand:
        tags.append(brand)
    tags_str = ", ".join(filter(None, tags))
    
    # Build search string (To column)
    search_parts = [img_name, category, subcategory, material, style, brand, color, description]
    search_str = "".join(filter(None, search_parts)).replace(" ", "")
    
    # Row order: Rating, Tags, Filename, URL, From, Mood, Author, Writer, Album, Genre, People, Company, Period, Artist, Title, Comment, To, Manager, Subject
    return [
        "",           # Rating
        tags_str,     # Tags (Category, Color, Brand)
        img_name,     # Filename
        category,     # URL (using Category here as a high-level grouping)
        unique_id,    # From (Unique ID)
        subcategory,  # Mood (Subcategory)
        "",           # Author
        "",           # Writer
        "",           # Album
        "",           # Genre
        "",           # People (Location - not extracted yet)
        brand,        # Company (Brand in PascalCase)
        material,     # Period (Material)
        style,        # Artist (Style)
        folder_name,  # Title (source folder)
        description,  # Comment (Description)
        search_str,   # To (Search string)
        category,     # Manager
        category      # Subject
    ]

def write_to_sheets(sheets_service, spreadsheet_id, results):
    """Write the processed results to Google Sheets."""
    header = ["Rating", "Tags", "Filename", "URL", "From", "Mood", "Author", "Writer", "Album",
              "Genre", "People", "Company", "Period", "Artist", "Title", "Comment", "To", "Manager", "Subject"]
    
    rows = [header]
    for item in results:
        rows.append(make_row(item["image"], item["metadata"], item["folder"]))
        
    print(f"Writing {len(rows)} rows to the new sheet...")
    body = {"values": rows}
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body=body
    ).execute()
    print("Write complete!")

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Process Google Drive images with Gemini and update Google Sheets.")
    parser.add_argument("--folder", required=True, help="Name of the Google Drive folder to process (e.g., 'LifeFitness')")
    args = parser.parse_args()
    
    folder_name = args.folder
    sheet_name = folder_name # Use folder name as the sheet tab name
    
    print(f"Starting process for folder: {folder_name}")
    print("=" * 50)
    
    # Setup
    credentials = setup_credentials()
    gemini_client = get_gemini_client()
    drive_service = build('drive', 'v3', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    # 1. Get files recursively
    folder_id = get_folder_id(drive_service, folder_name)
    files = list_images_in_folder(drive_service, folder_id, folder_name)
    
    if not files:
        print("No images to process. Exiting.")
        return
        
    print(f"\nFound total {len(files)} images across all subfolders.")
        
    # 2. Process images in parallel
    print(f"\nProcessing {len(files)} images with {MAX_WORKERS} parallel workers...")
    results = []
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_image, gemini_client, credentials, file_info, folder_name): file_info 
            for file_info in files
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_file):
            result = future.result()
            if result:
                results.append(result)
                
    elapsed = time.time() - start_time
    print(f"\nProcessed {len(results)}/{len(files)} images successfully in {elapsed:.2f} seconds.")
    
    # 3. Group results by subfolder and write to Google Sheets
    if results:
        print("\nWriting to Google Sheets...")
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{OUTPUT_SPREADSHEET_ID}/edit"
        
        # Group by folder so we can create one tab per folder
        grouped_results = {}
        for r in results:
            f_name = r['folder']
            if f_name not in grouped_results:
                grouped_results[f_name] = []
            grouped_results[f_name].append(r)
            
        for tab_name, tab_results in grouped_results.items():
            # Sheet names can't be longer than 100 chars and can't contain certain chars
            safe_tab_name = tab_name[:100].replace(':', '').replace('*', '').replace('?', '').replace('[', '').replace(']', '')
            prepare_sheet_tab(sheets_service, OUTPUT_SPREADSHEET_ID, safe_tab_name)
            write_to_sheets(sheets_service, OUTPUT_SPREADSHEET_ID, tab_results)
            print(f"Wrote {len(tab_results)} items to tab '{safe_tab_name}'")
        
        print(f"\nSUCCESS! View your data here:")
        print(f"--> {spreadsheet_url} <--")
        
    print("\nAll done!")

if __name__ == "__main__":
    main()
