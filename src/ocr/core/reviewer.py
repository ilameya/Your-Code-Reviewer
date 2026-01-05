from __future__ import annotations

import json
import requests
from pathlib import Path

from ocr.core.schemas import ReviewReport
from ocr.core.chunking import chunk_text

OLLAMA_URL_DEFAULT = "http://localhost:11434"


def _load_prompt(name: str) -> str:
    here = Path(__file__).resolve().parents[1] / "prompts"
    return (here / name).read_text(encoding="utf-8")


SYSTEM_PROMPT = _load_prompt("system.txt")
REVIEW_PROMPT = _load_prompt("review.txt")


def ollama_generate(
    *,
    model: str,
    prompt: str,
    system: str,
    base_url: str = OLLAMA_URL_DEFAULT,
    temperature: float = 0.2,
    num_ctx: int = 4096,
) -> str:
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
        },
    }

    r = requests.post(url, json=payload, timeout=300)
    if not r.ok:
        raise RuntimeError(
            f"Ollama error {r.status_code} for {url}\n"
            f"Model: {model}\n"
            f"Response:\n{r.text}\n"
        )

    return r.json()["response"]


def detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
    }.get(ext, "unknown")


def normalize_report_obj(obj: dict, *, fallback_path: str, fallback_language: str) -> dict:
    """
    Normalize LLM output to match the minimal ReviewReport schema.
    Advisory-only. No patches. No extras.
    """
    if not isinstance(obj, dict):
        obj = {}

    obj["path"] = obj.get("path", fallback_path)
    obj["language"] = obj.get("language", fallback_language)
    obj["summary"] = str(obj.get("summary", "No summary provided."))

    # score: int 0–100
    try:
        obj["score"] = int(round(float(obj.get("score", 0))))
    except Exception:
        obj["score"] = 0
    obj["score"] = max(0, min(100, obj["score"]))

    allowed_categories = {"bug", "security", "style", "design", "performance", "testing", "docs"}
    allowed_severities = {"low", "medium", "high", "critical"}

    findings = obj.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    for f in findings:
        if not isinstance(f, dict):
            continue

        # category
        cat = str(f.get("category", "bug")).lower().strip()
        if cat not in allowed_categories:
            cat = "bug"
        f["category"] = cat

        # severity
        sev = str(f.get("severity", "medium")).lower().strip()
        if sev not in allowed_severities:
            sev = "medium"
        f["severity"] = sev

        # required fields
        f["title"] = str(f.get("title", "Untitled issue"))
        f["details"] = str(f.get("details", ""))
        f["line_start"] = int(f.get("line_start", 0))
        f["line_end"] = int(f.get("line_end", f["line_start"]))
        f["suggestion"] = str(f.get("suggestion", "Provide a fix for this issue."))

    obj["findings"] = findings
    return obj


def _merge_reports(path: str, language: str, reports: list[ReviewReport]) -> ReviewReport:
    if len(reports) == 1:
        return reports[0]

    summaries = []
    findings = []
    scores = []

    for r in reports:
        summaries.append(r.summary.strip())
        findings.extend(r.findings)
        scores.append(r.score)

    # severity-based penalty
    sev_penalty = {"low": 5, "medium": 15, "high": 30, "critical": 50}
    max_penalty = max((sev_penalty.get(f.severity, 0) for f in findings), default=0)

    avg_score = round(sum(scores) / len(scores))
    avg_score = max(0, min(100, avg_score - max_penalty))

    summary = " | ".join(dict.fromkeys(summaries))[:1200]

    return ReviewReport(
        path=path,
        language=language,
        summary=summary,
        score=avg_score,
        findings=findings,
    )


def review_code(
    *,
    path: str,
    code: str,
    model: str = "llama3.1:latest",
    base_url: str = OLLAMA_URL_DEFAULT,
    temperature: float = 0.2,
) -> ReviewReport:
    language = detect_language(path)
    chunks = chunk_text(code, max_chars=12000)

    reports: list[ReviewReport] = []

    for idx, chunk in enumerate(chunks, start=1):
        chunk_path = path if len(chunks) == 1 else f"{path} (chunk {idx}/{len(chunks)})"
        prompt = REVIEW_PROMPT.format(language=language, path=chunk_path, code=chunk)

        raw = ollama_generate(
            model=model,
            prompt=prompt,
            system=SYSTEM_PROMPT,
            base_url=base_url,
            temperature=temperature,
        )

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Ollama returned non-JSON output.\nError: {e}\nRaw:\n{raw[:1000]}"
            )

        obj = normalize_report_obj(obj, fallback_path=chunk_path, fallback_language=language)
        reports.append(ReviewReport.model_validate(obj))

    return _merge_reports(path=path, language=language, reports=reports)
