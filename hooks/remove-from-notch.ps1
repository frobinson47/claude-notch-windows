# Remove-from-Notch Command
# Unpins all sessions from the Windows Notch display

# Build unpin payload
$payload = @{
    timestamp = Get-Date -Format "o"
}

$json = $payload | ConvertTo-Json -Compress

# Send to server
try {
    $uri = "http://localhost:27182/unpin"
    Invoke-RestMethod -Uri $uri -Method Post -Body $json -ContentType "application/json" -TimeoutSec 1 | Out-Null
    Write-Host "All sessions unpinned from Notch display"
} catch {
    Write-Host "Error: Notch app not running"
}

exit 0
