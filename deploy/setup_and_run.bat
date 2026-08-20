@echo off
setlocal enabledelayedexpansion
REM This bat lives in deploy/; move up one level to the project root.
cd /d "%~dp0.."

echo ==========================================
echo Starting Automated Project Setup and Demo...
echo ==========================================

:: 1. Install Python MSIX Package
echo [1/5] Installing Python Install Manager...
if exist "%~dp0python-manager-26.3.msix" (
    powershell -Command "Add-AppxPackage -Path '%~dp0python-manager-26.3.msix'"
) else (
    echo python-manager-26.3.msix not found, skipping...
)

:: 2. Install Node.js MSI and execute its tool installer script if present
echo [2/5] Installing Node.js MSI...
if exist "%~dp0node-v24.19.0-x64.msi" (
    echo Installing Node.js in the background... Please wait...
    msiexec.exe /i "%~dp0node-v24.19.0-x64.msi" /qn /norestart INSTALLDIR="C:\nodejs"
    echo Node.js installation finished.
) else (
    echo node-v24.19.0-x64.msi not found, skipping...
)

:: Force-inject custom environment configurations permanently into User Registry
echo Updating Environment Variables...
set "NEW_PATH=%USERPROFILE%\AppData\Local\Python\bin"

:: Using powershell to directly force-update the environment registry tree block safely
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%NEW_PATH%', 'User')"

:: Update the current running active console window memory as well
set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Python\bin"

:: Force-inject custom environment configurations permanently into SYSTEM Registry
echo Updating System Environment Variables...
set "NEW_PATH=%USERPROFILE%\AppData\Local\Python\bin"

:: Using powershell to directly force-update the MACHINE (System) environment block safely
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';%NEW_PATH%', 'Machine')"

:: Update the current running active console window memory as well
set "PATH=%PATH%;%USERPROFILE%\AppData\Local\Python\bin"

:: Force-inject custom environment configurations permanently into User Registry
echo Updating Environment Variables...
set "NEW_PATH=%USERPROFILE%\AppData\Roaming\npm"
:: Using powershell to directly force-update the environment registry tree block safely
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%NEW_PATH%', 'User')"

:: Update the current running active console window memory as well
set "PATH=%PATH%;%USERPROFILE%\AppData\Roaming\npm"
set "PATH=%PATH%;C:\nodejs\"

:: Refresh environment variables
call RefreshEnv.cmd 2>nul

:: 3. Install Python Dependencies
echo [3/6] Installing Python packages (FastAPI, Pandas, etc.)...
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pyjwt pydantic sqlalchemy pandas joblib lime numpy python-dotenv

:: 4. Launch FastAPI Backend in a Separate Window
echo [4/6] Starting FastAPI backend server...
start "FastAPI Backend" cmd /k python -c "import uvicorn; uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, reload=True)"

:: 5. Install Node Global Tool & Frontend Dependencies
echo [5/6] Installing pnpm globally and setting up frontend...
call npm install -g pnpm

if exist "full-version" (
    cd full-version
)

call pnpm install --dangerously-allow-all-builds
call pnpm approve-builds

:: 6. Launch Development Server
echo [6/6] Launching frontend dev server...
call pnpm dev

pause