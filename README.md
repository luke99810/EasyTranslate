# EasyTranslate - Academic PDF Translation Tool

A professional academic PDF translation tool for researchers, featuring Deepl, Google, and OpenAI translation engines with bilingual对照阅读 support.

## 📦 Project Overview

EasyTranslate is a web-based tool that translates academic papers (English to Chinese) while preserving original formatting. It intelligently protects LaTeX formulas and provides horizontal/vertical bilingual comparison modes.

## ✨ Features

- **Multi-engine Support**: DeepL, Google, OpenAI translation APIs
- **Format Preservation**: Maintains original PDF layout
- **LaTeX Protection**: Intelligently isolates and protects mathematical formulas
- **Bilingual Reading**: Horizontal and vertical comparison modes
- **Export Options**: PDF and Word format export
- **Docker Deploy**: Lightweight one-click deployment via Docker Compose

## 🛠️ Tech Stack

- **Frontend**: React 18 / Vite / TailwindCSS / Zustand
- **Backend**: Python 3.10+ / FastAPI / PyMuPDF
- **Deployment**: Docker Compose

## 📂 Project Structure

```
EasyTranslate/
├── paper-translate/           # Backend service
│   └── backend/
│       ├── app/              # API routes
│       ├── Dockerfile
│       └── requirements.txt
├── docs/                      # Documentation
│   ├── 市场调研与竞品分析.md
│   ├── 产品需求文档(PRD).md
│   └── 技术架构设计.md
├── DEPLOYMENT.md              # Deployment guide
├── User Guide.md              # User manual
└── README.md
```

## 🚀 Quick Start

### Backend

```bash
cd paper-translate/backend
pip install -r requirements.txt
docker build -t easytranslate-backend .
docker run -p 8000:8000 easytranslate-backend
```

### Frontend

```bash
# Use the hosted version or deploy your own
# Access at http://localhost:5173
```

### Docker Compose (Full Stack)

```bash
docker-compose up -d
```

## 📖 Documentation

- [User Guide](User%20Guide.md) - Detailed usage instructions
- [Deployment Guide](DEPLOYMENT.md) - Docker deployment tutorial
- [PRD](docs/产品需求文档(PRD).md) - Product requirements

## 📄 License

MIT License
