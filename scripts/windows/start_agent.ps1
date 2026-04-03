param(
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

if ($PeerUrl -ne "") {
    Write-Host "Peer URL: $PeerUrl"
    py -3 -m crosspaste windows-agent --peer-url $PeerUrl --port $Port
}
else {
    Write-Host "Auto-discovery mode (may not work across subnets)..."
    py -3 -m crosspaste windows-agent --auto-discover --port $Port
}
