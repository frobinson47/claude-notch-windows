# Test script to send a sample event to the Notch app

Write-Host "Testing Claude Code Notch for Windows..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check
Write-Host "1. Testing server health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:27182/health" -Method Get
    Write-Host "   ✓ Server is running: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Server not responding!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Send a Read event
Write-Host "2. Sending 'Read' tool event..." -ForegroundColor Yellow
$payload = @{
    eventType = "PreToolUse"
    sessionId = "test-session-123"
    cwd = "C:\TestProject"
    tool = "Read"
    toolInput = @{
        file_path = "test.txt"
    }
    timestamp = Get-Date -Format "o"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json"
    Write-Host "   ✓ Event sent successfully!" -ForegroundColor Green
    Write-Host "   → Check your system tray - icon should be CYAN (reading)" -ForegroundColor Cyan
} catch {
    Write-Host "   ✗ Failed to send event: $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 3

# Test 3: Send a Write event
Write-Host ""
Write-Host "3. Sending 'Write' tool event..." -ForegroundColor Yellow
$payload = @{
    eventType = "PreToolUse"
    sessionId = "test-session-123"
    cwd = "C:\TestProject"
    tool = "Write"
    toolInput = @{
        file_path = "output.txt"
    }
    timestamp = Get-Date -Format "o"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json"
    Write-Host "   ✓ Event sent successfully!" -ForegroundColor Green
    Write-Host "   → Check your system tray - icon should be GREEN (writing)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed to send event: $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 3

# Test 4: Send a Bash event
Write-Host ""
Write-Host "4. Sending 'Bash' tool event..." -ForegroundColor Yellow
$payload = @{
    eventType = "PreToolUse"
    sessionId = "test-session-123"
    cwd = "C:\TestProject"
    tool = "Bash"
    toolInput = @{
        command = "dir"
    }
    timestamp = Get-Date -Format "o"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json"
    Write-Host "   ✓ Event sent successfully!" -ForegroundColor Green
    Write-Host "   → Check your system tray - icon should be RED (executing)" -ForegroundColor Red
} catch {
    Write-Host "   ✗ Failed to send event: $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 3

# Test 5: Send Stop event (back to idle)
Write-Host ""
Write-Host "5. Sending 'Stop' event (returning to idle)..." -ForegroundColor Yellow
$payload = @{
    eventType = "Stop"
    sessionId = "test-session-123"
    cwd = "C:\TestProject"
    timestamp = Get-Date -Format "o"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json"
    Write-Host "   ✓ Event sent successfully!" -ForegroundColor Green
    Write-Host "   → Check your system tray - icon should be GRAY (idle)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Failed to send event: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "What to check:" -ForegroundColor Yellow
Write-Host "  1. System tray icon changed colors during the test"
Write-Host "  2. Tooltip shows tool names when you hover"
Write-Host "  3. Double-click the tray icon to see the overlay window"
Write-Host "  4. The overlay shows the test session with animations"
Write-Host ""
Write-Host "If you saw color changes, it's working!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
