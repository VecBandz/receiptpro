# Download Poppler for Windows (oschwartz10612 build) and set POPPLER_DIR.

$ErrorActionPreference = "Stop"

$popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.02.0-0/Release-24.02.0-0.zip"
$zipPath    = "$env:TEMP\poppler.zip"
$extractDir = "C:\poppler"

Write-Host "Downloading Poppler..."
Invoke-WebRequest -Uri $popplerUrl -OutFile $zipPath -UseBasicParsing

Write-Host "Extracting Poppler..."
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

# Find the Library\bin directory inside the extracted tree
$binDir = Get-ChildItem -Path $extractDir -Recurse -Directory | Where-Object { $_.Name -eq "bin" } | Select-Object -First 1 -ExpandProperty FullName

if (-not $binDir) {
    Write-Error "Could not locate Poppler bin directory after extraction."
    exit 1
}

Write-Host "Poppler bin at: $binDir"

"POPPLER_DIR=$binDir" | Out-File -Append -Encoding utf8 $env:GITHUB_ENV
