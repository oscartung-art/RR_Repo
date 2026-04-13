import csv
from pathlib import Path

path = Path(r"D:\DB\.metadata.efu")
with path.open("r", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    headers = reader.fieldnames

print(f"Total rows: {len(rows)}")
print(f"Headers: {headers}")
print()

# Show first 5 rows with key fields
for r in rows[:5]:
    print(f"  Filename : {r.get('Filename','-')}")
    print(f"  Subject  : {r.get('Subject','-')}")
    print(f"  Mood     : {r.get('Mood','-')}")
    print(f"  Author   : {r.get('Author','-')}")
    print(f"  Writer   : {r.get('Writer','-')}")
    print(f"  Album    : {r.get('Album','-')}")
    print(f"  Genre    : {r.get('Genre','-')}")
    print(f"  Company  : {r.get('Company','-')}")
    print(f"  Period   : {r.get('Period','-')}")
    print(f"  Manager  : {r.get('Manager','-')}")
    print()

# Summary: fill rates
fields = ["Mood", "Author", "Writer", "Album", "Genre", "Company", "Period", "People"]
print("Field fill rates:")
for field in fields:
    filled = sum(1 for r in rows if r.get(field, "").strip() not in ("", "-"))
    print(f"  {field:<10}: {filled}/{len(rows)} filled")
