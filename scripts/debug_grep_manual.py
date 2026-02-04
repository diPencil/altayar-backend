
import os

def find_text_in_files(root_dir, search_text):
    print(f"Searching for '{search_text}' in {root_dir}...")
    found = False
    for root, dirs, files in os.walk(root_dir):
        if "venv" in dirs:
            dirs.remove("venv")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
            
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if search_text in line:
                                print(f"FOUND in {path}:{i+1}")
                                print(f"  > {line.strip()}")
                                found = True
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    
    if not found:
        print("Text NOT FOUND in any allowed file.")

if __name__ == "__main__":
    find_text_in_files("d:/Development/altayar/MobileApp/backend", "user_uuid")
