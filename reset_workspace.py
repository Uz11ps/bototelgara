import os
import shutil
import sys

def reset_workspace():
    current_dir = os.getcwd()
    temp_clone_dir = os.path.join(current_dir, "temp_clone")
    
    if not os.path.exists(temp_clone_dir):
        print("Error: temp_clone directory not found!")
        return

    # Files/Dirs to preserve
    preserve = {".env", "temp_clone", "reset_workspace.py", ".git"} 

    print("Cleaning workspace...")
    for item in os.listdir(current_dir):
        if item in preserve:
            continue
        
        item_path = os.path.join(current_dir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
            print(f"Deleted: {item}")
        except Exception as e:
            print(f"Failed to delete {item}: {e}")

    print("Moving files from temp_clone...")
    for item in os.listdir(temp_clone_dir):
        src_path = os.path.join(temp_clone_dir, item)
        dst_path = os.path.join(current_dir, item)
        
        # If destination exists (e.g. .gitignore if we missed it), remove it first
        if os.path.exists(dst_path):
            if os.path.isfile(dst_path) or os.path.islink(dst_path):
                os.unlink(dst_path)
            elif os.path.isdir(dst_path):
                shutil.rmtree(dst_path)
                
        shutil.move(src_path, dst_path)
        print(f"Moved: {item}")

    print("Removing temp_clone...")
    os.rmdir(temp_clone_dir)
    print("Workspace reset complete.")

if __name__ == "__main__":
    reset_workspace()
