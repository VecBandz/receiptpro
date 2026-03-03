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

### Deploy SaaS to Vercel

The `deploy-saas.yml` workflow triggers on every push to `main` that touches `web/`, `core/`, or the requirements files. It:

1. Builds and verifies the app
2. Sends an email when the build is **ready to deploy**
3. Deploys to Vercel via the Vercel CLI
4. Sends an email when the deployment is **complete** (or if it **fails**)

Add these secrets to the repository:

| Secret | Description |
|---|---|
| `VERCEL_TOKEN` | Vercel personal access token |
| `VERCEL_ORG_ID` | Vercel team/org ID (found in Vercel project settings) |
| `VERCEL_PROJECT_ID` | Vercel project ID (found in Vercel project settings) |
| `NOTIFY_EMAIL` | Email address to receive build/deploy notifications |
| `MAIL_SERVER` | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `MAIL_USERNAME` | SMTP login username |
| `MAIL_PASSWORD` | SMTP login password or app password |

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
