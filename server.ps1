# FastAPI Server Management Script
param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start",
    [switch]$Background = $true,
    [int]$Port = 8015
)

# Load project configuration
. "$PSScriptRoot\project_config.ps1"

function Test-ServerRunning {
    param([int]$Port)
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -Method GET -TimeoutSec 5
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Start-Server {
    param([int]$Port, [bool]$Background)
    Set-Location $PROJECT_ROOT
    
    if (Test-ServerRunning -Port $Port) {
        Write-Host "Server already running on port $Port" -ForegroundColor Yellow
        return
    }
    
    Write-Host "Starting server on port $Port..." -ForegroundColor Green
    
    if ($Background) {
        $processArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $Port.ToString())
        Start-Process -FilePath "py" -ArgumentList $processArgs -WindowStyle Hidden
        Start-Sleep -Seconds 3
        
        if (Test-ServerRunning -Port $Port) {
            Write-Host "âœ… Server started successfully" -ForegroundColor Green
        } else {
            Write-Host "âŒ Failed to start server" -ForegroundColor Red
        }
    } else {
        py -m uvicorn app.main:app --host 127.0.0.1 --port $Port
    }
}

function Stop-Server {
    param([int]$Port)
    Write-Host "Stopping server on port $Port..."
    Get-Process | Where-Object { 
        $_.ProcessName -eq "python" -and 
        $_.CommandLine -like "*uvicorn*" -and 
        $_.CommandLine -like "*$Port*" 
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

function Show-ServerStatus {
    param([int]$Port)
    Write-Host "Checking server status on port $Port..." -ForegroundColor Blue
    
    if (Test-ServerRunning -Port $Port) {
        Write-Host "âœ… Server is running" -ForegroundColor Green
        Write-Host "ðŸŒ Server URL: http://127.0.0.1:$Port/" -ForegroundColor Cyan
    } else {
        Write-Host "âŒ Server is not running" -ForegroundColor Red
    }
}

# Main execution
switch ($Action) {
    "start" { Start-Server -Port $Port -Background $Background }
    "stop" { Stop-Server -Port $Port; Write-Host "âœ… Server stopped" -ForegroundColor Green }
    "restart" { Stop-Server -Port $Port; Start-Sleep -Seconds 2; Start-Server -Port $Port -Background $Background }
    "status" { Show-ServerStatus -Port $Port }
}
