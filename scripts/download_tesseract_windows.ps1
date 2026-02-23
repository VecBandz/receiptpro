# Download and silently install Tesseract OCR on Windows CI
# Sets the TESSERACT_DIR environment variable for subsequent steps.

$ErrorActionPreference = "Stop"

$installerUrl = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
$installerPath = "$env:TEMP\tesseract-installer.exe"
$installDir = "C:\Program Files\Tesseract-OCR"

Write-Host "Downloading Tesseract installer..."
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing

Write-Host "Installing Tesseract silently..."
Start-Process -FilePath $installerPath -ArgumentList "/S", "/D=$installDir" -Wait -NoNewWindow

if (-not (Test-Path "$installDir\tesseract.exe")) {
    Write-Error "Tesseract installation failed — tesseract.exe not found at $installDir"
    exit 1
}

Write-Host "Tesseract installed at: $installDir"

# Export for subsequent GitHub Actions steps
"TESSERACT_DIR=$installDir" | Out-File -Append -Encoding utf8 $env:GITHUB_ENV
