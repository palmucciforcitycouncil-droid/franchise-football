# Test Runner for Franchise Football
# Runs common tests and validations

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("all", "server", "schedule", "simulation", "rng")]
    [string]$TestType = "all"
)

# Load project configuration
. "$PSScriptRoot\project_config.ps1"

# Ensure we're in the correct directory
Set-Location $PROJECT_ROOT

function Test-ServerEndpoints {
    Write-Host "🧪 Testing server endpoints..." -ForegroundColor Blue
    
    $baseUrl = "http://127.0.0.1:$SERVER_PORT"
    
    # Test health endpoint
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/" -Method GET -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Health endpoint working" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "❌ Health endpoint failed" -ForegroundColor Red
        return $false
    }
    
    # Test schedule endpoint
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule/2026" -Method POST -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Schedule endpoint working" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "❌ Schedule endpoint failed" -ForegroundColor Red
        return $false
    }
    
    return $true
}

function Test-ScheduleGeneration {
    Write-Host "🧪 Testing schedule generation..." -ForegroundColor Blue
    
    $baseUrl = "http://127.0.0.1:$SERVER_PORT"
    
    try {
        # Test schedule-all endpoint
        $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/2026" -Method POST -TimeoutSec 15
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            if ($result.games -eq 272) {
                Write-Host "✅ Schedule generation working (272 games)" -ForegroundColor Green
                return $true
            } else {
                Write-Host "❌ Wrong number of games: $($result.games)" -ForegroundColor Red
                return $false
            }
        }
    }
    catch {
        Write-Host "❌ Schedule generation failed" -ForegroundColor Red
        return $false
    }
    
    return $false
}

function Test-SimulationFlow {
    Write-Host "🧪 Testing simulation flow..." -ForegroundColor Blue
    
    $baseUrl = "http://127.0.0.1:$SERVER_PORT"
    
    try {
        # Test play-season endpoint
        $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/2026" -Method POST -TimeoutSec 30
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Season simulation working" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Season simulation failed" -ForegroundColor Red
        return $false
    }
    
    return $false
}

function Test-RNGValidation {
    Write-Host "🧪 Testing RNG validation..." -ForegroundColor Blue
    
    $baseUrl = "http://127.0.0.1:$SERVER_PORT"
    
    try {
        # Test with seed 101
        $env:LEAGUE_SEED = "101"
        $response1 = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/2026" -Method POST -TimeoutSec 30
        
        # Test with seed 202
        $env:LEAGUE_SEED = "202"
        $response2 = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/2026" -Method POST -TimeoutSec 30
        
        if ($response1.StatusCode -eq 200 -and $response2.StatusCode -eq 200) {
            Write-Host "✅ RNG validation working" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ RNG validation failed" -ForegroundColor Red
        return $false
    }
    
    return $false
}

# Main execution
Write-Host "🧪 Running Franchise Football Tests..." -ForegroundColor Green
Write-Host "Test Type: $TestType" -ForegroundColor Cyan

$allPassed = $true

switch ($TestType) {
    "server" {
        $allPassed = Test-ServerEndpoints
    }
    "schedule" {
        $allPassed = Test-ScheduleGeneration
    }
    "simulation" {
        $allPassed = Test-SimulationFlow
    }
    "rng" {
        $allPassed = Test-RNGValidation
    }
    "all" {
        $allPassed = Test-ServerEndpoints -and Test-ScheduleGeneration -and Test-SimulationFlow -and Test-RNGValidation
    }
}

if ($allPassed) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Some tests failed!" -ForegroundColor Red
}
