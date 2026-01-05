from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import argparse

from rich.console import Console
from rich.table import Table

from ocr.core.reviewer import review_code
from ocr.utils.fs import iter_files, read_text_file

console = Console()


def render_report_console(report: dict) -> None:
    console.print(f"\n[bold]File:[/bold] {report['path']}")
    console.print(f"[bold]Language:[/bold] {report['language']}   [bold]Score:[/bold] {report['score']}/100")
    console.print(f"[bold]Summary:[/bold] {report['summary']}\n")

    findings = report.get("findings", [])
    if findings:
        t = Table(title="Findings", show_lines=True)
        t.add_column("Category")
        t.add_column("Severity")
        t.add_column("Lines")
        t.add_column("Title")

        for f in findings:
            ls = f.get("line_start")
            le = f.get("line_end")
            if ls is None:
                line = "?"
            else:
                line = str(ls) if le in (None, ls) else f"{ls}-{le}"
            t.add_row(str(f.get("category", "")), str(f.get("severity", "")), line, str(f.get("title", "")))

        console.print(t)


def main():
    ap = argparse.ArgumentParser(prog="ocr", description="Local code reviewer using Ollama")
    ap.add_argument("target", help="File or directory to review")
    ap.add_argument("--model", default="llama3.1:latest", help="Ollama model name (e.g., llama3.1:latest)")
    ap.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL")
    ap.add_argument("--no-recursive", action="store_true", help="Do not scan directories recursively")
    ap.add_argument("--out", default="reports", help="Output directory for JSON reports")
    ap.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    ap.add_argument("--max-files", type=int, default=30, help="Safety limit for directory scans")
    args = ap.parse_args()

    files = iter_files(args.target, recursive=not args.no_recursive)
    if not files:
        console.print("[red]No reviewable files found.[/red]")
        raise SystemExit(2)

    if len(files) > args.max_files:
        console.print(f"[red]Too many files ({len(files)}). Use --max-files or point to a smaller folder.[/red]")
        raise SystemExit(2)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for fp in files:
        code = read_text_file(fp)
        try:
            report = review_code(
                path=str(fp),
                code=code,
                model=args.model,
                base_url=args.base_url,
                temperature=args.temperature,
            )
            data = report.model_dump()
        except Exception as e:
            data = {
                "path": str(fp),
                "language": "unknown",
                "summary": f"Review failed: {e}",
                "score": 0,
                "findings": [],
            }

        render_report_console(data)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = fp.name.replace(".", "_")
        out_path = out_dir / f"{safe_name}_{stamp}.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"[dim]Saved:[/dim] {out_path}")


if __name__ == "__main__":
    main()
