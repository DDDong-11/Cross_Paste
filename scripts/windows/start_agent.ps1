param(
    [Parameter(Mandatory = $false)]
    [string]$Mode = "auto",

    [Parameter(Mandatory = $false)]
    [string]$PeerUrl = "",

    [Parameter(Mandatory = $false)]
    [int]$Port = 45892
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "CrossPaste Windows agent starting..."
Write-Host "Mode: $Mode"
Write-Host "Project root: $ProjectRoot"
Write-Host "Local port: $Port"

Set-Location $ProjectRoot

if ($Mode -eq "auto") {
    Write-Host "Auto-discovery: enabled"
    py -3 -m crosspaste windows-agent --auto-discover --port $Port
}
elseif ($PeerUrl -ne "") {
    Write-Host "Peer URL: $PeerUrl"
    py -3 -m crosspaste windows-agent --peer-url $PeerUrl --port $Port
}
else {
    Write-Host "Error: specify -PeerUrl or use -Mode auto"
    exit 1
}

