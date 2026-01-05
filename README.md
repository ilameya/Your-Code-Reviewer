# YCR - Your Code Reviewer

YCR is a **local, advisory-only code reviewer** powered by a locally running LLM (via Ollama).  
It analyzes source code files and returns **structured, human-readable feedback** without modifying code.

- Runs **entirely locally**


---

## Features

- Review individual files or directories
- LLM-powered analysis using Ollama
- Structured output (JSON)
- CLI for terminal users
- Streamlit UI for interactive use
- Findings include severity, category, line numbers, and suggestions
- Explains problems, never edits your code

---

## Supported Languages

Any text-based source file, including (but not limited to):

- Python, C, C++, Java, JavaScript, TypeScript
- Go, Rust, C#, PHP, Ruby
- Swift, Kotlin, Scala
- Shell scripts and config-like files

Binary files are automatically skipped.

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) running locally
- A local model installed (e.g. `llama3.1`)

---

## Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-username/ycr.git
cd ycr
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Install Streamlit (for the UI)
```bash
pip install streamlit pandas
```

### Make sure Ollama is running
```bash
ollama serve
```
---

## CLI Usage 

Review a single file:
```bash
ocr tests/file.py --model model-name
```
The CLI prints a readable summary and saves a JSON report to the reports/ directory.

---

## Streamlit UI

Run the UI:
```bash
streamlit run streamlit_app.py
```
Features:
- Upload one or more code files
- Configure model, temperature, and server URL
- Filter findings by severity
- Search within findings
- Download JSON reports
- The UI uses the same review engine as the CLI

---

## Notes

YCR is intentionally not an auto-fixing tool. This makes YCR suitable for:
- Learning
- Code review assistance
- Offline environments
- Sensitive or private codebases

