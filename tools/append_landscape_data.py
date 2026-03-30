import csv
import os
import sys
from Shared.config import DEFAULT_CSV_ENCODING

def append_landscape_data(input_file_path):
    csv_file_path = "db/landscape/master_landscape.csv"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    # Read new data from the input file
    with open(input_file_path, 'r', newline='', encoding='utf-8') as f:
        new_data_string = f.read()

    # Parse new data
    lines = new_data_string.strip().split(os.linesep)
    
    if not lines:
        print("Error: Input file is empty or contains only whitespace.")
        return

    new_data_headers = [h.strip() for h in lines[0].split('	') if h.strip()]
    if not new_data_headers:
        print("Error: No headers found in the input file.")
        return

    new_data_rows = []
    for line in lines[1:]:
        if not line.strip(): # Skip empty lines
            continue

        split_line = line.split('	')
        # Pad the split_line if it has fewer elements than headers
        padded_line = split_line + [''] * (len(new_data_headers) - len(split_line))
        
        # Clean each cell in the padded line, handling internal newlines/quotes
        cleaned_row = [
            cell.strip().replace('"' + os.linesep + '"' , ' ').replace(os.linesep, ' ')
            for cell in padded_line
        ]
        new_data_rows.append(cleaned_row)

    # Read existing data and merge headers
    existing_headers = []
    existing_data = []

    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r', newline='', encoding=DEFAULT_CSV_ENCODING) as f:
            reader = csv.reader(f)
            existing_headers = [h.strip() for h in next(reader) if h.strip()]
            for row in reader:
                existing_data.append([c.strip() for c in row])

    # Combine headers, maintaining order and uniqueness
    final_headers = list(existing_headers)
    for new_h in new_data_headers:
        if new_h not in final_headers:
            final_headers.append(new_h)
    
    # Pad existing data if new headers were added
    padded_existing_data = []
    for row in existing_data:
        padded_row = row + [''] * (len(final_headers) - len(existing_headers))
        padded_existing_data.append(padded_row)
    
    # Map new data to final headers
    mapped_new_data = []
    for new_row_original in new_data_rows:
        # new_row_original is already padded and cleaned, directly map
        mapped_row = [''] * len(final_headers)
        
        # Create a dictionary for easy lookup by new_data_headers
        new_row_dict = {new_data_headers[i]: new_row_original[i] for i in range(len(new_data_headers))}

        for i, header in enumerate(final_headers):
            if header in new_row_dict:
                mapped_row[i] = new_row_dict[header]
        mapped_new_data.append(mapped_row)

    # Write all data back to the CSV
    with open(csv_file_path, 'w', newline='', encoding=DEFAULT_CSV_ENCODING) as f:
        writer = csv.writer(f)
        writer.writerow(final_headers)
        writer.writerows(padded_existing_data + mapped_new_data)

    print(f"Successfully updated {csv_file_path} with {len(mapped_new_data)} new rows.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        append_landscape_data(sys.argv[1])
    else:
        print("Error: No input file path provided. Usage: python script.py <input_file_path>")
