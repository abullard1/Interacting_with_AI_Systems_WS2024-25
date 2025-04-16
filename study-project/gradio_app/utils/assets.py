import os

def load_asset(file_path, asset_type=None):
    if not os.path.exists(file_path):
        return ""
        
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Error loading asset {file_path}: {str(e)}")
        return ""