from __future__ import annotations
from pathlib import Path

TEXT_EXTS = {
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".cs",
    ".md", ".txt", ".yml", ".yaml", ".toml", ".json"
}

def iter_files(target: str, recursive: bool = True) -> list[Path]:
    p = Path(target)
    if p.is_file():
        return [p]

    files = []
    if recursive:
        for fp in p.rglob("*"):
            if fp.is_file() and fp.suffix.lower() in TEXT_EXTS:
                files.append(fp)
    else:
        for fp in p.glob("*"):
            if fp.is_file() and fp.suffix.lower() in TEXT_EXTS:
                files.append(fp)

    return sorted(files)

def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
