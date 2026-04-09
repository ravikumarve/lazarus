#!/bin/bash
# Generate self-signed SSL certificate for Lazarus Protocol development

set -e

# Create ssl directory if it doesn't exist
mkdir -p ssl

# Generate self-signed certificate
openssl req -x509 \
  -newkey rsa:4096 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -days 365 \
  -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:127.0.0.1"

# Set proper permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Verify certificate
echo "✅ Certificate generated successfully:"
echo "   Certificate: ssl/cert.pem"
echo "   Private key: ssl/key.pem"
echo ""
echo "📋 Certificate details:"
openssl x509 -in ssl/cert.pem -text -noout | grep -E "(Subject:|Not Before|Not After)"

# Generate environment file for easy setup
echo ""
echo "🌐 To use HTTPS, set these environment variables:"
echo "export LAZARUS_SSL_CERT_FILE=$(pwd)/ssl/cert.pem"
echo "export LAZARUS_SSL_KEY_FILE=$(pwd)/ssl/key.pem"
echo ""
echo "🚀 Start server with HTTPS:"
echo "python3 -m web.server"
echo ""
echo "🔐 Access dashboard at: https://localhost:6666"
echo "   (Browser will show security warning for self-signed certificate)"