param(
    [Parameter(Mandatory = $false)]
    [string]$PeerUrl = "http://192.168.1.23:45892/latest",

    [Parameter(Mandatory = $false)]
    [int]$Port = 45892
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "CrossPaste Windows agent starting..."
Write-Host "Peer URL: $PeerUrl"
Write-Host "Project root: $ProjectRoot"
Write-Host "Local port: $Port"

Set-Location $ProjectRoot
py -3 -m crosspaste windows-agent --peer-url $PeerUrl --port $Port

