import subprocess
import sys
import time
import os

os.chdir(r"C:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate\backend")
python = r"C:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate\backend\venv\Scripts\python.exe"

# Use Start-Process equivalent - launch detached
proc = subprocess.Popen(
    [python, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
    cwd=r"C:\Users\宿心\WorkBuddy\EasyTranslate\paper-translate\backend",
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    close_fds=True
)

print(f"Started backend PID: {proc.pid}")
print("Waiting 5s...")

time.sleep(5)

# Test health
import urllib.request
try:
    resp = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
    print(f"Health check: {resp.status} - {resp.read().decode()}")
except Exception as e:
    print(f"Health check FAILED: {e}")
