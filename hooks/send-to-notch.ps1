# Send-to-Notch Command
# Pins the current session to the Windows Notch display

param(
    [Parameter(ValueFromPipeline=$true)]
    [string]$InputData
)

# Read from stdin if not provided
if (-not $InputData) {
    $InputData = $input | Out-String
}

# Parse JSON input
try {
    $hookData = $InputData | ConvertFrom-Json
} catch {
    exit 0
}

# Build pin payload (Claude Code uses snake_case field names)
$payload = @{
    sessionId = $hookData.session_id
    cwd = $hookData.cwd
    timestamp = Get-Date -Format "o"
}

$json = $payload | ConvertTo-Json -Compress

# Send to server
try {
    $uri = "http://localhost:27182/pin"
    Invoke-RestMethod -Uri $uri -Method Post -Body $json -ContentType "application/json" -TimeoutSec 1 | Out-Null
    Write-Host "Session pinned to Notch display"
} catch {
    Write-Host "Error: Notch app not running"
}

exit 0
