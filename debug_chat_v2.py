import sys
import os

print("Attempting to import modules.chat.routes...")

try:
    from modules.chat import routes
    print("✅ Successfully imported modules.chat.routes")
except Exception as e:
    print("\n❌ Exception during import:")
    import traceback
    traceback.print_exc()
