# Interactive Setup Script for Tailscale Funnel + OAuth2-Proxy + Flask
# PowerShell version for Windows

# DracWrite-Host ""
Write-Host "${DracOrange}STEP 3: Configure Environment${Reset}"
Write-Host "${DracOrange}============================${Reset}"
Write-Host ""Color Definitions
$DracRed = "`e[38;2;255;85;85m"      # #ff5555
$DracGreen = "`e[38;2;80;250;123m"   # #50fa7b
$DracYellow = "`e[38;2;241;250;140m" # #f1fa8c
$DracCyan = "`e[38;2;139;233;253m"   # #8be9fd
$DracPurple = "`e[38;2;189;147;249m" # #bd93f9
$DracOrange = "`e[38;2;255;184;108m" # #ffb86c
$DracPink = "`e[38;2;255;121;198m"   # #ff79c6
$Reset = "`e[0m"

# ASCII Art Header
Write-Host ""
Write-Host "${DracPurple}    _____ __               __      ${Reset}"
Write-Host "${DracPurple}   / ___// /_  ____ ______/ /__    ${Reset}"
Write-Host "${DracPurple}   \__ \/ __ \/ __ \/ ___/ //_/    ${Reset}"
Write-Host "${DracPurple}  ___/ / / / / /_/ / /  / ,<       ${Reset}"
Write-Host "${DracPurple} /____/_/ /_/\__,_/_/  /_/|_|      ${Reset}"
Write-Host "${DracPurple}                                   ${Reset}"
Write-Host "${DracCyan} Shark-no-Ninsho-Mon Setup Script ${Reset}"
Write-Host "${DracCyan} ================================= ${Reset}"
Write-Host ""

# Function to prompt for user input with validation
function Get-UserInput {
    param(
        [string]$Prompt,
        [string]$DefaultValue = "",
        [bool]$Required = $true,
        [bool]$Secret = $false
    )
    
    do {
        if ($DefaultValue -ne "") {
            $displayPrompt = "$Prompt [$DefaultValue]" + ": "
        } else {
            $displayPrompt = "$Prompt" + ": "
        }
        
        if ($Secret) {
            $input = Read-Host -Prompt $displayPrompt -AsSecureString
            $input = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($input))
        } else {
            $input = Read-Host -Prompt $displayPrompt
        }
        
        if ($input -eq "" -and $DefaultValue -ne "") {
            return $DefaultValue
        }
        
        if ($Required -and $input -eq "") {
            Write-Host "${DracRed}This field is required. Please enter a value.${Reset}"
        }
    } while ($Required -and $input -eq "")
    
    return $input
}

# Function to test if a command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

Write-Host "${DracOrange}STEP 1: Prerequisites Check${Reset}"
Write-Host "${DracOrange}===========================${Reset}"
Write-Host ""

# Check Docker
if (Test-Command "docker") {
    Write-Host "[OK] Docker is installed" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check Tailscale
if (Test-Command "tailscale") {
    Write-Host "[OK] Tailscale is installed" -ForegroundColor Green
    $tailscaleStatus = tailscale status 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Tailscale is running and authenticated" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Tailscale may not be authenticated" -ForegroundColor Yellow
        Write-Host "Please run: tailscale login" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ERROR] Tailscale is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Tailscale from https://tailscale.com/download" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "${DracOrange}STEP 2: Generate Secrets${Reset}"
Write-Host "${DracOrange}========================${Reset}"
Write-Host ""

Write-Host "Checking for Python..." -ForegroundColor Cyan
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $testPython = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            Write-Host "Found Python: $cmd" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

if ($pythonCmd) {
    Write-Host ""
    Write-Host "Do you want to use the automated secret generator? (Recommended)" -ForegroundColor Yellow
    $useGenerator = Get-UserInput -Prompt "Use generate-secrets.py? (y/n)" -DefaultValue "y" -Required $false
    
    if ($useGenerator -eq "y" -or $useGenerator -eq "yes" -or $useGenerator -eq "") {
        Write-Host ""
        Write-Host "Running secret generator..." -ForegroundColor Cyan
        & $pythonCmd generate-secrets.py
        
        if (Test-Path ".env") {
            Write-Host ""
            Write-Host "Secrets have been generated and saved to .env!" -ForegroundColor Green
            Write-Host "Continuing with additional configuration..." -ForegroundColor Cyan
            Write-Host ""
            
            # Read the generated secrets
            $cookieSecret = Get-ExistingEnvValue "OAUTH2_PROXY_COOKIE_SECRET"
            $flaskSecret = Get-ExistingEnvValue "SECRET_KEY"
        }
    } else {
        # Manual secret generation fallback
        try {
            $cookieSecret = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
            Write-Host "Generated cookie secret: $cookieSecret" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Cannot generate cookie secret automatically." -ForegroundColor Red
            Write-Host "Please enter a 32-byte base64 cookie secret:" -ForegroundColor Yellow
            $cookieSecret = Get-UserInput -Prompt "Cookie secret (base64)" -Required $true
        }
    }
} else {
    Write-Host "[WARNING] Python not found. Using manual secret generation." -ForegroundColor Yellow
    Write-Host "For better security, install Python and run: python generate-secrets.py" -ForegroundColor Yellow
    Write-Host ""
    
    # Manual fallback
    try {
        $cookieSecret = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
        Write-Host "Generated cookie secret: $cookieSecret" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Cannot generate cookie secret automatically." -ForegroundColor Red
        Write-Host "Please enter a 32-byte base64 cookie secret:" -ForegroundColor Yellow
        $cookieSecret = Get-UserInput -Prompt "Cookie secret (base64)" -Required $true
    }
}

Write-Host ""
Write-Host "STEP 3: Configure Environment" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Please provide your Google OAuth2 credentials."
Write-Host "Get these from: https://console.cloud.google.com/apis/credentials"
Write-Host ""

$clientId = Get-UserInput -Prompt "Google OAuth2 Client ID" -Required $true
$clientSecret = Get-UserInput -Prompt "Google OAuth2 Client Secret" -Required $true -Secret $true

Write-Host ""
Write-Host "Please provide your Tailscale Funnel configuration."
Write-Host "Example: sharky.snowy-burbot.ts.net"
Write-Host ""

do {
    $hostname = Get-UserInput -Prompt "Your Tailscale hostname (full domain)" -Required $true
    
    # Validate that it's a proper .ts.net domain
    if ($hostname -match "^[^.]+\.[^.]+\.ts\.net$") {
        break
    } else {
        Write-Host "Please provide the full hostname format: hostname.tailnet.ts.net" -ForegroundColor Red
    }
} while ($true)
$funnelHost = "https://$hostname"
$funnelHostname = $hostname

Write-Host ""
Write-Host "STEP 4: Create Environment File" -ForegroundColor Yellow
Write-Host "===============================" -ForegroundColor Yellow
Write-Host ""

# Function to read existing value from .env file
function Get-ExistingEnvValue {
    param([string]$Key)
    if (Test-Path ".env") {
        $content = Get-Content ".env" -ErrorAction SilentlyContinue
        $line = $content | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
        if ($line) {
            return $line.Split('=', 2)[1]
        }
    }
    return $null
}

# Read existing values
$existingClientId = Get-ExistingEnvValue "OAUTH2_PROXY_CLIENT_ID"
$existingClientSecret = Get-ExistingEnvValue "OAUTH2_PROXY_CLIENT_SECRET"
$existingCookieSecret = Get-ExistingEnvValue "OAUTH2_PROXY_COOKIE_SECRET"
$existingFunnelHost = Get-ExistingEnvValue "FUNNEL_HOST"
$existingFunnelHostname = Get-ExistingEnvValue "FUNNEL_HOSTNAME"

Write-Host "Creating environment configuration..." -ForegroundColor Green
Write-Host ""

# Prompt for each value with existing values as defaults
if ($existingClientId) {
    Write-Host "Current OAuth2 Client ID: $existingClientId" -ForegroundColor Cyan
    $finalClientId = Get-UserInput -Prompt "Keep this OAuth2 Client ID or enter new one" -DefaultValue $existingClientId -Required $true
} else {
    $finalClientId = $clientId
}

if ($existingClientSecret) {
    Write-Host "Current OAuth2 Client Secret: [HIDDEN]" -ForegroundColor Cyan
    $useExistingSecret = Get-UserInput -Prompt "Keep existing OAuth2 Client Secret? (y/n)" -DefaultValue "y" -Required $false
    if ($useExistingSecret -eq "y" -or $useExistingSecret -eq "yes") {
        $finalClientSecret = $existingClientSecret
    } else {
        $finalClientSecret = $clientSecret
    }
} else {
    $finalClientSecret = $clientSecret
}

if ($existingCookieSecret) {
    Write-Host "Current Cookie Secret: [HIDDEN]" -ForegroundColor Cyan
    $useExistingCookie = Get-UserInput -Prompt "Keep existing Cookie Secret? (y/n)" -DefaultValue "y" -Required $false
    if ($useExistingCookie -eq "y" -or $useExistingCookie -eq "yes") {
        $finalCookieSecret = $existingCookieSecret
    } else {
        $finalCookieSecret = $cookieSecret
    }
} else {
    $finalCookieSecret = $cookieSecret
}

if ($existingFunnelHost) {
    Write-Host "Current Funnel Host: $existingFunnelHost" -ForegroundColor Cyan
    $finalFunnelHost = Get-UserInput -Prompt "Keep this Funnel Host or enter new one" -DefaultValue $existingFunnelHost -Required $true
    # Extract hostname from the host URL
    $finalFunnelHostname = $finalFunnelHost -replace '^https?://', ''
} else {
    $finalFunnelHost = $funnelHost
    $finalFunnelHostname = $funnelHostname
}

# Ask about development mode
Write-Host ""
Write-Host "Do you want to enable Development Mode?" -ForegroundColor Yellow
Write-Host "  - Development Mode: Bypasses OAuth2 (for local testing)" -ForegroundColor Cyan
Write-Host "  - Production Mode: Full OAuth2 authentication (for deployment)" -ForegroundColor Cyan
$devMode = Get-UserInput -Prompt "Enable Development Mode? (y/n)" -DefaultValue "n" -Required $false

$devModeValue = if ($devMode -eq "y" -or $devMode -eq "yes") { "true" } else { "false" }
$flaskEnv = if ($devModeValue -eq "true") { "development" } else { "production" }
$debugMode = if ($devModeValue -eq "true") { "true" } else { "false" }

# Write .env file with clean formatting
$envLines = @(
    "# Generated by setup script on $(Get-Date)",
    "# DO NOT commit this file to version control!",
    "",
    "# ============================================================================",
    "# Google OAuth2 Client Credentials",
    "# ============================================================================",
    "OAUTH2_PROXY_CLIENT_ID=$finalClientId",
    "OAUTH2_PROXY_CLIENT_SECRET=$finalClientSecret",
    "",
    "# ============================================================================",
    "# Cookie Secret (32 random bytes, base64 encoded)",
    "# ============================================================================",
    "OAUTH2_PROXY_COOKIE_SECRET=$finalCookieSecret",
    "",
    "# ============================================================================",
    "# Tailscale Funnel Configuration",
    "# ============================================================================",
    "FUNNEL_HOST=$finalFunnelHost",
    "FUNNEL_HOSTNAME=$finalFunnelHostname",
    "",
    "# ============================================================================",
    "# Application Configuration",
    "# ============================================================================",
    "FLASK_ENV=$flaskEnv",
    "DEV_MODE=$devModeValue",
    "DEBUG=$debugMode",
    "",
    "# Server configuration",
    "PORT=8000",
    "HOST=0.0.0.0"
)

# Add Flask SECRET_KEY if it was generated
if ($flaskSecret) {
    $envLines += ""
    $envLines += "# Flask Secret Key"
    $envLines += "SECRET_KEY=$flaskSecret"
}

$envLines | Out-File -FilePath ".env" -Encoding UTF8

# Verify the .env file was created correctly
if (Test-Path ".env") {
    Write-Host "[OK] Created .env file" -ForegroundColor Green
    
    # Check each required field and prompt for missing ones
    $envContent = Get-Content ".env"
    $needsUpdate = $false
    
    if (-not ($envContent | Where-Object { $_ -match "^OAUTH2_PROXY_CLIENT_ID=" })) {
        Write-Host "Missing OAUTH2_PROXY_CLIENT_ID" -ForegroundColor Yellow
        $finalClientId = Get-UserInput -Prompt "Please enter Google OAuth2 Client ID" -Required $true
        $needsUpdate = $true
    }
    
    if (-not ($envContent | Where-Object { $_ -match "^OAUTH2_PROXY_CLIENT_SECRET=" })) {
        Write-Host "Missing OAUTH2_PROXY_CLIENT_SECRET" -ForegroundColor Yellow
        $finalClientSecret = Get-UserInput -Prompt "Please enter Google OAuth2 Client Secret" -Required $true -Secret $true
        $needsUpdate = $true
    }
    
    if (-not ($envContent | Where-Object { $_ -match "^OAUTH2_PROXY_COOKIE_SECRET=" })) {
        Write-Host "Missing OAUTH2_PROXY_COOKIE_SECRET" -ForegroundColor Yellow
        try {
            $finalCookieSecret = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
            Write-Host "Generated new cookie secret" -ForegroundColor Green
        } catch {
            Write-Host "Please enter a 32-byte base64 cookie secret:" -ForegroundColor Yellow
            $finalCookieSecret = Get-UserInput -Prompt "Cookie secret (base64)" -Required $true
        }
        $needsUpdate = $true
    }
    
    if (-not ($envContent | Where-Object { $_ -match "^FUNNEL_HOST=" })) {
        Write-Host "Missing FUNNEL_HOST" -ForegroundColor Yellow
        $finalFunnelHost = Get-UserInput -Prompt "Please enter Funnel Host (e.g., https://sharky.snowy-burbot.ts.net)" -Required $true
        $needsUpdate = $true
    }
    
    if (-not ($envContent | Where-Object { $_ -match "^FUNNEL_HOSTNAME=" })) {
        Write-Host "Missing FUNNEL_HOSTNAME" -ForegroundColor Yellow
        if ($finalFunnelHost) {
            $finalFunnelHostname = $finalFunnelHost -replace '^https?://', ''
            Write-Host "Extracted hostname from Funnel Host: $finalFunnelHostname" -ForegroundColor Green
        } else {
            $finalFunnelHostname = Get-UserInput -Prompt "Please enter Funnel Hostname (e.g., sharky.snowy-burrot.ts.net)" -Required $true
        }
        $needsUpdate = $true
    }
    
    # Recreate .env file if any fields were missing
    if ($needsUpdate) {
        Write-Host "Updating .env file with missing fields..." -ForegroundColor Yellow
        
        # Read existing values for fields that weren't missing
        if (-not $finalClientId) { $finalClientId = Get-ExistingEnvValue "OAUTH2_PROXY_CLIENT_ID" }
        if (-not $finalClientSecret) { $finalClientSecret = Get-ExistingEnvValue "OAUTH2_PROXY_CLIENT_SECRET" }
        if (-not $finalCookieSecret) { $finalCookieSecret = Get-ExistingEnvValue "OAUTH2_PROXY_COOKIE_SECRET" }
        if (-not $finalFunnelHost) { $finalFunnelHost = Get-ExistingEnvValue "FUNNEL_HOST" }
        if (-not $finalFunnelHostname) { $finalFunnelHostname = Get-ExistingEnvValue "FUNNEL_HOSTNAME" }
        
        # Recreate the .env file with all values
        $envLines = @(
            "# Generated by setup script on $(Get-Date)",
            "# DO NOT commit this file to version control!",
            "",
            "# Google OAuth2 Client Credentials",
            "OAUTH2_PROXY_CLIENT_ID=$finalClientId",
            "OAUTH2_PROXY_CLIENT_SECRET=$finalClientSecret",
            "",
            "# Cookie Secret (32 random bytes, base64 encoded)",
            "OAUTH2_PROXY_COOKIE_SECRET=$finalCookieSecret",
            "",
            "# Tailscale Funnel Configuration",
            "FUNNEL_HOST=$finalFunnelHost",
            "FUNNEL_HOSTNAME=$finalFunnelHostname"
        )
        
        $envLines | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "[OK] Updated .env file with all required fields" -ForegroundColor Green
        
        # Update variables for later use
        $funnelHost = $finalFunnelHost
        $funnelHostname = $finalFunnelHostname
    } else {
        Write-Host "[OK] All required fields are present in .env file" -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] Failed to create .env file" -ForegroundColor Red
    exit 1
}

# Update variables for later use
$funnelHost = $finalFunnelHost
$funnelHostname = $finalFunnelHostname

Write-Host ""
Write-Host "STEP 5: Configure Authorized Emails" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "Current emails.txt content:"
$currentEmails = @()
if (Test-Path "emails.txt") {
    Get-Content "emails.txt" | ForEach-Object {
        # Skip comments and empty lines
        if ($_ -notmatch "^\s*#" -and $_ -ne "" -and $_ -notmatch "^\s*$") {
            $currentEmails += $_.Trim()
            Write-Host "  - $_" -ForegroundColor Cyan
        }
    }
    
    if ($currentEmails.Count -eq 0) {
        Write-Host "  (no emails configured)" -ForegroundColor Gray
    }
} else {
    Write-Host "  (file does not exist)" -ForegroundColor Gray
}

Write-Host ""
$configureEmails = Get-UserInput -Prompt "Do you want to configure authorized emails? (y/n)" -DefaultValue "y" -Required $false

if ($configureEmails -eq "y" -or $configureEmails -eq "yes") {
    # Ask if user wants to keep existing emails
    if ($currentEmails.Count -gt 0) {
        Write-Host ""
        Write-Host "You have $($currentEmails.Count) existing email(s) configured."
        $keepExisting = Get-UserInput -Prompt "Do you want to keep the existing emails and add more? (y/n)" -DefaultValue "y" -Required $false
        
        if ($keepExisting -eq "y" -or $keepExisting -eq "yes") {
            $emails = $currentEmails.Clone()
            Write-Host "Keeping existing emails" -ForegroundColor Green
        } else {
            $emails = @()
            Write-Host "Starting with a clean email list" -ForegroundColor Yellow
        }
    } else {
        $emails = @()
    }
    
    Write-Host ""
    Write-Host "Enter email addresses to add (one per line, empty line to finish):"
    
    do {
        $email = Get-UserInput -Prompt "Email" -Required $false
        if ($email -ne "") {
            if ($email -match "^[^@]+@[^@]+\.[^@]+$") {
                # Check if email already exists
                if ($emails -contains $email) {
                    Write-Host "Email already exists, skipping: $email" -ForegroundColor Yellow
                } else {
                    $emails += $email
                    Write-Host "Added: $email" -ForegroundColor Green
                }
            } else {
                Write-Host "Invalid email format, skipping: $email" -ForegroundColor Yellow
            }
        }
    } while ($email -ne "")
    
    if ($emails.Count -gt 0) {
        $emailContent = @"
# Authorized emails for Shark Authentication
# Generated by setup script on $(Get-Date)
# Add one email per line
# Lines starting with # are comments

$($emails -join "`n")
"@
        $emailContent | Out-File -FilePath "emails.txt" -Encoding UTF8
        Write-Host "[OK] Updated emails.txt with $($emails.Count) email(s)" -ForegroundColor Green
    } else {
        Write-Host "No emails configured. You may need to add emails later." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "STEP 6: Google Cloud Console Configuration" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "IMPORTANT: Configure your Google OAuth2 client with this redirect URI:"
Write-Host "$funnelHost/oauth2/callback" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Go to: https://console.cloud.google.com/apis/credentials"
Write-Host "2. Select your OAuth2 client ID"
Write-Host "3. Add the redirect URI above to 'Authorized redirect URIs'"
Write-Host "4. Save the configuration"
Write-Host ""

$continueSetup = Get-UserInput -Prompt "Have you configured the redirect URI? (y/n)" -Required $true

if ($continueSetup -ne "y" -and $continueSetup -ne "yes") {
    Write-Host ""
    Write-Host "Please complete the Google Cloud Console configuration and run this script again." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "STEP 7: Build and Deploy" -ForegroundColor Yellow
Write-Host "========================" -ForegroundColor Yellow
Write-Host ""

$deploy = Get-UserInput -Prompt "Build and start the containers now? (y/n)" -DefaultValue "y" -Required $false

if ($deploy -eq "y" -or $deploy -eq "yes") {
    Write-Host "Building and starting containers..." -ForegroundColor Green
    
    # Try docker compose first
    docker compose up -d --build
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Containers started successfully" -ForegroundColor Green
    } else {
        Write-Host "Docker compose failed, trying with elevated privileges..." -ForegroundColor Yellow
        Write-Host "You may see a UAC prompt - please click Yes to allow elevated access" -ForegroundColor Yellow
        
        try {
            # Try to run with elevated privileges
            $process = Start-Process -FilePath "docker" -ArgumentList "compose", "up", "-d", "--build" -Verb RunAs -Wait -PassThru
            if ($process.ExitCode -eq 0) {
                Write-Host "[OK] Containers started successfully with elevated privileges" -ForegroundColor Green
                Write-Host "Note: Docker required elevated privileges" -ForegroundColor Yellow
            } else {
                Write-Host "[ERROR] Failed to start containers even with elevated privileges" -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "[ERROR] Failed to start containers with elevated privileges" -ForegroundColor Red
            Write-Host "Please try running this script as Administrator" -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host ""
Write-Host "STEP 8: Start Tailscale Funnel" -ForegroundColor Yellow
Write-Host "==============================" -ForegroundColor Yellow
Write-Host ""

$startFunnel = Get-UserInput -Prompt "Start Tailscale Funnel now? (y/n)" -DefaultValue "y" -Required $false

if ($startFunnel -eq "y" -or $startFunnel -eq "yes") {
    Write-Host "Starting Tailscale Funnel on port 4180..." -ForegroundColor Green
    Write-Host "Note: This will run in the background. Use Ctrl+C to stop." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Your app will be available at: $funnelHost" -ForegroundColor Cyan
    Write-Host ""
    
    # Try tailscale funnel first
    $funnelProcess = Start-Process -FilePath "tailscale" -ArgumentList "funnel", "4180" -PassThru -NoNewWindow
    Start-Sleep -Seconds 2
    
    # Check if the process is still running (indicates success)
    if (-not $funnelProcess.HasExited) {
        Write-Host "Tailscale Funnel started successfully" -ForegroundColor Green
        Wait-Process -InputObject $funnelProcess
    } else {
        Write-Host "Tailscale Funnel failed, trying with elevated privileges..." -ForegroundColor Yellow
        Write-Host "You may see a UAC prompt - please click Yes to allow elevated access" -ForegroundColor Yellow
        
        try {
            Start-Process -FilePath "tailscale" -ArgumentList "funnel", "4180" -Verb RunAs -Wait
        } catch {
            Write-Host "[ERROR] Failed to start Tailscale Funnel even with elevated privileges" -ForegroundColor Red
            Write-Host "Please try running 'tailscale set --operator=$env:USERNAME' as Administrator first" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host ""
    Write-Host "To start Tailscale Funnel manually, run:" -ForegroundColor Yellow
    Write-Host "tailscale funnel 4180" -ForegroundColor White
    Write-Host "If that fails, try running as Administrator" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Your app will be available at: $funnelHost" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "${DracPurple}Setup Complete!${Reset}"
Write-Host "${DracPurple}===============${Reset}"
Write-Host ""
Write-Host "${DracGreen}Your secure web app is ready!${Reset}"
Write-Host "${DracCyan}Access URL: ${DracPink}$funnelHost${Reset}"
Write-Host ""
Write-Host "Troubleshooting:"
Write-Host "- Check container logs: docker compose logs"
Write-Host "- Restart services: docker compose restart"
Write-Host "- View Tailscale status: tailscale status"
Write-Host "- Start funnel manually: tailscale funnel 4180 (try as Administrator if it fails)"
Write-Host "- Set operator permissions: tailscale set --operator=$env:USERNAME (as Administrator)"
Write-Host ""
