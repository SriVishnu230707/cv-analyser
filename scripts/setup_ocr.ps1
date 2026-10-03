# Downloads English language data only; PyMuPDF supplies the local OCR engine.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$modelDirectory = Join-Path $projectRoot '.tools/tessdata'
$modelPath = Join-Path $modelDirectory 'eng.traineddata'
$expectedHash = '7D4322BD2A7749724879683FC3912CB542F19906C83BCC1A52132556427170B2'
New-Item -ItemType Directory -Force -Path $modelDirectory | Out-Null
if (-not (Test-Path -LiteralPath $modelPath)) {
    Invoke-WebRequest 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata' -OutFile $modelPath
}
$actualHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) {
    throw 'OCR data checksum differs from the validated model. Review the upstream model before updating this script.'
}
Write-Output "English OCR data ready: $modelPath"
