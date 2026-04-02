param(
    [Parameter(Mandatory = $false)]
    [string]$ServerUrl = "http://192.168.1.23:45892/latest"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "CrossPaste Windows client starting..."
Write-Host "Server URL: $ServerUrl"
Write-Host "Project root: $ProjectRoot"

Set-Location $ProjectRoot
py -3 -m crosspaste windows-client --server-url $ServerUrl

