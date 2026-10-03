import os
import shutil
import glob
from pathlib import Path
from typing import Dict, List, Any

# Map common file extensions to category folders
CATEGORY_MAPPING = {
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".md"],
    "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
    "Code_Scripts": [".py", ".js", ".html", ".css", ".json", ".ts", ".jsx", ".tsx", ".sh", ".bat", ".ps1"],
    "Audio_Video": [".mp3", ".mp4", ".wav", ".mkv", ".mov", ".avi", ".flac"],
    "Executables_Installers": [".exe", ".msi", ".iso"]
}

def get_category_for_ext(extension: str) -> str:
    ext = extension.lower()
    for cat, exts in CATEGORY_MAPPING.items():
        if ext in exts:
            return cat
    return "Other"

def list_directory_contents(directory_path: str = ".", pattern: str = "*") -> str:
    """Lists files and folders in a specified directory with sizes and types."""
    try:
        if not directory_path or directory_path.strip() == "":
            directory_path = "."
        if not pattern or pattern.strip() == "":
            pattern = "*"
            
        p = Path(directory_path).expanduser().resolve()
        if not p.exists():
            return f"Error: Directory '{directory_path}' does not exist."
        
        items = list(p.glob(pattern))
        if not items:
            return f"Directory '{p}' contains 0 items matching pattern '{pattern}'."
            
        summary = [f"Directory contents for: {p}"]
        summary.append(f"{'TYPE':<6} | {'SIZE':<10} | {'NAME'}")
        summary.append("-" * 50)
        
        for item in sorted(items[:60], key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.is_dir():
                summary.append(f"DIR    | {'-':<10} | {item.name}/")
            else:
                size_kb = item.stat().st_size / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
                summary.append(f"FILE   | {size_str:<10} | {item.name}")
                
        if len(items) > 60:
            summary.append(f"... and {len(items) - 60} more items.")
        return "\n".join(summary)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def organize_folder(directory_path: str = ".", dry_run: bool = False) -> str:
    """Organizes unorganized files in a target directory into category subfolders (Images, Documents, etc.)."""
    try:
        if not directory_path or directory_path.strip() == "":
            directory_path = "."
        p = Path(directory_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            return f"Error: '{directory_path}' is not a valid directory."
            
        files_to_move = [f for f in p.iterdir() if f.is_file()]
        if not files_to_move:
            return f"No loose files found in '{p}' to organize."
            
        plan = []
        moved_count = 0
        for file in files_to_move:
            cat = get_category_for_ext(file.suffix)
            dest_dir = p / cat
            dest_file = dest_dir / file.name
            
            if dry_run:
                plan.append(f"[PREVIEW] '{file.name}' -> '{cat}/{file.name}'")
            else:
                dest_dir.mkdir(exist_ok=True)
                # Avoid overwriting
                if dest_file.exists():
                    dest_file = dest_dir / f"{file.stem}_copy{file.suffix}"
                shutil.move(str(file), str(dest_file))
                moved_count += 1
                plan.append(f"[MOVED] '{file.name}' -> '{cat}/'")
                
        status_header = "DRY RUN PREVIEW (No changes made):" if dry_run else f"Successfully organized {moved_count} files:"
        return status_header + "\n" + "\n".join(plan[:50])
    except Exception as e:
        return f"Error organizing folder: {str(e)}"

def read_file_content(file_path: str, max_chars: int = 4000) -> str:
    """Reads content of a text file."""
    try:
        p = Path(file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return f"Error: File '{file_path}' does not exist or is not a regular file."
        
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
            if len(content) >= max_chars:
                content += "\n... [Content truncated at limit]"
            return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

def bulk_rename_files(directory_path: str, find_str: str, replace_str: str, dry_run: bool = False) -> str:
    """Finds and replaces text patterns in filenames inside a folder."""
    try:
        p = Path(directory_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            return f"Error: '{directory_path}' is not a valid directory."
            
        matches = [f for f in p.iterdir() if f.is_file() and find_str in f.name]
        if not matches:
            return f"No files found containing '{find_str}' in '{p}'."
            
        logs = []
        renamed = 0
        for f in matches:
            new_name = f.name.replace(find_str, replace_str)
            target = p / new_name
            if dry_run:
                logs.append(f"[PREVIEW] Rename '{f.name}' -> '{new_name}'")
            else:
                f.rename(target)
                renamed += 1
                logs.append(f"[RENAMED] '{f.name}' -> '{new_name}'")
                
        header = "DRY RUN PREVIEW:" if dry_run else f"Successfully renamed {renamed} files:"
        return header + "\n" + "\n".join(logs)
    except Exception as e:
        return f"Error renaming files: {str(e)}"

def create_or_write_file(file_path: str, content: str) -> str:
    """Creates or updates a file with provided text content."""
    try:
        p = Path(file_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{p}' written successfully ({len(content)} characters)."
    except Exception as e:
        return f"Error writing file: {str(e)}"
