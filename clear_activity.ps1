# Clear current activity (send Stop event)

$payload = @{
    eventType = "Stop"
    sessionId = "test-session-123"
    cwd = "C:\TestProject"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json" | Out-Null

Write-Host "Activity cleared. Icon should return to gray (idle)." -ForegroundColor Green
