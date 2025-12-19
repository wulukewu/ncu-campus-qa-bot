
import sys
from pathlib import Path
import os

# Mocking the location as if we are in rag_server
current_file = Path(r"c:/finalproject.github/ncu-campus-qa-bot/ncu-campus-qa-bot/server/rag_server/crawler_worker.py")
server_dir = current_file.parent.parent
linebot_dir = server_dir / "linebot"

print(f"Server dir: {server_dir}")
print(f"Linebot dir: {linebot_dir}")

# Test 1: Try importing as package
sys.path.append(str(server_dir))
try:
    from linebot import app
    print("✅ Successfully imported linebot.app via package")
except ImportError as e:
    print(f"❌ Failed to import linebot.app via package: {e}")

# Test 2: Try importing via direct path
sys.path.append(str(linebot_dir))
try:
    import app
    print("✅ Successfully imported app via direct path")
except ImportError as e:
    print(f"❌ Failed to import app via direct path: {e}")
