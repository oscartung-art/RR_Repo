import os
import csv
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../') # Add parent directory to path
from Shared.google_auth import get_sheets_service
from Shared.config import LANDSCAPE_SPREADSHEET_ID, DEFAULT_CSV_ENCODING

# Configuration
OUTPUT_CSV = 'db/landscape/master_landscape.csv'
METADATA_EFU = 'db/landscape/.metadata.efu'

def generate_efu_metadata(csv_file_path, efu_file_path, headers):
    """Generates a .metadata.efu file with custom columns for the given CSV."""
    custom_headers = [
        "Filename",
        "LandscapeCategory",
        "BotanicalName",
        "ChineseName",
        "HeightMM",
        "SpreadMM",
        "AssetBrand",
        "AssetModel",
        "StatusNotes",
        "SourceSheet",
    ]
    
    # Prepare the data for the .efu file
    # This .efu will only describe the master_landscape.csv file itself, not its rows
    efu_data = [[os.path.basename(csv_file_path)]]
    
    # Add placeholder values for custom columns to describe the CSV
    # For simplicity, we'll just indicate that these columns are available in the CSV.
    efu_data[0].extend(["Available in CSV"] * (len(custom_headers) - 1))

    os.makedirs(os.path.dirname(efu_file_path), exist_ok=True)
    with open(efu_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(custom_headers)
        writer.writerows(efu_data)
    print(f"Success: Generated {efu_file_path} for Everything Search.")

def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    service = get_sheets_service()
    spreadsheet = service.spreadsheets()

    meta = spreadsheet.get(spreadsheetId=LANDSCAPE_SPREADSHEET_ID).execute()
    sheet_titles = [s['properties']['title'] for s in meta['sheets'] if s['properties']['title'] not in ['MASTER_ARCHIVE', 'Working', 'Sheet1']]

    headers = ['Category', 'Botanical Name', 'Chinese Name', 'Height (mm)', 'Spread (mm)', '3D Asset Brand', 'Model/Bundle', 'Status/Notes', 'Source Sheet']
    master_data = []
    
    for sheet_name in sheet_titles:
        print(f"Processing sheet: {sheet_name}...")
        result = spreadsheet.values().get(spreadsheetId=LANDSCAPE_SPREADSHEET_ID, range=f"'{sheet_name}'!A1:Z1000").execute()
        values = result.get('values', [])
        
        if not values:
            continue

        for row in values[1:]: # Skip header
            if not any(row): continue # Skip empty rows
            
            clean_row = [""] * 9
            clean_row[8] = sheet_name # Source Sheet
            
            if sheet_name == 'VG':
                # Map VG columns: Botanical Name(18), Chinese Name(19), Brand(20), Bundle(21), Model(22), H(8), S(10)
                try:
                    clean_row[1] = row[18].strip() if len(row) > 18 else ""
                    clean_row[2] = row[19].strip() if len(row) > 19 else ""
                    clean_row[3] = row[8].replace("-", "").strip() if len(row) > 8 else ""
                    clean_row[4] = row[10].replace("-", "").strip() if len(row) > 10 else ""
                    clean_row[5] = row[20].strip() if len(row) > 20 else ""
                    clean_row[6] = f"{row[21].strip()} {row[22].strip()}" if len(row) > 22 and row[21].strip() and row[22].strip() else (row[21].strip() if len(row) > 21 else "")
                except Exception: pass
            
            elif sheet_name in ['Trees', 'Shrubs', 'Large Shrubs']:
                # Standard format: Botanical(0), Chinese(1), H(2), S(3), Spacing/Location(4)
                try:
                    clean_row[1] = row[0].strip() if len(row) > 0 else ""
                    clean_row[2] = row[1].strip() if len(row) > 1 else ""
                    clean_row[3] = row[2].strip() if len(row) > 2 else ""
                    clean_row[4] = row[3].strip() if len(row) > 3 else ""
                    clean_row[7] = row[4].strip() if len(row) > 4 else ""
                    clean_row[0] = sheet_name[:-1].strip() if sheet_name.endswith('s') else sheet_name.strip()
                except Exception: pass
            
            elif sheet_name == 'TOPIARY PLANTING':
                # IDs(0), Chi(3), Bot(2), H(5), S(7), Notes(10)
                try:
                    clean_row[1] = row[2].strip() if len(row) > 2 else ""
                    clean_row[2] = row[3].strip() if len(row) > 3 else ""
                    clean_row[3] = row[5].strip() if len(row) > 5 else ""
                    clean_row[4] = row[7].strip() if len(row) > 7 else ""
                    clean_row[7] = row[10].strip() if len(row) > 10 else ""
                    clean_row[0] = "Topiary"
                except Exception: pass

            if clean_row[1] or clean_row[2]: # Only add if has a botanical or chinese name
                master_data.append(clean_row)

    print(f"Writing {len(master_data)} rows to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, 'w', newline='', encoding=DEFAULT_CSV_ENCODING) as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(master_data)
    print("Success: Landscape data synced to local CSV.")

    # Generate .metadata.efu for Everything Search Custom Columns
    generate_efu_metadata(OUTPUT_CSV, METADATA_EFU, headers)

if __name__ == '__main__':
    main()
