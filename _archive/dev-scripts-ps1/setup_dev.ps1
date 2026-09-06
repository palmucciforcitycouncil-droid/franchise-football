# Development Environment Setup
# Sets up the correct working directory and environment for development

# Load project configuration
. "$PSScriptRoot\project_config.ps1"

Write-Host "🚀 Setting up Franchise Football development environment..." -ForegroundColor Green

# Ensure we're in the correct directory
Set-Location $PROJECT_ROOT
Write-Host "📁 Working directory: $(Get-Location)" -ForegroundColor Cyan

# Set environment variables
$env:USE_PBP_V2 = "false"
$env:HFA_POINTS = "1.4"
$env:LEAGUE_SEED = "101"

Write-Host "🔧 Environment variables set:" -ForegroundColor Cyan
Write-Host "   USE_PBP_V2 = $env:USE_PBP_V2" -ForegroundColor White
Write-Host "   HFA_POINTS = $env:HFA_POINTS" -ForegroundColor White
Write-Host "   LEAGUE_SEED = $env:LEAGUE_SEED" -ForegroundColor White

# Check if Python is available
try {
    $pythonVersion = py --version
    Write-Host "✅ Python available: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "   Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
}

# Check if required modules exist
$requiredFiles = @("app/main.py", "app/routers/sim.py", "app/core/config.py")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
    }
}

Write-Host "`n🎯 Quick Commands:" -ForegroundColor Yellow
Write-Host "   .\server.ps1 start          # Start server in background" -ForegroundColor White
Write-Host "   .\server.ps1 status        # Check server status" -ForegroundColor White
Write-Host "   .\server.ps1 stop          # Stop server" -ForegroundColor White
Write-Host "   .\server.ps1 restart       # Restart server" -ForegroundColor White

Write-Host "`n✅ Development environment ready!" -ForegroundColor Green
