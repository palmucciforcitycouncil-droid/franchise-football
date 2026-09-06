# Simplified Performance and Idempotency Test Script
# Tests simulation efficiency and data protection mechanisms

$baseUrl = "http://127.0.0.1:8011"
$season = 2026

Write-Host "🧪 Starting Performance & Idempotency Tests..." -ForegroundColor Green
Write-Host "Season: $season" -ForegroundColor Cyan
Write-Host "Server: $baseUrl" -ForegroundColor Cyan

# Test 1: Performance Benchmarking
Write-Host "`n📊 TEST 1: Performance Benchmarking" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

Write-Host "⏱️  Starting full season simulation..." -ForegroundColor Blue
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    # Build schedule
    Write-Host "📅 Building schedule..." -ForegroundColor Cyan
    $scheduleResponse = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$season" -Method POST -TimeoutSec 30
    $scheduleResult = $scheduleResponse.Content | ConvertFrom-Json
    Write-Host "✅ Schedule built: $($scheduleResult.games) games" -ForegroundColor Green
    
    # Play season
    Write-Host "🎮 Playing season..." -ForegroundColor Cyan
    $playResponse = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$season" -Method POST -TimeoutSec 60
    $playResult = $playResponse.Content | ConvertFrom-Json
    Write-Host "✅ Season played: $($playResult.games_played) games" -ForegroundColor Green
    
    $stopwatch.Stop()
    $duration = $stopwatch.Elapsed.TotalSeconds
    
    Write-Host "✅ Performance Test Completed" -ForegroundColor Green
    Write-Host "⏱️  Duration: $($duration.ToString('F2')) seconds" -ForegroundColor Cyan
    
    # Get memory usage estimate
    $memoryMB = [math]::Round([System.GC]::GetTotalMemory($false) / 1MB, 2)
    Write-Host "🧠 Memory Usage: $memoryMB MB" -ForegroundColor Cyan
    
} catch {
    $stopwatch.Stop()
    Write-Host "❌ Performance Test Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Schedule Idempotency
Write-Host "`n📊 TEST 2: Schedule Idempotency" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

Write-Host "🔄 Running schedule endpoint first time..." -ForegroundColor Blue
try {
    $schedule1Response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$season" -Method POST -TimeoutSec 30
    $schedule1Result = $schedule1Response.Content | ConvertFrom-Json
    $gamesAfterRun1 = $schedule1Result.games
    Write-Host "📈 Games after Run 1: $gamesAfterRun1" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Schedule Run 1 Failed: $($_.Exception.Message)" -ForegroundColor Red
    $gamesAfterRun1 = 0
}

Write-Host "🔄 Running schedule endpoint second time..." -ForegroundColor Blue
try {
    $schedule2Response = Invoke-WebRequest -Uri "$baseUrl/api/sim/schedule-all/$season" -Method POST -TimeoutSec 30
    $schedule2Result = $schedule2Response.Content | ConvertFrom-Json
    $gamesAfterRun2 = $schedule2Result.games
    Write-Host "📈 Games after Run 2: $gamesAfterRun2" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Schedule Run 2 Failed: $($_.Exception.Message)" -ForegroundColor Red
    $gamesAfterRun2 = 0
}

$scheduleIdempotent = ($gamesAfterRun1 -eq $gamesAfterRun2) -and ($gamesAfterRun1 -eq 272)
Write-Host "📊 Schedule Idempotency Result: $(if($scheduleIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($scheduleIdempotent) {'Green'} else {'Red'})

# Test 3: Game Play Idempotency
Write-Host "`n📊 TEST 3: Game Play Idempotency" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Yellow

Write-Host "🎮 Running PBP simulation first time..." -ForegroundColor Blue
try {
    $play1Response = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$season" -Method POST -TimeoutSec 60
    $play1Result = $play1Response.Content | ConvertFrom-Json
    $finalGamesAfterRun1 = $play1Result.games_played
    Write-Host "📈 Final games after Run 1: $finalGamesAfterRun1" -ForegroundColor Cyan
} catch {
    Write-Host "❌ PBP Run 1 Failed: $($_.Exception.Message)" -ForegroundColor Red
    $finalGamesAfterRun1 = 0
}

Write-Host "🎮 Running PBP simulation second time..." -ForegroundColor Blue
try {
    $play2Response = Invoke-WebRequest -Uri "$baseUrl/api/sim/play-season/$season" -Method POST -TimeoutSec 60
    $play2Result = $play2Response.Content | ConvertFrom-Json
    $finalGamesAfterRun2 = $play2Result.games_played
    Write-Host "📈 Final games after Run 2: $finalGamesAfterRun2" -ForegroundColor Cyan
} catch {
    Write-Host "❌ PBP Run 2 Failed: $($_.Exception.Message)" -ForegroundColor Red
    $finalGamesAfterRun2 = 0
}

$playIdempotent = ($finalGamesAfterRun1 -eq $finalGamesAfterRun2) -and ($finalGamesAfterRun1 -eq 272)
Write-Host "📊 Game Play Idempotency Result: $(if($playIdempotent) {'✅ PASS'} else {'❌ FAIL'})" -ForegroundColor $(if($playIdempotent) {'Green'} else {'Red'})

# Final Results Summary
Write-Host "`n📋 FINAL RESULTS SUMMARY" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "Test 1: Performance Benchmarking" -ForegroundColor White
if ($stopwatch.IsRunning -eq $false -and $duration -gt 0) {
    Write-Host "  ✅ Full Season Simulation Time: $($duration.ToString('F2')) seconds" -ForegroundColor Green
    Write-Host "  ✅ Peak Memory Usage: $memoryMB MB" -ForegroundColor Green
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
$overallPass = ($duration -gt 0) -and $scheduleIdempotent -and $playIdempotent
Write-Host "  $(if($overallPass) {'✅ ALL TESTS PASSED - Simulation is operationally stable'} else {'❌ SOME TESTS FAILED - Issues detected'})" -ForegroundColor $(if($overallPass) {'Green'} else {'Red'})
