from pathlib import Path
import csv
import sys

candidates = [Path(r'G:\db\project\.metadata.efu'), Path(r'G:\DB\project\.metadata.efu')]
proj_file = None
for c in candidates:
    if c.exists():
        proj_file = c
        break

if proj_file is None:
    print('ERROR: project metadata file not found. Checked:', candidates, file=sys.stderr)
    sys.exit(2)

tmp = proj_file.with_suffix('.tmp')

with proj_file.open('r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    rows = list(reader)

if not rows:
    print('ERROR: file is empty', file=sys.stderr)
    sys.exit(3)

header = rows[0]
try:
    idx = header.index('custom_property_5')
except ValueError:
    print("ERROR: 'custom_property_5' column not found", file=sys.stderr)
    sys.exit(4)

targets = {
    'Bed_Flou_10965538.jpg',
    'Bed_LazeBed_FF098791.jpg',
    'BedroomFurniture_FendiBed_8779E4B5.jpg',
}
updated = 0
for i in range(1, len(rows)):
    r = rows[i]
    if r and r[0] in targets:
        if len(r) <= idx:
            r.extend([''] * (idx - len(r) + 1))
        r[idx] = 'King'
        updated += 1

with tmp.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)

# Atomic replace
try:
    tmp.replace(proj_file)
except Exception as e:
    print('ERROR replacing file:', e, file=sys.stderr)
    sys.exit(5)

print(f'Updated {updated} rows in {proj_file}')

# Print updated rows for verification
with proj_file.open('r', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    for r in reader:
        if r and r[0] in targets:
            print(','.join(r))
