<div align="center">
# 💀 DeadHunt


**Hunt the Dead Code. Expose the Zombies.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*An AI-powered forensic scanner that surgically detects dead code, zombie dependencies, and unused imports in Python repositories.*

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [How It Works](#-how-it-works) • [Contributing](#-contributing)

</div>

---

## 🎯 Overview

**DeadHunt** is a sophisticated static analysis tool that combines AST parsing, dependency analysis, and AI-powered reasoning to identify dead code and zombie dependencies in Python projects. Unlike traditional linters, DeadHunt understands framework patterns (Django, Flask, FastAPI) and reduces false positives through intelligent context analysis.

### Why DeadHunt?

- 🔍 **Framework-Aware**: Recognizes Django models, Flask routes, FastAPI endpoints, and other framework patterns
- 🧠 **AI-Powered Analysis**: Uses LLM reasoning to distinguish real dead code from framework-invoked code
- 📊 **Comprehensive Reports**: Beautiful, interactive HTML reports with actionable insights
- 🚀 **Zero Configuration**: Just paste a GitHub URL and scan
- 🎨 **Modern UI**: Cyberpunk-inspired terminal interface with real-time progress

---

## ✨ Features

### 🔬 Dead Code Detection
- Identifies unused functions, classes, variables, and imports
- AST-based analysis with cross-file reference tracking
- Framework-specific whitelisting to avoid false positives
- Confidence scoring for each finding

### 🧟 Zombie Dependency Hunting
- Compares declared dependencies vs. actual imports
- Detects packages installed but never used
- Identifies bloated `requirements.txt` files
- Suggests safe removal candidates

### 📈 Intelligent Reporting
- Executive summary with health score
- Risk-categorized findings (High/Medium/Low)
- Actionable recommendations for each issue
- PDF export and markdown copy functionality
- Interactive table of contents with scroll spy

### 🎨 Beautiful Interface
- Cyberpunk-themed terminal UI
- Real-time scan progress
- Animated particles and scanline effects
- Responsive design for mobile and desktop

---

## 🎬 Demo

### Landing Page
```
┌─────────────────────────────────────────┐
│  💀 DeadHunt                            │
│  Hunt The Dead Code.                    │
│                                         │
│  ❯ https://github.com/user/repo        │
│    [SCAN]                               │
└─────────────────────────────────────────┘
```

### Analysis Report
- **Health Score**: Visual ring chart showing codebase health (0-100)
- **Finding Cards**: Color-coded cards with verdict badges
- **Sidebar TOC**: Auto-generated navigation with active section highlighting
- **Export Options**: PDF download and raw markdown copy

---

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Git
- pip

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/DeadHunt.git
   cd DeadHunt
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create a .env file with your API keys
   cp .env.example .env
   ```

   Add your API keys to `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENROUTER_API_KEY=your_openrouter_key_here  # Optional
   GROQ_API_KEY=your_groq_key_here              # Optional
   CEREBRAS_API_KEY=your_cerebras_key_here      # Optional
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open your browser**
   ```
   Navigate to http://localhost:5000
   ```

---

## 📖 Usage

### Web Interface

1. Open DeadHunt in your browser
2. Paste a GitHub repository URL (e.g., `https://github.com/user/repo`)
3. Click **SCAN**
4. Wait for analysis to complete (typically 30-90 seconds)
5. Review the forensic report with findings and recommendations

### Command Line (Advanced)

```python
from enginex import analyze_repo

# Analyze a repository
report = analyze_repo("https://github.com/user/repo")
print(report)
```

---

## 🔧 How It Works

### Phase 1: Clone & Parse
```
Repository → Shallow Clone → AST Parsing → Framework Detection
```
- Clones the target repository (depth=1 for speed)
- Parses all Python files into Abstract Syntax Trees
- Detects framework architecture (Django/Flask/FastAPI/Generic)

### Phase 2: Static Analysis
```
AST → Vulture Scanner → Cross-File References → Confidence Scoring
```
- Uses [Vulture](https://github.com/jendrikseipp/vulture) for dead code detection
- Performs cross-file reference analysis
- Applies framework-specific whitelists
- Assigns confidence scores (60-100%)

### Phase 3: Dependency Analysis
```
requirements.txt → Import Extraction → Diff Analysis → Zombie Detection
```
- Generates actual imports using `pipreqs` or manual AST scan
- Compares declared vs. actual dependencies
- Identifies unused packages

### Phase 4: AI Reasoning
```
Findings → LLM Analysis → Verdict Assignment → Risk Categorization
```
- Sends findings to AI model (Gemini/OpenRouter/Groq/Cerebras)
- Applies framework pattern recognition
- Distinguishes false positives from real issues
- Generates actionable recommendations

---

## 🏗️ Architecture

```
DeadHunt/
├── app.py                 # Flask application & routing
├── enginex.py             # Core analysis engine
├── deadhunt_router.py     # Multi-provider LLM failover (if exists)
├── templates/
│   ├── index.html         # Landing page
│   └── report.html        # Analysis report UI
├── .env                   # API keys (not committed)
└── README.md              # This file
```

### Key Components

- **app.py**: Flask web server, handles routing and report rendering
- **enginex.py**: Core scanning logic, AST parsing, Vulture integration, LLM communication
- **index.html**: Cyberpunk-themed landing page with terminal input
- **report.html**: Interactive forensic report with markdown rendering

---

## 🛡️ Framework Support

DeadHunt intelligently handles framework-specific patterns:

| Framework | Supported Patterns |
|-----------|-------------------|
| **Django** | Models, Meta classes, admin attributes, signals, middleware, AppConfig |
| **Flask** | Routes, blueprints, decorators, context processors |
| **FastAPI** | Path operations, dependencies, background tasks |
| **Celery** | Task decorators, worker-invoked functions |
| **Pytest** | Fixtures, test functions, conftest.py |
| **SQLAlchemy** | Model columns, relationships, event listeners |

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Format code
black .

# Lint
flake8 .
```

---

## 📊 Roadmap

- [ ] Support for JavaScript/TypeScript repositories
- [ ] GitHub Actions integration
- [ ] CLI tool for CI/CD pipelines
- [ ] VS Code extension
- [ ] Batch scanning for multiple repositories
- [ ] Historical trend analysis
- [ ] Custom rule configuration

---

## 🐛 Known Limitations

- **Python 2 Support**: Limited AST parsing for Python 2 codebases
- **Dynamic Imports**: Cannot detect runtime imports via `importlib` or `exec()`
- **Reflection Patterns**: May flag metaprogramming patterns as dead code
- **Private Repositories**: Requires public GitHub URLs (or manual cloning)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Vulture](https://github.com/jendrikseipp/vulture) - Dead code detection
- [Marked.js](https://marked.js.org/) - Markdown parsing
- [Highlight.js](https://highlightjs.org/) - Syntax highlighting
- [Google Gemini](https://ai.google.dev/) - AI-powered analysis
- [Flask](https://flask.palletsprojects.com/) - Web framework

---

## 📧 Contact

**Project Maintainer**: [Your Name]

- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com
- Twitter: [@yourhandle](https://twitter.com/yourhandle)

---

<div align="center">

**Built with 💀 by developers, for developers**

[⬆ Back to Top](#-deadhunt)

</div>
