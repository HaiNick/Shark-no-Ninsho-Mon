#!/usr/bin/env python3
"""
Generate secure secrets for .env file
Works on Windows, Linux, and macOS
"""
import os
import base64
import secrets
import sys
from pathlib import Path


def generate_oauth_cookie_secret():
    """Generate 32-byte base64 URL-safe secret for oauth2-proxy"""
    random_bytes = os.urandom(32)
    return base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')


def generate_flask_secret_key():
    """Generate secure random secret key for Flask"""
    return secrets.token_hex(32)


def update_env_file(env_path, oauth_secret, flask_secret):
    """Update .env file with generated secrets"""
    if not env_path.exists():
        print(f"❌ Error: {env_path} not found!")
        print(f"💡 Tip: Copy .env.template to .env first:")
        print(f"   cp .env.template .env")
        return False
    
    # Read current content
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track what we updated
    updated = []
    
    # Update OAUTH2_PROXY_COOKIE_SECRET
    if 'OAUTH2_PROXY_COOKIE_SECRET=' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('OAUTH2_PROXY_COOKIE_SECRET='):
                lines[i] = f'OAUTH2_PROXY_COOKIE_SECRET={oauth_secret}'
                updated.append('OAUTH2_PROXY_COOKIE_SECRET')
                break
        content = '\n'.join(lines)
    
    # Update or add SECRET_KEY
    if 'SECRET_KEY=' in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('SECRET_KEY=') or line.startswith('# SECRET_KEY='):
                lines[i] = f'SECRET_KEY={flask_secret}'
                updated.append('SECRET_KEY')
                break
        content = '\n'.join(lines)
    else:
        # Add SECRET_KEY if not present
        content += f'\n\n# Flask Secret Key (auto-generated)\nSECRET_KEY={flask_secret}\n'
        updated.append('SECRET_KEY')
    
    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return updated


def main():
    print("=" * 70)
    print("🔐 Secret Generator for Shark-no-Ninsho-Mon")
    print("=" * 70)
    print()
    
    # Find .env file
    env_path = Path('.env')
    if not env_path.exists():
        env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("❌ Error: .env file not found!")
        print()
        print("📝 Please create .env first:")
        print("   cp .env.template .env")
        print()
        sys.exit(1)
    
    print(f"📄 Found .env file: {env_path.absolute()}")
    print()
    
    # Generate secrets
    print("🔄 Generating secrets...")
    oauth_secret = generate_oauth_cookie_secret()
    flask_secret = generate_flask_secret_key()
    print("✅ Secrets generated!")
    print()
    
    # Show secrets
    print("📋 Generated Secrets:")
    print("-" * 70)
    print(f"OAUTH2_PROXY_COOKIE_SECRET={oauth_secret}")
    print(f"SECRET_KEY={flask_secret}")
    print("-" * 70)
    print()
    
    # Ask for confirmation
    response = input("❓ Update .env file with these secrets? [Y/n]: ").strip().lower()
    
    if response in ['', 'y', 'yes']:
        updated = update_env_file(env_path, oauth_secret, flask_secret)
        
        if updated:
            print()
            print("✅ Successfully updated .env file!")
            print(f"   Updated: {', '.join(updated)}")
            print()
            print("🎉 Your secrets are ready!")
            print()
            print("⚠️  Important Security Notes:")
            print("   1. Never commit .env to git (it's already in .gitignore)")
            print("   2. Keep these secrets safe and private")
            print("   3. Generate new secrets for production deployments")
            print()
        else:
            print()
            print("❌ Failed to update .env file")
            print()
    else:
        print()
        print("❌ Cancelled. No changes made to .env")
        print()
        print("💡 You can manually copy the secrets above into your .env file")
        print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
