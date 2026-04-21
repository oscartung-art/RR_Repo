from pathlib import Path
import csv
import sys

src = Path(r'E:\Database\CurrentDB.csv')
if not src.exists():
    print('ERROR: source file not found:', src)
    sys.exit(2)

out_dir = Path(r'G:\DB\designconnected')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / '.metadata.efu'

with src.open('r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    rows = list(reader)

if not rows:
    print('ERROR: source file is empty')
    sys.exit(3)

header = rows[0]
matches = [r for r in rows[1:] if any('designconnected' in (c or '').lower() for c in r)]

with out_file.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(matches)

print(f'Wrote {len(matches)} entries to {out_file}')
# print first 5 matched filenames for quick verification
for r in matches[:5]:
    if r:
        print(r[0])
