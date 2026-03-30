"""
add_new_rows_to_sheet.py — Append 501 missing image files as new rows to CurrentDB.gsheet.
Each row gets: Filename (col C) and URL/type (col D). Other columns left blank for AI enrichment.
"""
import json
import subprocess

SPREADSHEET_ID = "1yA65ahfpUmym4sFnT2bQfKg1YumhW5Z9pzaoxmlBAi4"
SHEET_NAME = "CurrentDB"

# Load the rows to add
with open("/home/ubuntu/new_rows_to_add.json") as f:
    rows_to_add = json.load(f)

print(f"Rows to append: {len(rows_to_add)}")

# The sheet columns are: Rating(A), Tags(B), Filename(C), URL(D), ...
# We need to append rows with Filename and URL filled in
# Format: each row = ["", "", filename, url_type]
values = [["", "", fn, url] for fn, url in rows_to_add]

# Use sheets.spreadsheets.values.append to add rows at the end
body = {
    "values": values
}

params = {
    "spreadsheetId": SPREADSHEET_ID,
    "range": f"{SHEET_NAME}!A1",
    "valueInputOption": "RAW",
    "insertDataOption": "INSERT_ROWS",
}

result = subprocess.run(
    ["gws", "sheets", "spreadsheets", "values", "append",
     "--params", json.dumps(params),
     "--json", json.dumps(body)],
    capture_output=True, text=True
)

if result.returncode == 0:
    data = json.loads(result.stdout)
    updates = data.get("updates", {})
    print(f"SUCCESS: {updates.get('updatedRows', '?')} rows appended")
    print(f"Updated range: {updates.get('updatedRange', '?')}")
else:
    print(f"ERROR: {result.stderr[:500]}")
    print(f"stdout: {result.stdout[:200]}")
