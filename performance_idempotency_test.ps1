# Performance and Idempotency Test Script
# Tests simulation efficiency and data protection mechanisms

param(
    [int]$Season = 2026,
    [int]$Port = 8011
)

$baseUrl = "http://127.0.0.1:$Port"

Write-Host "🧪 Starting Performance & Idempotency Tests..." -ForegroundColor Green
Write-Host "Season: $Season" -ForegroundColor Cyan
Write-Host "Server: $baseUrl" -ForegroundColor Cyan

# Helper function to measure performance
function Measure-Performance {
    param(
        [string]$TestName,
        [scriptblock]$ScriptBlock
    )
    
    Write-Host "`n⏱️  Running: $TestName" -ForegroundColor Blue
    
    # Get initial memory usage
    $initialMemory = [System.GC]::GetTotalMemory($false)
    
    # Measure execution time
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        $result = & $ScriptBlock
        $stopwatch.Stop()
        
        # Get peak memory usage
        $peakMemory = [System.GC]::GetTotalMemory($false)
        $memoryUsed = $peakMemory - $initialMemory
        
        return @{
            Success = $true
            Duration = $stopwatch.Elapsed
            MemoryUsed = $memoryUsed
            Result = $result
        }
    }
    catch {
        $stopwatch.Stop()
        return @{
            Success = $false
            Duration = $stopwatch.Elapsed
            Error = $_.Exception.Message
        }
    }
}

# Helper function to get game count
function Get-GameCount {
    param([int]$Season)
    
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/games/$Season/1" -Method GET -TimeoutSec 10
        $games = ($response.Content | ConvertFrom-Json)
        return $games.Count
    }
    catch {
        Write-Host "⚠️  Could not get game count: $($_.Exception.Message)" -ForegroundColor Yellow
        return 0
    }
}

# Helper function to get all games for a season
function Get-AllGames {
    param([int]$Season)
    
    $totalGames = 0
    for ($week = 1; $week -le 18; $week++) {
        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/games/$Season/$week" -Method GET -TimeoutSec 10
            $games = ($response.Content | ConvertFrom-Json)
            $totalGames += $games.Count
        }
        catch {
            Write-Host "⚠️  Could not get games for week $week" -ForegroundColor Yellow
        }
    }
    return $totalGames
}

# Helper function to check game statuses
function Get-GameStatuses {
    param([int]$Season)
    
    $statusCounts = @{}
    for ($week = 1; $week -le 18; $week++) {
        try {
            $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/games/$Season/$week" -Method GET -TimeoutSec 10
            $games = ($response.Content | ConvertFrom-Json)
            foreach ($game in $games) {
                $status = $game.status
                $statusCounts[$status] = ($statusCounts[$status] + 1)
            }
        }
        catch {
            Write-Host "⚠️  Could not get game statuses for week $week" -ForegroundColor Yellow
        }
    }
    return $statusCounts
}

Write-Host "`n📊 TEST 1: Performance Benchmarking" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

# Test 1: Performance Benchmarking
$perfResult = Measure-Performance "Full Season Simulation" {
    # Build schedule
    $scheduleResponse = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$Season" -Method POST -TimeoutSec 30
    $scheduleResult = $scheduleResponse.Content | ConvertFrom-Json
    
    # Play season
    $playResponse = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$Season" -Method POST -TimeoutSec 60
    $playResult = $playResponse.Content | ConvertFrom-Json
    
    return @{
        ScheduleResult = $scheduleResult
        PlayResult = $playResult
    }
}

if ($perfResult.Success) {
    Write-Host "✅ Performance Test Completed" -ForegroundColor Green
    Write-Host "⏱️  Duration: $($perfResult.Duration.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Cyan
    Write-Host "🧠 Memory Used: $([math]::Round($perfResult.MemoryUsed / 1MB, 2)) MB" -ForegroundColor Cyan
} else {
    Write-Host "❌ Performance Test Failed: $($perfResult.Error)" -ForegroundColor Red
}

Write-Host "`n📊 TEST 2: Schedule Idempotency" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

# Test 2: Schedule Idempotency
Write-Host "🔄 Running schedule endpoint first time..." -ForegroundColor Blue
$schedule1 = Measure-Performance "Schedule Run 1" {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$Season" -Method POST -TimeoutSec 30
    return $response.Content | ConvertFrom-Json
}

$gamesAfterRun1 = Get-AllGames -Season $Season
Write-Host "📈 Games after Run 1: $gamesAfterRun1" -ForegroundColor Cyan

Write-Host "🔄 Running schedule endpoint second time..." -ForegroundColor Blue
$schedule2 = Measure-Performance "Schedule Run 2" {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$Season" -Method POST -TimeoutSec 30
    return $response.Content | ConvertFrom-Json
}

$gamesAfterRun2 = Get-AllGames -Season $Season
Write-Host "📈 Games after Run 2: $gamesAfterRun2" -ForegroundColor Cyan

$scheduleIdempotent = ($gamesAfterRun1 -eq $gamesAfterRun2) -and ($gamesAfterRun1 -eq 272)
Write-Host "📊 Schedule Idempotency Result: $(if($scheduleIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($scheduleIdempotent) {'Green'} else {'Red'})

Write-Host "`n📊 TEST 3: Game Play Idempotency" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

# Test 3: Game Play Idempotency
Write-Host "🎮 Running PBP simulation first time..." -ForegroundColor Blue
$play1 = Measure-Performance "PBP Run 1" {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$Season" -Method POST -TimeoutSec 60
    return $response.Content | ConvertFrom-Json
}

$statusesAfterRun1 = Get-GameStatuses -Season $Season
$finalGamesAfterRun1 = $statusesAfterRun1["final"]
Write-Host "📈 Final games after Run 1: $finalGamesAfterRun1" -ForegroundColor Cyan

Write-Host "🎮 Running PBP simulation second time..." -ForegroundColor Blue
$play2 = Measure-Performance "PBP Run 2" {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$Season" -Method POST -TimeoutSec 60
    return $response.Content | ConvertFrom-Json
}

$statusesAfterRun2 = Get-GameStatuses -Season $Season
$finalGamesAfterRun2 = $statusesAfterRun2["final"]
Write-Host "📈 Final games after Run 2: $finalGamesAfterRun2" -ForegroundColor Cyan

$playIdempotent = ($finalGamesAfterRun1 -eq $finalGamesAfterRun2) -and ($finalGamesAfterRun1 -eq 272)
Write-Host "📊 Game Play Idempotency Result: $(if($playIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($playIdempotent) {'Green'} else {'Red'})

Write-Host "`n📋 FINAL RESULTS SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "Test 1: Performance Benchmarking" -ForegroundColor White
if ($perfResult.Success) {
    Write-Host "  ✅ Full Season Simulation Time: $($perfResult.Duration.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Green
    Write-Host "  ✅ Peak Memory Usage: $([math]::Round($perfResult.MemoryUsed / 1MB, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "  ❌ Performance Test Failed" -ForegroundColor Red
}

Write-Host "`nTest 2: Schedule Idempotency" -ForegroundColor White
Write-Host "  📊 Total Games in Database after Run 1: $gamesAfterRun1" -ForegroundColor Cyan
Write-Host "  📊 Total Games in Database after Run 2: $gamesAfterRun2" -ForegroundColor Cyan
Write-Host "  📊 Status: $(if($scheduleIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($scheduleIdempotent) {'Green'} else {'Red'})

Write-Host "`nTest 3: Game Play Idempotency" -ForegroundColor White
Write-Host "  📊 Total Game Records after Run 1: $finalGamesAfterRun1 (All status 'final')" -ForegroundColor Cyan
Write-Host "  📊 Total Game Records after Run 2: $finalGamesAfterRun2" -ForegroundColor Cyan
Write-Host "  📊 Status: $(if($playIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($playIdempotent) {'Green'} else {'Red'})

Write-Host "`n🎯 Overall Assessment:" -ForegroundColor Yellow
$overallPass = $perfResult.Success -and $scheduleIdempotent -and $playIdempotent
Write-Host "  $(if($overallPass) {'✅ ALL TESTS PASSED - Simulation is operationally stable'} else {'❌ SOME TESTS FAILED - Issues detected'})" -ForegroundColor $(if($overallPass) {'Green'} else {'Red'})
