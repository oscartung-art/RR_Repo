import sys
import os
from pathlib import Path

# Run directly - don't use subprocess
sys.path.insert(0, str(Path(__file__).parent / "tools"))

# Now run extract_schedule_json
import importlib
sys.argv = [
    'extract_schedule_json.py',
    '--dry-run',
    r"G:\DB\sandbox\1. 1F Material Specification_20230418 Extract[2,18,21,37].pdf"
]

spec = importlib.util.spec_from_file_location("extract_schedule_json", r"D:\rr_repo\tools\extract_schedule_json.py")
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except SystemExit as e:
    print(f"Exit code: {e.code}")

