@echo off
setlocal

set "PEER_URL=%~1"
if "%PEER_URL%"=="" set "PEER_URL=http://192.168.1.23:45892/latest"

set "PORT=%~2"
if "%PORT%"=="" set "PORT=45892"

set "PROJECT_ROOT=%~dp0..\.."

echo CrossPaste Windows agent starting...
echo Peer URL: %PEER_URL%
echo Local port: %PORT%
echo Project root: %PROJECT_ROOT%

pushd "%PROJECT_ROOT%"
py -3 -m crosspaste windows-agent --peer-url "%PEER_URL%" --port "%PORT%"
popd

