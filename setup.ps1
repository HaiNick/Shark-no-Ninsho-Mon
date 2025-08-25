# Setup script for Tailscale Funnel + OAuth2-Proxy + Flask
# PowerShell version for Windows

Write-Host "🦈 Shark-no-Ninsho-Mon Setup Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Generating cookie secret..." -ForegroundColor Yellow
try {
    $cookieSecret = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
    Write-Host "Generated cookie secret: $cookieSecret" -ForegroundColor Green
    Write-Host ""
    Write-Host "Update your .env file with this secret:" -ForegroundColor Yellow
    Write-Host "OAUTH2_PROXY_COOKIE_SECRET=$cookieSecret" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "⚠️  Cannot generate cookie secret automatically." -ForegroundColor Red
    Write-Host "   Please run: [System.Web.Security.Membership]::GeneratePassword(32,0)" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "2. Setup Checklist:" -ForegroundColor Yellow
Write-Host "===================" -ForegroundColor Yellow
Write-Host ""
Write-Host "□ Configure Google OAuth2 client in Google Cloud Console" -ForegroundColor White
Write-Host "  - Set redirect URI: https://<your-host>.<your-tailnet>.ts.net/oauth2/callback" -ForegroundColor Gray
Write-Host ""
Write-Host "□ Update .env with your Google OAuth credentials:" -ForegroundColor White
Write-Host "  - OAUTH2_PROXY_CLIENT_ID" -ForegroundColor Gray
Write-Host "  - OAUTH2_PROXY_CLIENT_SECRET" -ForegroundColor Gray
Write-Host "  - FUNNEL_HOST (your full https:// URL)" -ForegroundColor Gray
Write-Host "  - FUNNEL_HOSTNAME (your hostname without https://)" -ForegroundColor Gray
Write-Host ""
Write-Host "□ Update emails.txt with allowed email addresses" -ForegroundColor White
Write-Host ""
Write-Host "□ Build and start containers:" -ForegroundColor White
Write-Host "  docker compose up -d --build" -ForegroundColor Gray
Write-Host ""
Write-Host "□ Start Tailscale Funnel:" -ForegroundColor White
Write-Host "  tailscale funnel 4180" -ForegroundColor Gray
Write-Host ""
Write-Host "□ Test access at your public URL" -ForegroundColor White
Write-Host ""
Write-Host "📖 See README.md for detailed instructions!" -ForegroundColor Cyan
