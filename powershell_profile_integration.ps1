# PowerShell Profile Integration for Franchise Football
# Add this to your PowerShell profile to automatically set up the environment

# Check if we're in the franchise-football project directory
if ($PWD.Path -like "*franchise-football*") {
    # Load project configuration if available
    $configPath = Join-Path $PWD "project_config.ps1"
    if (Test-Path $configPath) {
        . $configPath
        Write-Host "🏈 Franchise Football environment loaded" -ForegroundColor Green
    }
}

# Function to quickly navigate to project root
function Go-FranchiseFootball {
    Set-Location "C:\Users\bpalm\Documents\franchise-football"
    . ".\setup_dev.ps1"
}

# Function to start the server
function Start-FranchiseFootballServer {
    Set-Location "C:\Users\bpalm\Documents\franchise-football"
    . ".\server.ps1" start
}

# Function to check server status
function Test-FranchiseFootballServer {
    Set-Location "C:\Users\bpalm\Documents\franchise-football"
    . ".\server.ps1" status
}

# Note: Export-ModuleMember only works in modules, not regular scripts