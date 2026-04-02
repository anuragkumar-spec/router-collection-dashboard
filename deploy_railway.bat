@echo off
cd /d "C:\Users\Anurag Kumar\Downloads\ameo\dashboard_app"
set RAILWAY="C:\Users\Anurag Kumar\AppData\Roaming\npm\railway.cmd"

echo.
echo =============================================
echo   Railway Deploy - Connect Rate Dashboard
echo =============================================
echo.
echo Step 1: Login (browserless - follow instructions below)
echo.
%RAILWAY% login --browserless
if errorlevel 1 goto :error

echo.
echo Step 2: Creating Railway project...
%RAILWAY% init --name "router-collection-dashboard"
if errorlevel 1 goto :error

echo.
echo Step 3: Deploying...
%RAILWAY% up --detach
if errorlevel 1 goto :error

echo.
echo Step 4: Getting your public URL...
%RAILWAY% domain
echo.
%RAILWAY% status

echo.
echo =============================================
echo   SUCCESS!
echo =============================================
pause
exit /b 0

:error
echo.
echo ERROR - see above message.
pause
exit /b 1
