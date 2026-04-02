@echo off
setlocal

set "SERVER_URL=%~1"
if "%SERVER_URL%"=="" set "SERVER_URL=http://192.168.1.23:45892/latest"

set "PROJECT_ROOT=%~dp0..\.."

echo CrossPaste Windows client starting...
echo Server URL: %SERVER_URL%
echo Project root: %PROJECT_ROOT%

pushd "%PROJECT_ROOT%"
py -3 -m crosspaste windows-client --server-url "%SERVER_URL%"
popd

