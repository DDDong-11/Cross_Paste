param(
    [Parameter(Mandatory = $false)]
    [string]$Mode = "",

    [Parameter(Mandatory = $false)]
    [string]$PeerUrl = "",

    [Parameter(Mandatory = $false)]
    [int]$Port = 45892
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "CrossPaste Windows agent starting..."
Write-Host "Project root: $ProjectRoot"
Write-Host "Local port: $Port"

Set-Location $ProjectRoot

if ($Mode -eq "auto") {
    Write-Host "Auto-discovery mode..."
    py -3 -m crosspaste windows-agent --auto-discover --port $Port
}
elseif ($Mode -eq "set") {
    Write-Host "Setting peer URL: $PeerUrl"
    $configPath = Join-Path $ProjectRoot "peers.json"
    @{peer_url = $PeerUrl} | ConvertTo-Json | Set-Content $configPath
    Write-Host "Saved peer URL to peers.json"
    exit 0
}
elseif ($PeerUrl -ne "") {
    Write-Host "Peer URL: $PeerUrl"
    py -3 -m crosspaste windows-agent --peer-url $PeerUrl --port $Port
}
elseif ($Mode -like "http*") {
    Write-Host "Peer URL: $Mode"
    py -3 -m crosspaste windows-agent --peer-url $Mode --port $Port
}
else {
    $configPath = Join-Path $ProjectRoot "peers.json"
    $peerUrl = ""
    if (Test-Path $configPath) {
        $config = Get-Content $configPath | ConvertFrom-Json
        $peerUrl = $config.peer_url
    }
    if ($peerUrl -ne "") {
        Write-Host "Using peer URL from peers.json: $peerUrl"
        py -3 -m crosspaste windows-agent --peer-url $peerUrl --port $Port
    }
    else {
        Write-Host "No peer configured. Set one with:"
        Write-Host "  .\scripts\windows\start_agent.ps1 -Mode set -PeerUrl http://<peer-ip>:45892/latest"
        Write-Host "Or use auto-discovery (same subnet only):"
        Write-Host "  .\scripts\windows\start_agent.ps1 -Mode auto"
        exit 1
    }
}
