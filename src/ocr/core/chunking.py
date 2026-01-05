from __future__ import annotations

def chunk_text(text: str, max_chars: int = 12000) -> list[str]:
    """
    Very simple chunker: split by lines to keep structure.
    max_chars is intentionally conservative for local models.
    """
    if len(text) <= max_chars:
        return [text]

    lines = text.splitlines(keepends=True)
    chunks = []
    buf = []
    size = 0

    for ln in lines:
        if size + len(ln) > max_chars and buf:
            chunks.append("".join(buf))
            buf = []
            size = 0
        buf.append(ln)
        size += len(ln)

    if buf:
        chunks.append("".join(buf))

    return chunks
