# Coding-Projects-Folder-Analyzer
# 📂 Folder Analyzer

**Upload any codebase. Get an instant map of its structure, dependencies, and execution flow.**

🔗 **Live demo:** [folder-analyzer.vercel.app](https://folder-analyzer.vercel.app/)

---

## 🧠 What it does

Folder Analyzer is a backend service that takes a zipped project (or a folder upload) and turns it into a structured, explorable picture of the codebase without you having to read a single file yourself. It's built for the moment you're dropped into an unfamiliar repo and need to know: *where do I even start?*

Upload a project and it will:

- **Map every dependency** between files regardless of whether the project is Python, JavaScript/TypeScript, Java, C/C++, HTML, or CSS
- **Score each file's importance** using graph analysis, so you instantly know which files actually matter
- **Auto-detect entry points** and trace the execution flow from them
- **Generate a Mermaid flowchart** of how the project actually runs
- **Summarize the project in plain English** type, framework, purpose, and key modules
- **Optionally use AI (Google Gemini)** to generate a richer, natural-language summary and flow diagram, with a rule-based analysis as an always available fallback

## ⚙️ How it works

```
Upload (.zip or folder)
        │
        ▼
  Extract & scan files ──► Build file tree + stats
        │
        ▼
Dependency Analyzer (AST for Python, regex for JS/TS/Java/C++/HTML/CSS)
        │
        ▼
Importance Scorer (in-degree + PageRank + entry-point bonus → 0–100 score)
        │
        ▼
Flow Analyzer (traces execution from entry points → Mermaid diagram)
        │
        ▼
AI Summarizer (Gemini, optional falls back to rule-based summary)
        │
        ▼
     Full JSON analysis
```

### Importance scoring formula

Each file gets a 0–100 importance score, weighted from three signals:

| Signal | Weight | What it captures |
|---|---|---|
| Incoming references | 40% | How many other files depend on this one |
| PageRank centrality | 40% | How structurally central the file is in the dependency graph |
| Entry-point / special-file bonus | 20% | Whether it's a main/entry file or otherwise structurally significant |

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)
- **Dependency graphing:** NetworkX + Python `ast` module (regex-based parsing for non-Python languages)
- **AI summaries:** Google Gemini (`google-genai`), with automatic fallback if no API key is set
- **Encoding-safe file reads:** `chardet`
- **Deployment:** Vercel

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API info and available routes |
| `GET` | `/health` | Health check |
| `POST` | `/upload/zip` | Upload a `.zip` of a project and run full analysis |
| `POST` | `/upload/folder` | Upload multiple files (with relative paths) and run full analysis |
| `GET` | `/analyze/{session_id}` | Retrieve a previously computed analysis |
| `DELETE` | `/cleanup/{session_id}` | Delete a session's uploaded files and cached results |

### Example response shape

```json
{
  "session_id": "…",
  "status": "success",
  "file_tree": { "...": "..." },
  "statistics": { "total_files": 0, "total_lines": 0, "languages": [] },
  "dependencies": { "nodes": [], "edges": [] },
  "importance": [ { "file": "main.py", "score": 92.4 } ],
  "summary": { "project_type": "…", "framework": "…", "purpose": "…" },
  "flow": { "has_flow": true, "mermaid_diagram": "graph TD; ..." },
  "ai_summary": { "ai_enabled": true },
  "metadata": { "entry_points": [], "languages_detected": [] }
}
```

## 🚀 Getting Started

```bash
# Clone the repo
git clone <your-repo-url>
cd folder-analyzer

# Install dependencies
pip install -r requirements.txt

# (Optional) enable AI-powered summaries
cp .env.example .env
# then add your Gemini API key to .env — free key at https://makersuite.google.com/app/apikey

# Run the server
python main.py
# → API live at http://localhost:8000
```

> No Gemini key? No problem the analyzer still returns full dependency graphs, importance scores, and rule-based summaries without it.

## 📁 Project Structure

```
├── main.py                     # FastAPI app & routes
├── analyzer/
│   ├── dependency_analyzer.py  # Multi-language import/dependency parsing
│   ├── importance_scorer.py    # Graph-based file importance scoring
│   ├── project_summarizer.py   # Project type/framework/purpose detection
│   ├── flow_analyzer.py        # Execution flow tracing + Mermaid diagrams
│   └── ai_summarizer.py        # Gemini-powered summaries (optional)
├── utils/
│   └── file_handler.py         # Upload handling, zip extraction, file tree
└── requirements.txt
```

## 🗺️ Roadmap

- [ ] Persistent storage for analysis results (Redis, currently in-memory)
- [ ] Support for additional languages (Go, Rust, PHP, Ruby)
- [ ] Interactive dependency graph visualization in the frontend
- [ ] Exportable project reports (PDF/Markdown)

## 🤝 Contributing

Issues and pull requests are welcome. If you spot a language whose imports aren't being parsed correctly, that's a great first contribution.


## 👥 Team

- [Soham Jathar](https://www.linkedin.com/in/soham-jathar-20b9302a8?utm_source=share_via&utm_content=profile&utm_medium=member_android)
- [Prathamesh Kolhe](https://www.linkedin.com/in/kolhe-prathamesh?utm_source=share_via&utm_content=profile&utm_medium=member_android)
- [Onkar Deshmukh](https://www.linkedin.com/in/onkar-deshmukh-981a79314?utm_source=share_via&utm_content=profile&utm_medium=member_android)
- [Bhavika Kadam](https://www.linkedin.com/in/bhavika-kadam-a939a928a?utm_source=share_via&utm_content=profile&utm_medium=member_android)

