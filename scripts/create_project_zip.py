"""
Script to create a clean ZIP archive of the entire COBRA-WATCH project.
Excludes build artifacts and dependencies (node_modules, __pycache__, .pytest_cache).
"""
import os
import zipfile
import shutil

def create_zip():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_name = "COBRA_WATCH_Project_Complete.zip"
    zip_path = os.path.join(project_dir, zip_name)

    artifact_dir = r"C:\Users\goldi\.gemini\antigravity-ide\brain\874b58b9-277e-4f6a-a0dd-adb1c90aba88"
    artifact_zip_path = os.path.join(artifact_dir, zip_name)

    exclude_dirs = {
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.venv',
        'venv',
        '.git',
        '.idea',
        '.vscode',
        'dist',
        'build'
    }

    exclude_files = {
        '.DS_Store',
        'thumbs.db'
    }

    print(f"[ZIP] Creating project zip: {zip_path}")
    file_count = 0
    total_uncompressed = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            # Exclude directories in-place
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]

            for file in files:
                if file in exclude_files or file.endswith('.pyc') or file == zip_name:
                    continue

                abs_filepath = os.path.join(root, file)
                rel_filepath = os.path.relpath(abs_filepath, project_dir)

                zipf.write(abs_filepath, rel_filepath)
                file_count += 1
                total_uncompressed += os.path.getsize(abs_filepath)

    zip_size = os.path.getsize(zip_path)
    print(f"[SUCCESS] Zip created successfully!")
    print(f"  Files included: {file_count}")
    print(f"  Uncompressed size: {total_uncompressed / (1024*1024):.2f} MB")
    print(f"  Compressed ZIP size: {zip_size / (1024*1024):.2f} MB")

    # Copy to artifacts directory if it exists
    if os.path.exists(artifact_dir):
        shutil.copyfile(zip_path, artifact_zip_path)
        print(f"  Copied to artifacts dir: {artifact_zip_path}")

if __name__ == "__main__":
    create_zip()
