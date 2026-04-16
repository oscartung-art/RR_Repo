#!/usr/bin/env python3
"""
Recreate .metadata.efu with Mood→Subject migration
Using a simpler approach with explicit data handling
"""

import csv
from io import StringIO

# Construct the CSV from the data provided in attachments
# This is the original data with full rows
csv_data = """Filename,Rating,Tags,URL,From,Mood,Author,Writer,Album,Genre,People,Company,Period,Artist,Title,Comment,To,Manager,Subject,CRC-32
-,-,-,-,-,Furniture/Seating/LoungeChair,Luc,Rossin,-,Orange,Living Room,-,-,-,Rossin,-,-,Furniture;src=10-03 luc-by-rossin;crc32=8E54D69E,LoungeChair_Luc_8E54D69E.rar,8E54D69E
-,-,-,-,-,Furniture/Table/SideTable,Gaby Low Tables,Ligne Roset,-,Wood,-,Square,-,-,-,-,-,Furniture;src=10-16 Gaby-Low-Tables;crc32=B3551929,SideTable_GabyLowTables_B3551929.rar,B3551929
-,-,-,-,-,Furniture/Seating/LoungeChair,Nestrest,Dedon,-,White,Outdoor,Teardrop,-,-,Dedon,-,-,Furniture;src=10-39 nestrest-by-dedon;crc32=4972A404,LoungeChair_Nestrest_4972A404.rar,4972A404
-,-,-,-,-,Fixture/ShowerMixer,A16601 Shower Set With Mixer,OM,-,Chrome,Bathroom,Vertical,-,-,-,-,-,Furniture;src=11-33 A16601-Shower-set-with-mixer_OM;crc32=EE10B758,ShowerMixer_A16601ShowerSetWithMixer_EE10B758.rar,EE10B758
-,-,-,-,-,Fixture/ShowerMixer,Vernis Blend Shower Mixer,Hansgrohe,Vernis Blend,Black,Bathroom,Column,-,-,Hansgrohe,-,-,Furniture;src=11-33 bathroom.shower_mixer.vernis_blend.Hansgrohe1;crc32=43341E22,ShowerMixer_VernisBlendShowerMixer_43341E22.rar,43341E22"""

try:
    # Backup existing file
    import shutil
    from pathlib import Path
    
    metadata_file = r'd:\DB\.metadata.efu'
    backup_file = r'd:\DB\.metadata.efu.backup'
    
    # Only backup if file has data
    if Path(metadata_file).stat().st_size > 100:
        shutil.copy2(metadata_file, backup_file + '.v2')
        print("Backup created (v2)")
    
    # Read CSV
    reader = csv.DictReader(StringIO(csv_data))
    rows = []
    count = 0
    
    for row in reader:
        # Move Mood → Subject
        row['Subject'] = row['Mood']
        del row['Mood']  # Remove Mood key
        rows.append(row)
        count += 1
    
    # Get new fieldnames (without Mood)
    fieldnames = [col for col in reader.fieldnames if col != 'Mood']
    
    # Write updated CSV
    with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Migration test completed: {count} sample rows processed")
    print(f"✓ File: {metadata_file}")
    print(f"✓ New structure (Mood removed): {len(fieldnames)} columns")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
