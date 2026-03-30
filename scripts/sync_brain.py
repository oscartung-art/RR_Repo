import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents"]

# The ID of the target document.
DOCUMENT_ID = "1EmnIcp81vS5ao6isWBVTGol7jVGUQVcArC-VxHPG1w8"
REPO_ROOT = r"D:\GoogleDrive\RR_Repo"
PRIMARY_BRAIN_FILE = os.path.join(REPO_ROOT, "gemini.md")
DIRS_TO_SCAN = [os.path.join(REPO_ROOT, "docs"), os.path.join(REPO_ROOT, "log")]


def get_credentials():
    """Gets user credentials from local files."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'Shared', 'credentials.json')

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return creds


def compile_content():
    """Compiles content from the main brain file and other specified docs."""
    master_string = ""
    
    # 1. Read the primary brain file
    try:
        with open(PRIMARY_BRAIN_FILE, "r", encoding="utf-8") as f:
            master_string += f.read()
    except FileNotFoundError:
        return f"Error: Primary brain file not found at {PRIMARY_BRAIN_FILE}"

    # 2. Scan other directories and append non-archived markdown files
    for directory in DIRS_TO_SCAN:
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".md") and "archive" not in filename.lower():
                    filepath = os.path.join(root, filename)
                    relative_path = os.path.relpath(filepath, REPO_ROOT).replace('\\', '/')
                    master_string += f"""

--- START OF {relative_path} ---

"""
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            master_string += f.read()
                    except Exception as e:
                        master_string += f"Error reading file {filepath}: {e}"
    
    return master_string
import sys

# Add the 'tools' directory to the system path to allow importing sync_crm
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))
try:
    from sync_crm import sync_crm as run_crm_sync
except ImportError:
    run_crm_sync = None

def main(should_sync_crm=False, crm_sweep=False):
    """
    Compiles all brain files into a single string and overwrites the Google Doc.
    Optionally triggers the CRM sync.
    """
    if should_sync_crm and run_crm_sync:
        run_crm_sync(global_sweep=crm_sweep)

    creds = get_credentials()
    try:
        service = build("docs", "v1", credentials=creds)
        
        print("Compiling local brain files...")
        compiled_text = compile_content()
        if compiled_text.startswith("Error"):
            print(compiled_text)
            return

        # Clear existing content
        document = service.documents().get(documentId=DOCUMENT_ID, fields="body").execute()
        if document.get("body") and document.get("body").get("content"):
            end_index = document["body"]["content"][-1]["endIndex"]
            if end_index > 1:
                requests = [{
                    "deleteContentRange": {
                        "range": {"startIndex": 1, "endIndex": end_index - 1}
                    }
                }]
                service.documents().batchUpdate(documentId=DOCUMENT_ID, body={"requests": requests}).execute()

        # Insert new content
        requests = [{"insertText": {"location": {"index": 1}, "text": compiled_text}}]
        service.documents().batchUpdate(documentId=DOCUMENT_ID, body={"requests": requests}).execute()

        print("Successfully synced compiled brain to Google Doc.")

    except HttpError as err:
        print(err)
    except FileNotFoundError:
        print(f"Error: Could not find 'credentials.json'. Please ensure it's in the same directory as the script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Master Brain Sync Script.")
    parser.add_argument('--crm', action='store_true', help='Run the CRM synchronization process.')
    parser.add_argument('--crm-sweep', action='store_true', help='Perform a one-way global sweep for the CRM sync.')
    args = parser.parse_args()

    main(should_sync_crm=args.crm or args.crm_sweep, crm_sweep=args.crm_sweep)
