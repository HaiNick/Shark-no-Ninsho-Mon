#!/bin/bash
# Interactive Setup Script for Tailscale Funnel + OAuth2-Proxy + Flask

# ASCII Art Header
echo ""
echo "    _____ __               __      "
echo "   / ___// /_  ____ ______/ /__    "
echo "   \__ \/ __ \/ __ \/ ___/ //_/    "
echo "  ___/ / / / / /_/ / /  / ,<       "
echo " /____/_/ /_/\__,_/_/  /_/|_|      "
echo "                                   "
echo " Shark-no-Ninsho-Mon Setup Script "
echo " ================================= "
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to prompt for user input with validation
get_user_input() {
    local prompt="$1"
    local default_value="$2"
    local required="$3"
    local secret="$4"
    local input=""
    
    while true; do
        if [ -n "$default_value" ]; then
            display_prompt="$prompt [$default_value]: "
        else
            display_prompt="$prompt: "
        fi
        
        if [ "$secret" = "true" ]; then
            read -r -s -p "$display_prompt" input
            echo "" # New line after hidden input
        else
            read -r -p "$display_prompt" input
        fi
        
        if [ -z "$input" ] && [ -n "$default_value" ]; then
            input="$default_value"
            break
        fi
        
        if [ "$required" = "true" ] && [ -z "$input" ]; then
            echo -e "${RED}This field is required. Please enter a value.${NC}"
        else
            break
        fi
    done
    
    echo "$input"
}

# Function to test if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${YELLOW}STEP 1: Prerequisites Check${NC}"
echo -e "${YELLOW}===========================${NC}"
echo ""

# Check Docker
if command_exists docker; then
    echo -e "${GREEN}[OK] Docker is installed${NC}"
else
    echo -e "${RED}[ERROR] Docker is not installed or not in PATH${NC}"
    echo -e "${YELLOW}Please install Docker from https://docker.com/get-docker${NC}"
    exit 1
fi

# Check Docker Compose
if command_exists docker && docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}[OK] Docker Compose is available${NC}"
elif command_exists docker-compose; then
    echo -e "${GREEN}[OK] Docker Compose is available (legacy)${NC}"
else
    echo -e "${RED}[ERROR] Docker Compose is not available${NC}"
    echo -e "${YELLOW}Please install Docker Compose${NC}"
    exit 1
fi

# Check Tailscale
if command_exists tailscale; then
    echo -e "${GREEN}[OK] Tailscale is installed${NC}"
    if tailscale status >/dev/null 2>&1; then
        echo -e "${GREEN}[OK] Tailscale is running and authenticated${NC}"
    else
        echo -e "${YELLOW}[WARNING] Tailscale may not be authenticated${NC}"
        echo -e "${YELLOW}Please run: tailscale login${NC}"
    fi
else
    echo -e "${RED}[ERROR] Tailscale is not installed or not in PATH${NC}"
    echo -e "${YELLOW}Please install Tailscale from https://tailscale.com/download${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}STEP 2: Generate Cookie Secret${NC}"
echo -e "${YELLOW}==============================${NC}"
echo ""

if command_exists openssl; then
    cookie_secret=$(openssl rand -base64 32)
    echo -e "${GREEN}Generated secure cookie secret: $cookie_secret${NC}"
elif [ -r /dev/urandom ] && command_exists base64; then
    cookie_secret=$(head -c 32 /dev/urandom | base64)
    echo -e "${GREEN}Generated secure cookie secret: $cookie_secret${NC}"
else
    echo -e "${RED}[ERROR] Cannot generate cookie secret automatically.${NC}"
    echo -e "${YELLOW}Please enter a 32-byte base64 cookie secret:${NC}"
    cookie_secret=$(get_user_input "Cookie secret (base64)" "" "true" "false")
fi

echo ""
echo -e "${YELLOW}STEP 3: Configure Environment${NC}"
echo -e "${YELLOW}============================${NC}"
echo ""

echo "Please provide your Google OAuth2 credentials."
echo "Get these from: https://console.cloud.google.com/apis/credentials"
echo ""

client_id=$(get_user_input "Google OAuth2 Client ID" "" "true" "false")
# Remove any newlines or carriage returns from client_id
client_id=$(echo "$client_id" | tr -d '\r\n')

client_secret=$(get_user_input "Google OAuth2 Client Secret" "" "true" "true")
# Remove any newlines or carriage returns from client_secret
client_secret=$(echo "$client_secret" | tr -d '\r\n')

echo ""
echo "Please provide your Tailscale Funnel configuration."
echo "Example: sharky.snowy-burbot.ts.net"
echo ""

while true; do
    hostname=$(get_user_input "Your Tailscale hostname (full domain)" "" "true" "false")
    
    # Validate that it's a proper .ts.net domain
    if [[ $hostname =~ ^[^.]+\.[^.]+\.ts\.net$ ]]; then
        break
    else
        echo -e "${RED}Please provide the full hostname format: hostname.tailnet.ts.net${NC}"
    fi
done
funnel_host="https://$hostname"
funnel_hostname="$hostname"

echo ""
echo -e "${YELLOW}STEP 4: Create Environment File${NC}"
echo -e "${YELLOW}==============================${NC}"
echo ""

# Function to read existing value from .env file
get_existing_env_value() {
    local key="$1"
    if [ -f ".env" ]; then
        grep "^${key}=" .env 2>/dev/null | cut -d'=' -f2- | head -n1
    fi
}

# Read existing values
existing_client_id=$(get_existing_env_value "OAUTH2_PROXY_CLIENT_ID")
existing_client_secret=$(get_existing_env_value "OAUTH2_PROXY_CLIENT_SECRET")
existing_cookie_secret=$(get_existing_env_value "OAUTH2_PROXY_COOKIE_SECRET")
existing_funnel_host=$(get_existing_env_value "FUNNEL_HOST")
existing_funnel_hostname=$(get_existing_env_value "FUNNEL_HOSTNAME")

echo "Creating environment configuration..."
echo ""

# Prompt for each value with existing values as defaults
if [ -n "$existing_client_id" ]; then
    echo "Current OAuth2 Client ID: $existing_client_id"
    final_client_id=$(get_user_input "Keep this OAuth2 Client ID or enter new one" "$existing_client_id" "true" "false")
else
    final_client_id="$client_id"
fi

if [ -n "$existing_client_secret" ]; then
    echo "Current OAuth2 Client Secret: [HIDDEN]"
    use_existing_secret=$(get_user_input "Keep existing OAuth2 Client Secret? (y/n)" "y" "false" "false")
    if [[ "$use_existing_secret" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        final_client_secret="$existing_client_secret"
    else
        final_client_secret="$client_secret"
    fi
else
    final_client_secret="$client_secret"
fi

if [ -n "$existing_cookie_secret" ]; then
    echo "Current Cookie Secret: [HIDDEN]"
    use_existing_cookie=$(get_user_input "Keep existing Cookie Secret? (y/n)" "y" "false" "false")
    if [[ "$use_existing_cookie" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        final_cookie_secret="$existing_cookie_secret"
    else
        final_cookie_secret="$cookie_secret"
    fi
else
    final_cookie_secret="$cookie_secret"
fi

if [ -n "$existing_funnel_host" ]; then
    echo "Current Funnel Host: $existing_funnel_host"
    final_funnel_host=$(get_user_input "Keep this Funnel Host or enter new one" "$existing_funnel_host" "true" "false")
    # Extract hostname from the host URL
    final_funnel_hostname=$(echo "$final_funnel_host" | sed 's|https\?://||')
else
    final_funnel_host="$funnel_host"
    final_funnel_hostname="$funnel_hostname"
fi

# Write .env file with clean formatting
{
    echo "# Generated by setup script on $(date)"
    echo "# DO NOT commit this file to version control!"
    echo ""
    echo "# Google OAuth2 Client Credentials"
    echo "OAUTH2_PROXY_CLIENT_ID=$final_client_id"
    echo "OAUTH2_PROXY_CLIENT_SECRET=$final_client_secret"
    echo ""
    echo "# Cookie Secret (32 random bytes, base64 encoded)"
    echo "OAUTH2_PROXY_COOKIE_SECRET=$final_cookie_secret"
    echo ""
    echo "# Tailscale Funnel Configuration"
    echo "FUNNEL_HOST=$final_funnel_host"
    echo "FUNNEL_HOSTNAME=$final_funnel_hostname"
} > .env

# Update variables for later use
funnel_host="$final_funnel_host"
funnel_hostname="$final_funnel_hostname"

# Verify the .env file was created correctly
if [ -f ".env" ]; then
    echo -e "${GREEN}[OK] Created .env file${NC}"
    
    # Check each required field and prompt for missing ones
    needs_update=false
    
    if ! grep -q "^OAUTH2_PROXY_CLIENT_ID=" .env; then
        echo -e "${YELLOW}Missing OAUTH2_PROXY_CLIENT_ID${NC}"
        final_client_id=$(get_user_input "Please enter Google OAuth2 Client ID" "" "true" "false")
        needs_update=true
    fi
    
    if ! grep -q "^OAUTH2_PROXY_CLIENT_SECRET=" .env; then
        echo -e "${YELLOW}Missing OAUTH2_PROXY_CLIENT_SECRET${NC}"
        final_client_secret=$(get_user_input "Please enter Google OAuth2 Client Secret" "" "true" "true")
        needs_update=true
    fi
    
    if ! grep -q "^OAUTH2_PROXY_COOKIE_SECRET=" .env; then
        echo -e "${YELLOW}Missing OAUTH2_PROXY_COOKIE_SECRET${NC}"
        if command_exists openssl; then
            final_cookie_secret=$(openssl rand -base64 32)
            echo -e "${GREEN}Generated new cookie secret${NC}"
        elif [ -r /dev/urandom ] && command_exists base64; then
            final_cookie_secret=$(head -c 32 /dev/urandom | base64)
            echo -e "${GREEN}Generated new cookie secret${NC}"
        else
            final_cookie_secret=$(get_user_input "Please enter a 32-byte base64 cookie secret" "" "true" "false")
        fi
        needs_update=true
    fi
    
    if ! grep -q "^FUNNEL_HOST=" .env; then
        echo -e "${YELLOW}Missing FUNNEL_HOST${NC}"
        final_funnel_host=$(get_user_input "Please enter Funnel Host (e.g., https://sharky.snowy-burbot.ts.net)" "" "true" "false")
        needs_update=true
    fi
    
    if ! grep -q "^FUNNEL_HOSTNAME=" .env; then
        echo -e "${YELLOW}Missing FUNNEL_HOSTNAME${NC}"
        if [ -n "$final_funnel_host" ]; then
            final_funnel_hostname=$(echo "$final_funnel_host" | sed 's|https\?://||')
            echo -e "${GREEN}Extracted hostname from Funnel Host: $final_funnel_hostname${NC}"
        else
            final_funnel_hostname=$(get_user_input "Please enter Funnel Hostname (e.g., sharky.snowy-burbot.ts.net)" "" "true" "false")
        fi
        needs_update=true
    fi
    
    # Recreate .env file if any fields were missing
    if [ "$needs_update" = true ]; then
        echo -e "${YELLOW}Updating .env file with missing fields...${NC}"
        
        # Read existing values for fields that weren't missing
        [ -z "$final_client_id" ] && final_client_id=$(get_existing_env_value "OAUTH2_PROXY_CLIENT_ID")
        [ -z "$final_client_secret" ] && final_client_secret=$(get_existing_env_value "OAUTH2_PROXY_CLIENT_SECRET")
        [ -z "$final_cookie_secret" ] && final_cookie_secret=$(get_existing_env_value "OAUTH2_PROXY_COOKIE_SECRET")
        [ -z "$final_funnel_host" ] && final_funnel_host=$(get_existing_env_value "FUNNEL_HOST")
        [ -z "$final_funnel_hostname" ] && final_funnel_hostname=$(get_existing_env_value "FUNNEL_HOSTNAME")
        
        # Recreate the .env file with all values
        {
            echo "# Generated by setup script on $(date)"
            echo "# DO NOT commit this file to version control!"
            echo ""
            echo "# Google OAuth2 Client Credentials"
            echo "OAUTH2_PROXY_CLIENT_ID=$final_client_id"
            echo "OAUTH2_PROXY_CLIENT_SECRET=$final_client_secret"
            echo ""
            echo "# Cookie Secret (32 random bytes, base64 encoded)"
            echo "OAUTH2_PROXY_COOKIE_SECRET=$final_cookie_secret"
            echo ""
            echo "# Tailscale Funnel Configuration"
            echo "FUNNEL_HOST=$final_funnel_host"
            echo "FUNNEL_HOSTNAME=$final_funnel_hostname"
        } > .env
        
        echo -e "${GREEN}[OK] Updated .env file with all required fields${NC}"
        
        # Update variables for later use
        funnel_host="$final_funnel_host"
        funnel_hostname="$final_funnel_hostname"
    else
        echo -e "${GREEN}[OK] All required fields are present in .env file${NC}"
    fi
else
    echo -e "${RED}[ERROR] Failed to create .env file${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}STEP 5: Configure Authorized Emails${NC}"
echo -e "${YELLOW}====================================${NC}"
echo ""

echo "Current emails.txt content:"
if [ -f "emails.txt" ]; then
    current_emails=()
    while IFS= read -r email; do
        # Skip comments and empty lines
        if [[ ! "$email" =~ ^[[:space:]]*# ]] && [[ -n "$email" ]] && [[ ! "$email" =~ ^[[:space:]]*$ ]]; then
            current_emails+=("$email")
            echo -e "  - ${CYAN}$email${NC}"
        fi
    done < "emails.txt"
    
    if [ ${#current_emails[@]} -eq 0 ]; then
        echo "  (no emails configured)"
    fi
else
    echo "  (file does not exist)"
    current_emails=()
fi

echo ""
configure_emails=$(get_user_input "Do you want to configure authorized emails? (y/n)" "y" "false" "false")

if [[ "$configure_emails" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    # Ask if user wants to keep existing emails
    if [ ${#current_emails[@]} -gt 0 ]; then
        echo ""
        echo "You have ${#current_emails[@]} existing email(s) configured."
        keep_existing=$(get_user_input "Do you want to keep the existing emails and add more? (y/n)" "y" "false" "false")
        
        if [[ "$keep_existing" =~ ^[Yy]([Ee][Ss])?$ ]]; then
            emails=("${current_emails[@]}")
            echo -e "${GREEN}Keeping existing emails${NC}"
        else
            emails=()
            echo -e "${YELLOW}Starting with a clean email list${NC}"
        fi
    else
        emails=()
    fi
    
    echo ""
    echo "Enter email addresses to add (one per line, empty line to finish):"
    
    while true; do
        email=$(get_user_input "Email" "" "false" "false")
        if [ -z "$email" ]; then
            break
        elif [[ "$email" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then
            # Check if email already exists
            email_exists=false
            for existing_email in "${emails[@]}"; do
                if [ "$existing_email" = "$email" ]; then
                    email_exists=true
                    break
                fi
            done
            
            if [ "$email_exists" = true ]; then
                echo -e "${YELLOW}Email already exists, skipping: $email${NC}"
            else
                emails+=("$email")
                echo -e "${GREEN}Added: $email${NC}"
            fi
        else
            echo -e "${YELLOW}Invalid email format, skipping: $email${NC}"
        fi
    done
    
    if [ ${#emails[@]} -gt 0 ]; then
        cat > emails.txt << EOF
# Authorized emails for Shark Authentication
# Generated by setup script on $(date)
# Add one email per line
# Lines starting with # are comments

$(printf '%s\n' "${emails[@]}")
EOF
        echo -e "${GREEN}[OK] Updated emails.txt with ${#emails[@]} email(s)${NC}"
    else
        echo -e "${YELLOW}No emails configured. You may need to add emails later.${NC}"
    fi
fi

echo ""
echo -e "${YELLOW}STEP 6: Google Cloud Console Configuration${NC}"
echo -e "${YELLOW}==========================================${NC}"
echo ""

echo "IMPORTANT: Configure your Google OAuth2 client with this redirect URI:"
echo -e "${CYAN}$funnel_host/oauth2/callback${NC}"
echo ""
echo "1. Go to: https://console.cloud.google.com/apis/credentials"
echo "2. Select your OAuth2 client ID"
echo "3. Add the redirect URI above to 'Authorized redirect URIs'"
echo "4. Save the configuration"
echo ""

continue_setup=$(get_user_input "Have you configured the redirect URI? (y/n)" "" "true" "false")

if [[ ! "$continue_setup" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo ""
    echo -e "${YELLOW}Please complete the Google Cloud Console configuration and run this script again.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}STEP 7: Build and Deploy${NC}"
echo -e "${YELLOW}========================${NC}"
echo ""

deploy=$(get_user_input "Build and start the containers now? (y/n)" "y" "false" "false")

if [[ "$deploy" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo -e "${GREEN}Building and starting containers...${NC}"
    
    # Try docker compose first, then with sudo if it fails
    docker_success=false
    
    if docker compose version >/dev/null 2>&1; then
        docker compose up -d --build
        if [ $? -eq 0 ]; then
            docker_success=true
        else
            echo -e "${YELLOW}Docker compose failed, trying with sudo...${NC}"
            sudo docker compose up -d --build
            if [ $? -eq 0 ]; then
                docker_success=true
                echo -e "${YELLOW}Note: Docker required sudo privileges${NC}"
            fi
        fi
    else
        docker-compose up -d --build
        if [ $? -eq 0 ]; then
            docker_success=true
        else
            echo -e "${YELLOW}Docker compose failed, trying with sudo...${NC}"
            sudo docker-compose up -d --build
            if [ $? -eq 0 ]; then
                docker_success=true
                echo -e "${YELLOW}Note: Docker required sudo privileges${NC}"
            fi
        fi
    fi
    
    if [ "$docker_success" = true ]; then
        echo -e "${GREEN}[OK] Containers started successfully${NC}"
    else
        echo -e "${RED}[ERROR] Failed to start containers even with sudo${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}STEP 8: Start Tailscale Funnel${NC}"
echo -e "${YELLOW}==============================${NC}"
echo ""

start_funnel=$(get_user_input "Start Tailscale Funnel now? (y/n)" "y" "false" "false")

if [[ "$start_funnel" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo -e "${GREEN}Starting Tailscale Funnel on port 4180...${NC}"
    echo -e "${YELLOW}Note: This will run in the background. Use Ctrl+C to stop.${NC}"
    echo ""
    echo -e "Your app will be available at: ${CYAN}$funnel_host${NC}"
    echo ""
    
    # Try tailscale funnel first, then with sudo if it fails
    tailscale funnel 4180 &
    funnel_pid=$!
    sleep 2
    
    # Check if the process is still running (indicates success)
    if kill -0 $funnel_pid 2>/dev/null; then
        echo -e "${GREEN}Tailscale Funnel started successfully${NC}"
        wait $funnel_pid
    else
        echo -e "${YELLOW}Tailscale Funnel failed, trying with sudo...${NC}"
        echo -e "${YELLOW}You may be prompted for your password${NC}"
        sudo tailscale funnel 4180
    fi
else
    echo ""
    echo -e "${YELLOW}To start Tailscale Funnel manually, run:${NC}"
    echo "tailscale funnel 4180"
    echo -e "${YELLOW}If that fails, try: sudo tailscale funnel 4180${NC}"
    echo ""
    echo -e "Your app will be available at: ${CYAN}$funnel_host${NC}"
fi

echo ""
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}===============${NC}"
echo ""
echo "Your secure web app is ready!"
echo -e "Access URL: ${CYAN}$funnel_host${NC}"
echo ""
echo "Troubleshooting:"
echo "- Check container logs: docker compose logs (or: sudo docker compose logs)"
echo "- Restart services: docker compose restart (or: sudo docker compose restart)"
echo "- View Tailscale status: tailscale status"
echo "- Start funnel manually: tailscale funnel 4180 (or: sudo tailscale funnel 4180)"
echo "- Set operator permissions: sudo tailscale set --operator=\$USER"
echo ""
