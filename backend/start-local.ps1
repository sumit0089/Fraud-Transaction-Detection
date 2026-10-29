# Run from any directory. Only known chat settings are loaded from ignored .env.
$safePayRoot = Split-Path $PSScriptRoot -Parent
$safePayEnvPath = Join-Path $safePayRoot '.env'
if (Test-Path -LiteralPath $safePayEnvPath) {
    foreach ($safePayLine in Get-Content -LiteralPath $safePayEnvPath) {
        if ($safePayLine -match '^\s*(GROQ_API_KEY|GROQ_MODEL|CHAT_DAILY_LIMIT)\s*=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
        }
    }
}
Push-Location $safePayRoot
try {
    & (Join-Path $safePayRoot '.venv\Scripts\python.exe') -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
} finally {
    Pop-Location
}
