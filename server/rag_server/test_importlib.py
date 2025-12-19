
import sys
import importlib.util
from pathlib import Path
import os

# Mimic crawler_worker.py location
current_dir = Path(__file__).resolve().parent
server_dir = current_dir.parent
linebot_dir = server_dir / "linebot"
env_path = linebot_dir / ".env"

print(f"Current dir: {current_dir}")
print(f"Linebot dir: {linebot_dir}")
print(f"Env path: {env_path}")

# Load .env (just to check existence)
if env_path.exists():
    print("✅ Found .env")
else:
    print("❌ .env not found")

# Use importlib to load linebot/app.py
try:
    module_name = "linebot_server_app"
    file_path = linebot_dir / "app.py"
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    print(f"✅ Successfully loaded module: {module}")
    print(f"Messaging API: {hasattr(module, 'messaging_api')}")
    
    import linebot_server_app
    print(f"✅ Successfully imported linebot_server_app")
    
except Exception as e:
    print(f"❌ Failed to load module with importlib: {e}")
    import traceback
    traceback.print_exc()
