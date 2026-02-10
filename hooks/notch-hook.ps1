# Claude Code Notch Hook (PowerShell version)
# Sends hook events to the Windows Notch app via HTTP

param(
    [Parameter(ValueFromPipeline=$true)]
    [string]$InputData
)

# Read from stdin if not provided as parameter
if (-not $InputData) {
    $InputData = $input | Out-String
}

# Also try [Console]::In.ReadToEnd() as fallback
if (-not $InputData -or $InputData.Trim() -eq "") {
    try {
        $InputData = [Console]::In.ReadToEnd()
    } catch {}
}

# Exit early if no data
if (-not $InputData -or $InputData.Trim() -eq "") {
    exit 0
}

# Parse JSON input
try {
    $hookData = $InputData | ConvertFrom-Json
} catch {
    # Invalid JSON, exit silently
    exit 0
}

# Build payload to send to server
# Claude Code uses snake_case field names:
#   session_id, hook_event_name, tool_name, tool_input, tool_output, transcript_path, cwd, permission_mode
$payload = @{
    eventType = $hookData.hook_event_name
    sessionId = $hookData.session_id
    cwd = $hookData.cwd
    tool = $hookData.tool_name
    toolInput = $hookData.tool_input
    toolOutput = $hookData.tool_output
    transcriptPath = $hookData.transcript_path
    permissionMode = $hookData.permission_mode
    timestamp = Get-Date -Format "o"
}

# Convert to JSON
$json = $payload | ConvertTo-Json -Depth 10 -Compress

# Send to local server (use WebClient for speed)
try {
    $webClient = New-Object System.Net.WebClient
    $webClient.Headers["Content-Type"] = "application/json"
    $webClient.UploadString("http://localhost:27182/hook", "POST", $json) | Out-Null
    $webClient.Dispose()
} catch {
    # Silently fail if server not running
}

# Exit successfully
exit 0
