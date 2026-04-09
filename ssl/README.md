# 🔒 SSL/TLS Configuration for Lazarus Protocol

## Overview

This directory contains SSL/TLS configuration for enabling HTTPS in Lazarus Protocol.

## Quick Start

### Using Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"

# Copy to ssl directory
mkdir -p ssl
cp cert.pem key.pem ssl/

# Start with HTTPS
export LAZARUS_SSL_CERT_FILE=ssl/cert.pem
export LAZARUS_SSL_KEY_FILE=ssl/key.pem
python3 -m web.server
```

### Using Let's Encrypt (Production)

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Set environment variables
export LAZARUS_SSL_CERT_FILE=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
export LAZARUS_SSL_KEY_FILE=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# Start server
python3 -m web.server
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LAZARUS_SSL_CERT_FILE` | Path to SSL certificate file | None |
| `LAZARUS_SSL_KEY_FILE` | Path to SSL private key file | None |

## Docker Compose with HTTPS

```yaml
services:
  lazarus-https:
    build: .
    ports:
      - "8443:8000"
    environment:
      - LAZARUS_SSL_CERT_FILE=/app/ssl/cert.pem
      - LAZARUS_SSL_KEY_FILE=/app/ssl/key.pem
    volumes:
      - ./ssl:/app/ssl:ro
```

## Certificate Types

### Self-Signed (Development)
- **Use**: Local development and testing
- **Security**: Browser warnings expected
- **Generation**: `openssl` command
- **Lifetime**: 1 year

### Let's Encrypt (Production)
- **Use**: Production deployments
- **Security**: Browser trusted
- **Generation**: Certbot
- **Lifetime**: 90 days (auto-renewal recommended)

### Commercial CA (Enterprise)
- **Use**: Enterprise environments
- **Security**: Highest trust level
- **Generation**: Purchased from CA
- **Lifetime**: 1-2 years

## Security Best Practices

1. **Key Protection**: Keep private keys secure (chmod 600)
2. **Certificate Rotation**: Rotate certificates regularly
3. **TLS Version**: Use TLS 1.2 or higher
4. **Cipher Suites**: Use strong cipher suites
5. **HTTP Redirection**: Redirect HTTP to HTTPS
6. **HSTS**: Consider implementing HTTP Strict Transport Security

## Troubleshooting

### Common Issues

1. **Certificate Not Found**
   ```bash
   # Check file existence
   ls -la $LAZARUS_SSL_CERT_FILE $LAZARUS_SSL_KEY_FILE
   
   # Check permissions
   chmod 600 $LAZARUS_SSL_KEY_FILE
   ```

2. **Permission Denied**
   ```bash
   # Fix key permissions
   chmod 400 ssl/key.pem
   
   # Fix directory permissions
   chmod 700 ssl/
   ```

3. **Browser Warnings**
   - For self-signed certs: Accept the security exception
   - For production: Use trusted CA certificates

### OpenSSL Commands

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Check certificate
openssl x509 -in cert.pem -text -noout

# Check private key
openssl rsa -in key.pem -check

# Verify certificate chain
openssl verify -CAfile ca.pem cert.pem
```

## Automated Renewal

### Let's Encrypt with Cron

```bash
# Add to crontab
0 0 * * 0 certbot renew --quiet && systemctl restart lazarus
```

### Systemd Timer

```bash
# Create timer file
sudo nano /etc/systemd/system/certbot-renew.timer

[Unit]
Description=Certbot renewal timer

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

## Monitoring

### Certificate Expiry Check

```bash
# Check expiry date
openssl x509 -in cert.pem -noout -enddate

# Days until expiry
openssl x509 -in cert.pem -noout -checkend 86400 && echo "Valid" || echo "Expiring"
```

### Health Check Endpoint

The Lazarus dashboard includes a health endpoint:

```bash
curl -k https://localhost:8000/status
```

## References

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)