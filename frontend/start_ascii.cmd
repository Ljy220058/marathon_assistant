@echo off
setlocal

set "SOURCE=%~dp0"
set "TARGET=%TEMP%\marathon_assistant_frontend"

echo [1/3] Preparing ASCII runtime directory:
echo       %TARGET%

node "%SOURCE%tools\copy-ascii-runtime.mjs" "%SOURCE%." "%TARGET%"
if errorlevel 1 exit /b %ERRORLEVEL%

pushd "%TARGET%"

echo [2/3] Installing dependencies when needed...
if not exist "node_modules" (
  call npm.cmd install --cache ".\.npm-cache"
  if errorlevel 1 exit /b %ERRORLEVEL%
)

echo [3/3] Starting Astro on http://127.0.0.1:4321
call npm.cmd run dev -- --host 127.0.0.1 --port 4321

popd
