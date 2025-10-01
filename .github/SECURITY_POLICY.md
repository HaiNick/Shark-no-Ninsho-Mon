# Security Policy

## Our Security Commitment

Shark-no-Ninsho-Mon is designed with security as a top priority. We take security vulnerabilities seriously and appreciate the community's help in identifying and resolving them.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | ✅ Yes             |
| < 1.0   | ❌ No              |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them responsibly by:

### Preferred Method: Private Security Advisory
1. Go to the [Security tab](https://github.com/HaiNick/Shark-no-Ninsho-Mon/security) of this repository
2. Click "Report a vulnerability"
3. Fill out the security advisory form

### Alternative Method: Email
Send an email to: [security@example.com] (replace with actual email)

Include the following information:
- Type of vulnerability
- Full paths of source file(s) related to the manifestation of the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution**: Varies based on severity and complexity

## Security Features

This project implements several security measures:

### Authentication & Authorization
- Google OAuth2 integration
- Email domain-based access control
- Secure session management
- CSRF protection

### Network Security
- Tailscale zero-trust networking
- TLS encryption via Tailscale Funnel
- No exposed ports on local network
- Container isolation

### Application Security
- Environment variable configuration
- Secure cookie handling
- Input validation and sanitization
- Security headers implementation

## Security Best Practices for Users

### Deployment Security
1. **Use strong secrets**: Generate cryptographically secure values for all secrets
2. **Limit email access**: Only add necessary email addresses to `emails.txt`
3. **Regular updates**: Keep all components updated
4. **Monitor logs**: Review application and container logs regularly

### Configuration Security
1. **Environment variables**: Never commit secrets to version control
2. **File permissions**: Ensure proper file permissions on configuration files
3. **Network isolation**: Use Tailscale's network isolation features
4. **Regular rotation**: Rotate OAuth2 secrets and Tailscale auth keys regularly

### Operational Security
1. **Access control**: Limit who has access to the deployment environment
2. **Backup security**: Secure any backups of configuration
3. **Incident response**: Have a plan for security incidents
4. **Documentation**: Keep security documentation up to date

## Known Security Considerations

### Dependencies
- Regular dependency updates via Dependabot
- Container image scanning in CI/CD
- Python package vulnerability scanning

### Network Exposure
- Application is exposed to the internet via Tailscale Funnel
- OAuth2 provides the primary authentication layer
- Consider additional rate limiting for production deployments

## Security Disclosure Policy

When we receive a security bug report, we will:

1. **Confirm** the problem and determine affected versions
2. **Audit** code to find any similar problems
3. **Prepare** fixes for all supported versions
4. **Release** security updates as quickly as possible
5. **Credit** the reporter (unless they prefer to remain anonymous)

## Legal

This security policy is subject to the terms in our [LICENSE](../LICENSE) file.

Thank you for helping keep Shark-no-Ninsho-Mon and our users safe! 🦈🔒