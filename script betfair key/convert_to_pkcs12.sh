#!/bin/bash
# Convert certificate to PKCS#12 format for Betfair

echo "=================================="
echo "🔄 CONVERT CERTIFICATE TO PKCS#12"
echo "=================================="
echo ""

cd betfair_certificates

# Convert to PKCS#12 format (required by some Betfair endpoints)
echo "Converting to PKCS#12 format..."
openssl pkcs12 -export -out client-2048.p12 -inkey client-2048.key -in client-2048.crt -passout pass:

if [ $? -eq 0 ]; then
    echo "✅ PKCS#12 certificate created: client-2048.p12"
else
    echo "❌ Failed to create PKCS#12 certificate"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ CONVERSION COMPLETE!"
echo "=================================="
echo ""
echo "Files available:"
echo "  - client-2048.crt (PEM format)"
echo "  - client-2048.key (Private key)"
echo "  - client-2048.p12 (PKCS#12 format)"
