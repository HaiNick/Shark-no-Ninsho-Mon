#!/usr/bin/env python3
"""
Shark Route Manager - Setup Wizard
Cross-platform setup tool with web GUI
"""

import os
import sys
import subprocess
import secrets
import base64
import platform
import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='setup_templates',
            static_folder='setup_static')

# Determine OS
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'
IS_MAC = platform.system() == 'Darwin'


class SystemCheck:
    """System requirements checker"""

    @staticmethod
    def is_admin():
        """Check if running with admin/sudo privileges"""
        try:
            if IS_WINDOWS:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False

    @staticmethod
    def check_docker():
        """Check if Docker is installed and running"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Check if Docker daemon is running
                daemon_check = subprocess.run(
                    ['docker', 'ps'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return {
                    'installed': True,
                    'running': daemon_check.returncode == 0,
                    'version': result.stdout.strip()
                }
            return {'installed': False, 'running': False, 'version': None}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {'installed': False, 'running': False, 'version': None}

    @staticmethod
    def check_docker_compose():
        """Check if Docker Compose is installed"""
        try:
            # Try docker compose (v2)
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {'installed': True, 'version': result.stdout.strip()}

            # Try docker-compose (v1)
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                'installed': result.returncode == 0,
                'version': result.stdout.strip() if result.returncode == 0 else None
            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {'installed': False, 'version': None}

    @staticmethod
    def check_tailscale():
        """Check if Tailscale is installed and running"""
        try:
            result = subprocess.run(
                ['tailscale', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Check if Tailscale is running
                status_check = subprocess.run(
                    ['tailscale', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return {
                    'installed': True,
                    'running': status_check.returncode == 0,
                    'version': result.stdout.strip()
                }
            return {'installed': False, 'running': False, 'version': None}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {'installed': False, 'running': False, 'version': None}

    @staticmethod
    def check_python_version():
        """Check Python version"""
        version = sys.version_info
        return {
            'version': f"{version.major}.{version.minor}.{version.micro}",
            'compatible': version >= (3, 8)
        }

    @staticmethod
    def run_system_checks():
        """Run all system checks"""
        return {
            'is_admin': SystemCheck.is_admin(),
            'platform': platform.system(),
            'platform_release': platform.release(),
            'python': SystemCheck.check_python_version(),
            'docker': SystemCheck.check_docker(),
            'docker_compose': SystemCheck.check_docker_compose(),
            'tailscale': SystemCheck.check_tailscale()
        }


class SecretGenerator:
    """Generate secure secrets"""

    @staticmethod
    def generate_oauth_cookie_secret():
        """Generate OAuth2 cookie secret (32 bytes, base64 URL-safe)"""
        random_bytes = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

    @staticmethod
    def generate_flask_secret_key():
        """Generate Flask secret key (64 hex characters)"""
        return secrets.token_hex(32)

    @staticmethod
    def generate_all():
        """Generate all required secrets"""
        return {
            'oauth_cookie_secret': SecretGenerator.generate_oauth_cookie_secret(),
            'flask_secret_key': SecretGenerator.generate_flask_secret_key()
        }


class ConfigManager:
    """Manage .env configuration"""

    ENV_FILE = Path('.env')
    ENV_TEMPLATE = Path('.env.template')

    @staticmethod
    def load_existing_env():
        """Load existing .env file if it exists"""
        env_vars = {}
        if ConfigManager.ENV_FILE.exists():
            with open(ConfigManager.ENV_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars

    @staticmethod
    def validate_oauth_client_id(client_id):
        """Validate Google OAuth2 Client ID format"""
        pattern = r'^[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com$'
        return bool(re.match(pattern, client_id))

    @staticmethod
    def validate_tailscale_hostname(hostname):
        """Validate Tailscale hostname format"""
        pattern = r'^[^.]+\.[^.]+\.ts\.net$'
        return bool(re.match(pattern, hostname))

    @staticmethod
    def create_env_file(config):
        """Create .env file with provided configuration"""
        try:
            from datetime import datetime

            env_content = f"""# Generated by Setup Wizard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# DO NOT commit this file to version control!

# ============================================
# Google OAuth2 Client Credentials
# ============================================
OAUTH2_PROXY_CLIENT_ID={config['oauth_client_id']}
OAUTH2_PROXY_CLIENT_SECRET={config['oauth_client_secret']}

# ============================================
# Cookie Secret (32 random bytes, base64 encoded)
# ============================================
OAUTH2_PROXY_COOKIE_SECRET={config['oauth_cookie_secret']}

# ============================================
# Cookie Refresh & Expiration Configuration
# ============================================
# Cookie expiration time (default: 168h = 7 days)
OAUTH2_PROXY_COOKIE_EXPIRE={config.get('cookie_expire', '168h')}

# Cookie refresh interval (0 = disabled, or 1m/1h/24h/168h/720h)
OAUTH2_PROXY_COOKIE_REFRESH={config.get('cookie_refresh', '0')}

# ============================================
# Tailscale Funnel Configuration
# ============================================
FUNNEL_HOST=https://{config['tailscale_hostname']}
FUNNEL_HOSTNAME={config['tailscale_hostname']}

# ============================================
# Flask App Configuration
# ============================================
FLASK_ENV={config['flask_env']}
DEV_MODE={config['dev_mode']}
DEBUG={config['debug']}
PORT=5001
HOST=0.0.0.0

# ============================================
# Flask Secret Key (for session management)
# ============================================
SECRET_KEY={config['flask_secret_key']}

# ============================================
# Flask Session Configuration
# ============================================
SESSION_COOKIE_SECURE={config.get('session_cookie_secure', 'true')}
SESSION_COOKIE_HTTPONLY={config.get('session_cookie_httponly', 'true')}
SESSION_COOKIE_SAMESITE={config.get('session_cookie_samesite', 'Lax')}
PERMANENT_SESSION_LIFETIME={config.get('permanent_session_lifetime', '604800')}
"""

            with open(ConfigManager.ENV_FILE, 'w') as f:
                f.write(env_content)

            return True
        except Exception as e:
            print(f"Error creating .env file: {e}")
            return False

    @staticmethod
    def create_emails_file(emails):
        """Create emails.txt file with authorized emails"""
        try:
            from datetime import datetime
            
            emails_file = Path('emails.txt')
            
            # Create file with header and emails
            content = f"# Authorized emails for Shark-no-Ninsho-Mon\n"
            content += f"# Generated by Setup Wizard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"# Add one email per line\n\n"
            
            if emails:
                if isinstance(emails, str):
                    # Single email string
                    content += f"{emails.strip()}\n"
                elif isinstance(emails, list):
                    # List of emails
                    for email in emails:
                        if email.strip():
                            content += f"{email.strip()}\n"
            
            emails_file.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error creating emails.txt file: {e}")
            return False


# Flask Routes
@app.route('/')
def index():
    """Main setup page"""
    return render_template('setup_wizard.html')


@app.route('/api/system-check', methods=['GET'])
def api_system_check():
    """API endpoint for system checks"""
    checks = SystemCheck.run_system_checks()
    return jsonify(checks)


@app.route('/api/generate-secrets', methods=['POST'])
def api_generate_secrets():
    """API endpoint to generate secrets"""
    secrets = SecretGenerator.generate_all()
    return jsonify(secrets)


@app.route('/api/load-config', methods=['GET'])
def api_load_config():
    """API endpoint to load existing configuration"""
    config = ConfigManager.load_existing_env()
    return jsonify(config)


@app.route('/api/validate-oauth', methods=['POST'])
def api_validate_oauth():
    """API endpoint to validate OAuth2 credentials"""
    data = request.json
    client_id = data.get('client_id', '')

    is_valid = ConfigManager.validate_oauth_client_id(client_id)

    return jsonify({
        'valid': is_valid,
        'message': 'Valid OAuth2 Client ID format' if is_valid else 'Invalid Client ID format. Expected: XXXXXX-XXXXX.apps.googleusercontent.com'
    })


@app.route('/api/validate-tailscale', methods=['POST'])
def api_validate_tailscale():
    """API endpoint to validate Tailscale hostname"""
    data = request.json
    hostname = data.get('hostname', '')

    is_valid = ConfigManager.validate_tailscale_hostname(hostname)

    return jsonify({
        'valid': is_valid,
        'message': 'Valid Tailscale hostname format' if is_valid else 'Invalid hostname format. Expected: hostname.tailnet.ts.net'
    })


@app.route('/api/save-config', methods=['POST'])
def api_save_config():
    """API endpoint to save configuration"""
    try:
        config = request.json

        # Validate required fields
        required_fields = [
            'oauth_client_id',
            'oauth_client_secret',
            'oauth_cookie_secret',
            'tailscale_hostname',
            'flask_secret_key',
            'dev_mode',
            'flask_env',
            'debug'
        ]

        for field in required_fields:
            if field not in config or not config[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400

        # Create .env file
        env_success = ConfigManager.create_env_file(config)
        
        if not env_success:
            return jsonify({
                'success': False,
                'message': 'Failed to create .env file'
            }), 500

        # Create emails.txt file with authorized email(s)
        authorized_email = config.get('authorized_email', '')
        if authorized_email:
            emails_success = ConfigManager.create_emails_file(authorized_email)
            if not emails_success:
                return jsonify({
                    'success': False,
                    'message': 'Configuration saved but failed to create emails.txt file'
                }), 500

        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully! Created .env and emails.txt files.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving configuration: {str(e)}'
        }), 500


@app.route('/api/docker/start', methods=['POST'])
def api_docker_start():
    """API endpoint to start Docker containers"""
    try:
        # Check if docker-compose.yml exists
        if not Path('docker-compose.yml').exists():
            return jsonify({
                'success': False,
                'message': 'docker-compose.yml not found in current directory'
            }), 404

        # Create required files before starting Docker to prevent Docker from creating them as directories
        routes_file = Path('routes.json')
        if not routes_file.exists():
            routes_file.write_text('{"_default": {}}', encoding='utf-8')
        elif routes_file.is_dir():
            # If it's a directory, remove it and create as file
            try:
                routes_file.rmdir()
                routes_file.write_text('{"_default": {}}', encoding='utf-8')
            except OSError:
                # Directory not empty, don't remove
                pass
        
        emails_file = Path('emails.txt')
        if not emails_file.exists():
            emails_file.write_text('# Add authorized emails here (one per line)\n', encoding='utf-8')
        elif emails_file.is_dir():
            # If it's a directory, remove it and create as file
            try:
                emails_file.rmdir()
                emails_file.write_text('# Add authorized emails here (one per line)\n', encoding='utf-8')
            except OSError:
                # Directory not empty, don't remove
                pass

        result = None
        error_msg = None
        
        # Try docker compose (v2) first
        try:
            result = subprocess.run(
                ['docker', 'compose', 'up', '-d', '--build'],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'Docker containers started successfully (using docker compose v2)',
                    'output': result.stdout
                })
            else:
                error_msg = result.stderr or result.stdout
        except FileNotFoundError:
            # Docker command not found
            pass
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'message': 'Docker compose command timed out after 120 seconds'
            }), 500
        except Exception as e:
            error_msg = str(e)
        
        # Try docker-compose (v1) as fallback
        try:
            result = subprocess.run(
                ['docker-compose', 'up', '-d', '--build'],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'Docker containers started successfully (using docker-compose v1)',
                    'output': result.stdout
                })
            else:
                error_msg = result.stderr or result.stdout
        except FileNotFoundError:
            # Neither command found
            return jsonify({
                'success': False,
                'message': 'Docker Compose not found. Please install Docker Desktop or Docker Compose plugin.'
            }), 500
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'message': 'docker-compose command timed out after 120 seconds'
            }), 500
        except Exception as e:
            error_msg = str(e)
        
        # If we got here, both commands failed
        return jsonify({
            'success': False,
            'message': 'Failed to start Docker containers',
            'error': error_msg or 'Unknown error occurred'
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error starting Docker: {str(e)}'
        }), 500


@app.route('/api/docker/stop', methods=['POST'])
def api_docker_stop():
    """API endpoint to stop Docker containers"""
    try:
        result = None
        error_msg = None
        
        # Try docker compose (v2) first
        try:
            result = subprocess.run(
                ['docker', 'compose', 'down'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'Docker containers stopped successfully (using docker compose v2)',
                    'output': result.stdout
                })
            else:
                error_msg = result.stderr or result.stdout
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'message': 'Docker compose command timed out'
            }), 500
        except Exception as e:
            error_msg = str(e)
        
        # Try docker-compose (v1) as fallback
        try:
            result = subprocess.run(
                ['docker-compose', 'down'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': 'Docker containers stopped successfully (using docker-compose v1)',
                    'output': result.stdout
                })
            else:
                error_msg = result.stderr or result.stdout
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'message': 'Docker Compose not found. Please install Docker Desktop or Docker Compose plugin.'
            }), 500
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'message': 'docker-compose command timed out'
            }), 500
        except Exception as e:
            error_msg = str(e)
        
        # If we got here, both commands failed
        return jsonify({
            'success': False,
            'message': 'Failed to stop Docker containers',
            'error': error_msg or 'Unknown error occurred'
        }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error stopping Docker: {str(e)}'
        }), 500


def print_banner():
    """Print setup wizard banner"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          Shark Route Manager - Setup Wizard               ║
║                                                           ║
║     Cross-platform setup tool with web interface          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Main entry point"""
    print_banner()

    # Run initial system checks
    print("Running system checks...\n")
    checks = SystemCheck.run_system_checks()

    # Print system info
    print(f"Platform: {checks['platform']} {checks['platform_release']}")
    print(f"Python: {checks['python']['version']}")
    print(
        f"Admin/Sudo: {'Yes - privileges detected' if checks['is_admin'] else 'No - run with admin/sudo'}"
    )
    print()

    # Check Docker
    docker = checks['docker']
    print(f"Docker: {'Installed' if docker['installed'] else 'Not Found'}")
    if docker['installed']:
        print(f"  Version: {docker['version']}")
    print(f"  Running: {'Yes' if docker['running'] else 'No'}")
    print()

    # Check Docker Compose
    compose = checks['docker_compose']
    print(
        f"Docker Compose: {'Installed' if compose['installed'] else 'Not Found'}")
    if compose['installed']:
        print(f"  Version: {compose['version']}")
    print()

    # Check Tailscale
    tailscale = checks['tailscale']
    print(
        f"Tailscale: {'Installed' if tailscale['installed'] else 'Not Found'}")
    if tailscale['installed']:
        print(f"  Version: {tailscale['version']}")
        print(f"  Running: {'Yes' if tailscale['running'] else 'No'}")
    print()

    # Warnings
    warnings = []
    if not checks['is_admin']:
        warnings.append(
            "WARNING: Not running with admin/sudo privileges - Docker and Tailscale commands may fail")
    if not docker['installed']:
        warnings.append(
            "WARNING: Docker is not installed - Install from https://docker.com")
    elif not docker['running']:
        warnings.append(
            "WARNING: Docker is not running - Please start Docker Desktop")
    if not compose['installed']:
        warnings.append("WARNING: Docker Compose is not installed")
    if not tailscale['installed']:
        warnings.append(
            "WARNING: Tailscale is not installed - Install from https://tailscale.com")
    elif not tailscale['running']:
        warnings.append(
            "WARNING: Tailscale is not running - Please start Tailscale")

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
        print()

    # Create required files if they don't exist (prevent Docker from creating them as directories)
    print("Checking required files...")
    routes_file = Path('routes.json')
    if not routes_file.exists():
        routes_file.write_text('{"_default": {}}', encoding='utf-8')
        print("  Created routes.json")
    elif routes_file.is_dir():
        print("  WARNING: routes.json exists as a directory! Please remove it manually.")
    
    emails_file = Path('emails.txt')
    if not emails_file.exists():
        emails_file.write_text('# Add authorized emails here (one per line)\n', encoding='utf-8')
        print("  Created emails.txt")
    elif emails_file.is_dir():
        print("  WARNING: emails.txt exists as a directory! Please remove it manually.")
    print()

    # Start Flask server
    print("=" * 70)
    print("Starting setup wizard web interface...")
    print("\n   Open your browser and navigate to:")
    print("   \033[1;36mhttp://localhost:8080\033[0m (from this machine)")
    
    # Try to get local network IP address (no internet required)
    try:
        import socket
        # Get hostname and resolve to local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Filter out localhost addresses
        if local_ip and not local_ip.startswith('127.'):
            print(f"   \033[1;36mhttp://{local_ip}:8080\033[0m (from other devices on your LAN)\n")
        else:
            # Fallback: try to get IP from all network interfaces
            import platform
            if platform.system() == 'Windows':
                print("   \033[1;36mhttp://<your-ip>:8080\033[0m (from other devices on your LAN)\n")
                print("   Run 'ipconfig' to find your local IP address\n")
            else:
                print("   \033[1;36mhttp://<your-ip>:8080\033[0m (from other devices on your LAN)\n")
                print("   Run 'ip addr' or 'ifconfig' to find your local IP address\n")
    except Exception:
        import platform
        if platform.system() == 'Windows':
            print("   \033[1;36mhttp://<your-ip>:8080\033[0m (from other devices on your LAN)\n")
            print("   Run 'ipconfig' to find your local IP address\n")
        else:
            print("   \033[1;36mhttp://<your-ip>:8080\033[0m (from other devices on your LAN)\n")
            print("   Run 'ip addr' or 'ifconfig' to find your local IP address\n")
    
    print("=" * 70)
    print("\nPress CTRL+C to stop the setup wizard\n")

    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n\nSetup wizard stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
