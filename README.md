# ReceiptPro

Receipt OCR desktop app and SaaS web app. Extracts text from receipt images/PDFs, parses key fields (company, date, amount, payment method, items), and exports to Excel.

## Project structure

```
receiptpro/
├── core/           # Shared business logic (OCR, parsing, Excel export)
├── desktop/        # customtkinter GUI app + PyInstaller entry point
├── web/            # Flask web app with SSE progress and Excel download
├── scripts/        # Windows CI helper scripts (Tesseract + Poppler)
├── .github/
│   └── workflows/  # build-desktop.yml (releases) + deploy.yml (Docker)
├── Dockerfile
├── docker-compose.yml
├── receiptpro.spec  # PyInstaller spec
└── requirements-*.txt
```

## Desktop app

### Local run

```bash
pip install -r requirements-desktop.txt
# Linux/macOS: ensure tesseract and poppler are installed via your package manager
python desktop/app.py
```

### Build standalone executable

```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
pip install -r requirements-desktop.txt
pyinstaller receiptpro.spec

# Windows (set env vars first)
$env:TESSERACT_DIR = "C:\Program Files\Tesseract-OCR"
$env:POPPLER_DIR   = "C:\poppler\Library\bin"
pip install -r requirements-desktop.txt
pyinstaller receiptpro.spec
```

The executable is output to `dist/ReceiptPro` (Linux) or `dist/ReceiptPro.exe` (Windows).

### CI releases

Push a tag like `v1.0.0` to trigger `build-desktop.yml`. Both Linux and Windows executables will be attached to a GitHub Release automatically.

## Web app

### Local run

```bash
pip install -r requirements-web.txt
# Ensure tesseract and poppler are installed
flask --app web.app run
# Visit http://localhost:5000
```

### Docker (local)

```bash
docker compose up --build
# Visit http://localhost:5000
```

### Deploy to server

1. Add GitHub repository secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`
2. Push to `main` — the `deploy.yml` workflow builds the Docker image, pushes it to GHCR, and restarts the container via SSH.

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `TESSERACT_CMD` | core/ocr.py | Override path to `tesseract` binary |
| `POPPLER_PATH` | core/ocr.py | Override path to Poppler `bin` directory |
| `TESSERACT_DIR` | receiptpro.spec, CI | Directory bundled into frozen binary |
| `POPPLER_DIR` | receiptpro.spec, CI | Directory bundled into frozen binary |

## Requirements

- Python 3.11+
- Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-eng`)
- Poppler utilities (`poppler-utils`)
