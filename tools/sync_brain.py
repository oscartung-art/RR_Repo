"""
sync_brain.py — Studio OS Master Sync
Performs three outputs in one run:
  1. Cloud Brain (Google Doc)  — Stitches all active .md files into the Cloud Brain Doc
  2. Visual Dashboard (Sheet)  — Parses log/action_log.md and pushes data to Google Sheet
  3. Auto-Formatting (API)     — Applies conditional colour formatting to the Status column

Usage: python tools/sync_brain.py
       python tools/sync_brain.py --dry-run   (print output without writing)

Requirements:
  pip install google-auth google-auth-oauthlib google-api-python-client
  Credentials via GOOGLE_SERVICE_ACCOUNT_JSON or OAuth via gws CLI tokens.
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Bootstrap Shared module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import DASHBOARD_SHEET_ID, CLOUD_BRAIN_DOC_ID

# Resolve BRAIN_ROOT to the correct path depending on execution environment
_BRAIN_CANDIDATES = [
    Path('/mnt/desktop/GoogleDrive/RR_Repo'),   # Manus sandbox (via FUSE mount)
    Path('D:/GoogleDrive/RR_Repo'),              # Windows local
    Path(__file__).resolve().parent.parent,      # Relative fallback
]
BRAIN_ROOT = next((p for p in _BRAIN_CANDIDATES if p.exists()), Path(__file__).resolve().parent.parent)

# ─── Google API Auth ──────────────────────────────────────────────────────────

def get_credentials():
    """
    Build Google API credentials.
    Priority: GOOGLE_WORKSPACE_CLI_TOKEN env var > service account JSON > gws token file.
    """
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.oauth2.credentials import Credentials as OAuthCredentials
        import google.auth
    except ImportError:
        print("[-] Missing google-auth packages. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/spreadsheets',
    ]

    # Option 0: GOOGLE_WORKSPACE_CLI_TOKEN environment variable (Manus-injected)
    token_env = os.environ.get('GOOGLE_WORKSPACE_CLI_TOKEN')
    if token_env:
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=token_env)
        return creds

    # Option 1: Service account JSON (check multiple locations)
    sa_candidates = [
        BRAIN_ROOT / '.env' / 'service_account.json',
        Path('/mnt/desktop/GoogleDrive/RR_Repo/.env/service_account.json'),
        Path.home() / 'service_account.json',
    ]
    for sa_path in sa_candidates:
        try:
            if sa_path.exists():
                creds = service_account.Credentials.from_service_account_file(
                    str(sa_path), scopes=SCOPES
                )
                return creds
        except OSError:
            continue

    # Option 2: gws CLI OAuth token (check multiple locations)
    token_candidates = [
        Path.home() / '.config' / 'gws' / 'token.json',
        Path.home() / '.gws' / 'token.json',
        Path('/root/.config/gws/token.json'),
    ]
    for token_path in token_candidates:
        try:
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                if creds and creds.valid:
                    return creds
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    return creds
        except OSError:
            continue

    print("[-] No valid credentials found.")
    print("    Option A: Place service_account.json in D:\\GoogleDrive\\RR_Repo\\.env\\")
    print("    Option B: Run 'gws auth login' to authenticate via OAuth.")
    sys.exit(1)


def build_services():
    creds = get_credentials()
    from googleapiclient.discovery import build
    docs_service   = build('docs',   'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return docs_service, sheets_service


# ─── 1. Cloud Brain Doc ───────────────────────────────────────────────────────

BRAIN_DOCS = [
    'gemini.md',
    'docs/RR_Improvement_Plan.md',
    'docs/Naming_Convention.md',
    'docs/AI_Terminal_Workflow_Guide.md',
    'log/action_log.md',
]

def stitch_brain_content():
    """Concatenate key .md files into a single string for the Cloud Brain Doc."""
    parts = []
    for rel_path in BRAIN_DOCS:
        fpath = BRAIN_ROOT / rel_path
        if fpath.exists():
            parts.append(f"{'='*60}\n# {rel_path}\n{'='*60}\n")
            parts.append(fpath.read_text(encoding='utf-8'))
            parts.append('\n\n')
        else:
            parts.append(f"[MISSING: {rel_path}]\n\n")
    return ''.join(parts)


def update_cloud_brain_doc(docs_service, content, dry_run=False):
    """Overwrite the Cloud Brain Google Doc with stitched content."""
    if dry_run:
        print("[DRY RUN] Would update Cloud Brain Doc:")
        print(content[:500] + '...')
        return

    # Get current doc length to clear it first
    doc = docs_service.documents().get(documentId=CLOUD_BRAIN_DOC_ID).execute()
    body_content = doc.get('body', {}).get('content', [])
    end_index = body_content[-1].get('endIndex', 1) if body_content else 1

    requests = []
    # Delete all existing content (except the required trailing newline at index 1)
    if end_index > 2:
        requests.append({
            'deleteContentRange': {
                'range': {'startIndex': 1, 'endIndex': end_index - 1}
            }
        })
    # Insert new content
    requests.append({
        'insertText': {
            'location': {'index': 1},
            'text': content
        }
    })

    docs_service.documents().batchUpdate(
        documentId=CLOUD_BRAIN_DOC_ID,
        body={'requests': requests}
    ).execute()
    print(f"[+] Cloud Brain Doc updated ({len(content):,} chars)")


# ─── 2. Visual Dashboard (Sheet) ─────────────────────────────────────────────

def parse_action_log():
    """Parse log/action_log.md and return rows as list of dicts."""
    log_path = BRAIN_ROOT / 'log' / 'action_log.md'
    if not log_path.exists():
        print(f"[-] action_log.md not found at {log_path}")
        return []

    rows = []
    for line in log_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        # Skip header, separator, and non-data lines
        if not line.startswith('|') or line.startswith('| :') or line.startswith('| #ID'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) >= 5:
            rows.append({
                'id':          cells[0],
                'date':        cells[1],
                'project':     cells[2],
                'description': cells[3],
                'status':      cells[4],
            })
    return rows


def push_dashboard(sheets_service, rows, dry_run=False):
    """Push action_log rows to the Dashboard Google Sheet."""
    header = [['#ID', 'Date', 'Project', 'Description', 'Status']]
    data_rows = [[r['id'], r['date'], r['project'], r['description'], r['status']] for r in rows]
    all_rows = header + data_rows

    if dry_run:
        print(f"[DRY RUN] Would push {len(data_rows)} rows to Dashboard Sheet:")
        for row in all_rows[:5]:
            print(' | '.join(row))
        return len(data_rows)

    sheets_service.spreadsheets().values().update(
        spreadsheetId=DASHBOARD_SHEET_ID,
        range='Sheet1!A1',
        valueInputOption='RAW',
        body={'values': all_rows}
    ).execute()
    print(f"[+] Dashboard Sheet updated with {len(data_rows)} rows")
    return len(data_rows)


# ─── 3. Conditional Formatting ────────────────────────────────────────────────

STATUS_COLORS = {
    'Done':        {'red': 0.56, 'green': 0.93, 'blue': 0.56},   # Green
    'Pending':     {'red': 1.00, 'green': 0.95, 'blue': 0.60},   # Yellow
    'In Progress': {'red': 0.53, 'green': 0.81, 'blue': 0.98},   # Blue
    'Blocked':     {'red': 0.96, 'green': 0.49, 'blue': 0.49},   # Red
    'Active':      {'red': 0.53, 'green': 0.81, 'blue': 0.98},   # Blue (alias)
    'Cancelled':   {'red': 0.85, 'green': 0.85, 'blue': 0.85},   # Grey
}

def apply_conditional_formatting(sheets_service, row_count, dry_run=False):
    """Apply colour formatting to the Status column (column E = index 4)."""
    if dry_run:
        print(f"[DRY RUN] Would apply conditional formatting to {row_count} rows")
        return

    # First get the sheet ID (tab ID, not file ID)
    sheet_meta = sheets_service.spreadsheets().get(
        spreadsheetId=DASHBOARD_SHEET_ID
    ).execute()
    sheet_id = sheet_meta['sheets'][0]['properties']['sheetId']

    requests = []
    for status, color in STATUS_COLORS.items():
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': row_count + 1,
                        'startColumnIndex': 4,
                        'endColumnIndex': 5,
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': status}]
                        },
                        'format': {
                            'backgroundColor': color
                        }
                    }
                },
                'index': 0
            }
        })

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=DASHBOARD_SHEET_ID,
        body={'requests': requests}
    ).execute()
    print(f"[+] Conditional formatting applied ({len(STATUS_COLORS)} status colours)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Studio OS Master Sync")
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--skip-doc',   action='store_true', help='Skip Cloud Brain Doc update')
    parser.add_argument('--skip-sheet', action='store_true', help='Skip Dashboard Sheet update')
    args = parser.parse_args()

    print(f"=== sync_brain.py — Studio OS Master Sync ===")
    print(f"    Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"    Dry Run: {args.dry_run}")
    print()

    docs_service, sheets_service = build_services()

    # 1. Cloud Brain Doc
    if not args.skip_doc:
        print("[1/3] Stitching Cloud Brain Doc...")
        content = stitch_brain_content()
        update_cloud_brain_doc(docs_service, content, dry_run=args.dry_run)
    else:
        print("[1/3] Skipped Cloud Brain Doc.")

    # 2. Dashboard Sheet
    if not args.skip_sheet:
        print("[2/3] Parsing action_log.md...")
        rows = parse_action_log()
        row_count = push_dashboard(sheets_service, rows, dry_run=args.dry_run)

        # 3. Conditional Formatting
        print("[3/3] Applying conditional formatting...")
        apply_conditional_formatting(sheets_service, row_count, dry_run=args.dry_run)
    else:
        print("[2/3] Skipped Dashboard Sheet.")
        print("[3/3] Skipped Conditional Formatting.")

    print()
    print("=== Sync Complete ===")


if __name__ == '__main__':
    main()
