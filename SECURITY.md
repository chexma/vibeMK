# Security Policy

## Supported Versions

We actively maintain security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in vibeMK, please report it responsibly:

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. **Email** us directly at: security@your-domain.com
3. **Include** the following information:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Suggested fix (if available)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Development**: Depends on severity
- **Disclosure**: Coordinated disclosure after fix

### Security Best Practices

When using vibeMK:

#### Configuration Security
- **Never commit** `claude_desktop_config.json` with real credentials
- **Use environment variables** for sensitive data when possible
- **Rotate API keys** regularly
- **Enable SSL/TLS** for production CheckMK servers

#### Network Security
- **Restrict network access** to CheckMK servers
- **Use HTTPS** instead of HTTP
- **Configure firewalls** appropriately
- **Monitor access logs**

#### CheckMK Server Security
- **Use dedicated automation users** with minimal required permissions
- **Enable audit logging** in CheckMK
- **Keep CheckMK updated** to latest security patches
- **Review user permissions** regularly

### Known Security Considerations

#### API Key Storage
- API keys are stored in `claude_desktop_config.json`
- This file should have restricted file permissions (600)
- Consider using environment variables for CI/CD environments

#### Network Communications
- All API calls to CheckMK are made over HTTP(S)
- SSL certificate verification can be disabled (not recommended for production)
- Consider using client certificates for additional security

#### Logging
- Server logs may contain API endpoints but not credentials
- Debug mode may log more detailed information
- Ensure log files have appropriate permissions

### Security Updates

Security updates will be:
- Released as patch versions (e.g., 2.0.1, 2.0.2)
- Documented in release notes
- Announced through GitHub releases
- Included in the main branch immediately

### Acknowledgments

We appreciate the security research community and will acknowledge responsible disclosure contributors (with their permission) in our security advisories.

## Contact

For security-related questions or concerns:
- Email: security@your-domain.com
- For general questions: [GitHub Issues](https://github.com/your-username/vibeMK/issues)

Thank you for helping keep vibeMK secure!