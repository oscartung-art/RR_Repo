#!/usr/bin/env python3
"""
Migrate asset classification from Mood column to Subject column in .metadata.efu
"""

import csv
import shutil
from pathlib import Path

# File paths
metadata_file = r'd:\DB\.metadata.efu'
backup_file = r'd:\DB\.metadata.efu.backup'

try:
    # Step 1: Create backup
    print("Creating backup...")
    shutil.copy2(metadata_file, backup_file)
    print(f"✓ Backup created: {backup_file}")
    
    # Step 2: Read the CSV and perform migration
    print("\nReading and migrating data...")
    rows = []
    migrated_samples = []
    row_count = 0
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # Process each row
        for row in reader:
            old_subject = row['Subject']
            row['Subject'] = row['Mood']  # Move Mood → Subject
            rows.append(row)
            row_count += 1
            
            # Collect first 3 samples
            if len(migrated_samples) < 3 and row['Subject'].strip() and row['Subject'] != '-':
                migrated_samples.append({
                    'filename': row['Filename'],
                    'old_mood': row['Mood'],
                    'old_subject': old_subject,
                    'new_subject': row['Subject']
                })
    
    # Step 3: Remove Mood column from fieldnames
    new_fieldnames = [col for col in fieldnames if col != 'Mood']
    
    # Step 4: Remove Mood key from each row dict
    for row in rows:
        if 'Mood' in row:
            del row['Mood']
    
    # Step 5: Write updated CSV
    print(f"Writing migrated CSV ({row_count} rows)...")
    with open(metadata_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Step 6: Verify
    print("\nVerifying migration...")
    verify_count = 0
    with open(metadata_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Subject'].strip():  # Check if Subject has data
                verify_count += 1
    
    # Summary Report
    print("\n" + "="*70)
    print("MIGRATION SUMMARY: Mood → Subject")
    print("="*70)
    print(f"✓ Backup created: Y")
    print(f"✓ Rows processed: {row_count}")
    print(f"✓ Rows with Subject data (non-empty): {verify_count}/{row_count}")
    print(f"\nNew CSV structure (Mood column removed):")
    print(f"{','.join(new_fieldnames)}")
    
    if migrated_samples:
        print(f"\n{'Sample migrated rows (Mood → Subject):':^70}")
        print("-"*70)
        for i, sample in enumerate(migrated_samples, 1):
            print(f"\nRow {i} - {sample['filename']}")
            print(f"  Old Mood:     {sample['old_mood']}")
            print(f"  Old Subject:  {sample['old_subject']}")
            print(f"  New Subject:  {sample['new_subject']}")
    
    print("\n" + "="*70)
    print("✓ CSV Migration completed successfully!")
    print("="*70)
    
except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    print("Migration failed. Backup preserved at:", backup_file)
    import traceback
    traceback.print_exc()
