@echo off
setlocal

set "SOURCE=%~dp0"
set "TARGET=%TEMP%\marathon_assistant_frontend"

echo [1/3] Preparing ASCII runtime directory:
echo       %TARGET%

node "%SOURCE%tools\copy-ascii-runtime.mjs" "%SOURCE%." "%TARGET%"
if errorlevel 1 exit /b %ERRORLEVEL%

pushd "%TARGET%"

echo [2/3] Checking dependencies...
if exist ".deps-required" (
  echo Dependencies changed or missing. Running npm install...
  call npm.cmd install --cache ".\.npm-cache"
  if errorlevel 1 exit /b %ERRORLEVEL%
  move /Y ".deps-required" ".deps.hash" >nul
) else (
  echo Dependencies are cached. Skipping npm install.
)

echo [3/3] Starting Astro on http://127.0.0.1:4321
call npm.cmd run dev -- --host 127.0.0.1 --port 4321

popd
