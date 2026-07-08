import os

# Configuration: Names of directories or files to skip entirely
IGNORE_DIRS = {'.git', '.venv', 'env', 'venv', '__pycache__', '.pytest_cache', '.idea', '.vscode'}
IGNORE_FILES = {'pack_repo.py'}  # Skip this script itself

def pack_python_files(output_filename="repo_context.txt"):
    """Scans the directory tree, reads all .py files, and combines them into one text file."""
    root_dir = os.getcwd()
    
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        # Loop through all files and directories
        for current_dir, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file.endswith('.py') and file not in IGNORE_FILES:
                    # Determine paths
                    full_path = os.path.join(current_dir, file)
                    relative_path = os.path.relpath(full_path, root_dir)
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                        
                        # Write structured headers for AI Studio
                        outfile.write(f"========================================\n")
                        outfile.write(f"FILE PATH: {relative_path}\n")
                        outfile.write(f"========================================\n\n")
                        outfile.write(content)
                        outfile.write("\n\n")
                        print(f"Packed: {relative_path}")
                        
                    except Exception as e:
                        print(f"Error reading {relative_path}: {e}")
                        
    print(f"\nSuccess! Full codebase dumped into: {output_filename}")

if __name__ == "__main__":
    pack_python_files()
