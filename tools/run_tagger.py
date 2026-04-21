import subprocess
import time
import os

script = "scripts/search_tag_assets.py"
last_mtime = os.path.getmtime(script)

print("[auto-restart] Starting tagger with auto-restart on file changes...")
print(f"[auto-restart] Watching: {script}")

while True:
    try:
        proc = subprocess.Popen([
            os.path.join(".venv", "Scripts", "python.exe"),
            script
        ])
        
        while True:
            if os.path.getmtime(script) != last_mtime:
                print("\n[auto-restart] Script changed, restarting...")
                last_mtime = os.path.getmtime(script)
                proc.terminate()
                proc.wait()
                time.sleep(0.5)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[auto-restart] Stopping...")
        proc.terminate()
        break
    except Exception as e:
        print(f"[auto-restart] Error: {e}")
        time.sleep(2)
