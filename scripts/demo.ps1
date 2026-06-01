$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$demoPath = (Resolve-Path "demo-app").Path
foreach ($generatedName in @("keel-out", "graphify-out")) {
  $generated = Join-Path $demoPath $generatedName
  if (Test-Path $generated) {
    Remove-Item -LiteralPath $generated -Recurse -Force
  }
}

if (-not $env:GEMINI_API_KEY -and (Test-Path ".env")) {
  $line = Get-Content ".env" | Where-Object { $_ -match "^GEMINI_API_KEY=" } | Select-Object -First 1
  if ($line) {
    $env:GEMINI_API_KEY = $line.Split("=", 2)[1].Trim()
  }
}

graphify demo-app --backend gemini
graphify cluster-only (Resolve-Path "demo-app").Path --backend gemini
keel discover demo-app --write
keel approve ui_never_touches_database demo-app
keel check demo-app --html
keel export demo-app --format json
