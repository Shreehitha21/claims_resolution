import os
import zipfile
import sys

def create_zip():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    zip_path = os.path.join(base_dir, 'claims_resolution_agent.zip')
    
    ignore_dirs = {'.git', 'venv', '__pycache__', '.pytest_cache'}
    ignore_files = {'.env', 'claims.db'} # Never package DB or local secrets
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file in ignore_files or file.endswith('.pyc') or file == 'claims_resolution_agent.zip':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, arcname)
                
    print(f"Archive created successfully: {zip_path}")

if __name__ == "__main__":
    create_zip()