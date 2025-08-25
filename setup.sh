#!/bin/bash
# Setup script for Tailscale Funnel + OAuth2-Proxy + Flask

echo "🦈 Shark-no-Ninsho-Mon Setup Script"
echo "====================================="
echo ""

echo "1. Generating cookie secret..."
if command -v openssl &> /dev/null; then
    COOKIE_SECRET=$(openssl rand -base64 32)
    echo "Generated cookie secret: $COOKIE_SECRET"
    echo ""
    echo "Update your .env file with this secret:"
    echo "OAUTH2_PROXY_COOKIE_SECRET=$COOKIE_SECRET"
    echo ""
elif command -v head &> /dev/null && [ -e /dev/urandom ]; then
    COOKIE_SECRET=$(head -c 32 /dev/urandom | base64)
    echo "Generated cookie secret: $COOKIE_SECRET"
    echo ""
    echo "Update your .env file with this secret:"
    echo "OAUTH2_PROXY_COOKIE_SECRET=$COOKIE_SECRET"
    echo ""
else
    echo "⚠️  Cannot generate cookie secret automatically."
    echo "   Please run: head -c 32 /dev/urandom | base64"
    echo "   Or on Windows: [System.Web.Security.Membership]::GeneratePassword(32,0)"
fi

echo "2. Setup Checklist:"
echo "==================="
echo ""
echo "□ Configure Google OAuth2 client in Google Cloud Console"
echo "  - Set redirect URI: https://<your-host>.<your-tailnet>.ts.net/oauth2/callback"
echo ""
echo "□ Update .env with your Google OAuth credentials:"
echo "  - OAUTH2_PROXY_CLIENT_ID"
echo "  - OAUTH2_PROXY_CLIENT_SECRET"
echo "  - FUNNEL_HOST (your full https:// URL)"
echo "  - FUNNEL_HOSTNAME (your hostname without https://)"
echo ""
echo "□ Update emails.txt with allowed email addresses"
echo ""
echo "□ Build and start containers:"
echo "  docker compose up -d --build"
echo ""
echo "□ Start Tailscale Funnel:"
echo "  tailscale funnel 4180"
echo ""
echo "□ Test access at your public URL"
echo ""
echo "📖 See README.md for detailed instructions!"
