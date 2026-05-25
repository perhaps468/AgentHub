@echo off
chcp 65001 >nul
title AgentHub Tunnel

echo ========================================
echo   AgentHub Cloudflare Tunnel
echo ========================================
echo.

for %%i in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe") do set CLOUDFLARED=%%~fi

if not exist "%CLOUDFLARED%" (
    echo [ERROR] cloudflared not found!
    echo Please install with:
    echo   winget install Cloudflare.cloudflared
    echo.
    pause
    exit /b 1
)

echo Starting tunnel to localhost:8088...
echo This window must stay open while debugging.
echo.
"%CLOUDFLARED%" tunnel --url http://localhost:8088
