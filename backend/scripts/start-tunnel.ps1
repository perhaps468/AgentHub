# Cloudflare Tunnel 启动脚本
# 用于将后端服务暴露到公网，供前端联调使用

$cloudflared = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"

if (-not (Test-Path $cloudflared)) {
    Write-Host "ERROR: cloudflared not found. Please install with:" -ForegroundColor Red
    Write-Host "  winget install Cloudflare.cloudflared" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Cloudflare Tunnel to localhost:8088..." -ForegroundColor Cyan
Write-Host ""

& $cloudflared tunnel --url http://localhost:8088
