$ProjectPath = "C:\Users\chatgpt-bridge"

Write-Host ""
Write-Host "========================================"
Write-Host "     STARTING CHATGPT LOCAL BRIDGE"
Write-Host "========================================"
Write-Host ""

Set-Location $ProjectPath

# Clear communication files
Set-Content "$ProjectPath\input.txt" ""
Set-Content "$ProjectPath\output.txt" ""

Write-Host "[1/2] Starting bridge2.py..."

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectPath'; .\venv\Scripts\python.exe bridge2.py"
)

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting FastAPI server..."

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectPath'; .\venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000"
)

Write-Host ""
Write-Host "Waiting for API..."

Start-Sleep -Seconds 5

try {
    $response = Invoke-WebRequest "http://127.0.0.1:8000/health" -TimeoutSec 10

    Write-Host ""
    Write-Host "========================================"
    Write-Host "          API IS READY! 🚀"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "URL: http://127.0.0.1:8000"
    Write-Host "end-point: http://127.0.0.1:8000/v1/chat/completions"
}
catch {
    Write-Host ""
    Write-Host "⚠ Server started, but health check failed."
    Write-Host "Check the server window."
}
