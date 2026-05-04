import os
import shutil
import git
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".md", ".json", ".yaml", ".yml",
    ".html", ".css", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".rb",
    ".php", ".sh", ".toml", ".ini", ".cfg",
}

SKIP_DIRS = {
    ".git", "node_modules", "venv", "__pycache__",
    ".venv", "dist", "build", ".next", ".nuxt",
    "coverage", ".pytest_cache", "vendor",
}


MAX_FILE_SIZE_BYTES = 50_000


def clone_repo(url: str, dest: Path) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    print(f"Cloning {url} → {dest}")
    git.Repo.clone_from(url, str(dest), depth=1)
    return dest

def extract_files(repo_path: Path) -> list[dict]:
    """
    Walk the cloned repo and return a list of dicts with:
      - path: relative file path (string)
      - content: file text
      - extension: file suffix
    """
    repo_path = Path(repo_path)
    files = []
 
    for filepath in repo_path.rglob("*"):
        if not filepath.is_file():
            continue
 
        # Skip hidden / build / dependency directories
        parts = set(filepath.relative_to(repo_path).parts)
        if parts & SKIP_DIRS:
            continue
 
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            continue
 
        if filepath.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue
 
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                continue
            files.append({
                "path": str(filepath.relative_to(repo_path)),
                "content": content,
                "extension": filepath.suffix,
            })
        except Exception:
            continue
 
    print(f"Extracted {len(files)} files from {repo_path.name}")
    return files


def repo_name_from_url(url: str) -> str:
    """Extract 'owner-repo' slug from a GitHub URL."""
    url = url.rstrip("/")
    parts = url.split("/")
    return f"{parts[-2]}-{parts[-1]}"