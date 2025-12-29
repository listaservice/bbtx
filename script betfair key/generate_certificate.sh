#!/bin/bash
# Script pentru generare certificat SSL Betfair
# Folosește OpenSSL pentru a crea certificatul self-signed

echo "=================================="
echo "🔐 BETFAIR SSL CERTIFICATE GENERATOR"
echo "=================================="
echo ""

# Check if OpenSSL is installed
if ! command -v openssl &> /dev/null; then
    echo "❌ OpenSSL nu este instalat!"
    echo "   Instalează cu: brew install openssl (macOS) sau apt-get install openssl (Linux)"
    exit 1
fi

echo "✅ OpenSSL găsit: $(openssl version)"
echo ""

# Create output directory
OUTPUT_DIR="betfair_certificates"
mkdir -p "$OUTPUT_DIR"

echo "📁 Certificatele vor fi salvate în: $OUTPUT_DIR/"
echo ""

# Generate private key
echo "🔑 Generare private key (2048-bit RSA)..."
openssl genrsa -out "$OUTPUT_DIR/client-2048.key" 2048

if [ $? -eq 0 ]; then
    echo "✅ Private key generat: $OUTPUT_DIR/client-2048.key"
else
    echo "❌ Eroare la generare private key"
    exit 1
fi

echo ""

# Generate certificate signing request (CSR)
echo "📝 Generare Certificate Signing Request (CSR)..."
echo "   (Apasă Enter pentru toate întrebările - nu sunt importante pentru Betfair)"
echo ""

openssl req -new -key "$OUTPUT_DIR/client-2048.key" -out "$OUTPUT_DIR/client-2048.csr" -subj "/C=RO/ST=Bucharest/L=Bucharest/O=Betix/OU=Betting/CN=betix-user"

if [ $? -eq 0 ]; then
    echo "✅ CSR generat: $OUTPUT_DIR/client-2048.csr"
else
    echo "❌ Eroare la generare CSR"
    exit 1
fi

echo ""

# Generate self-signed certificate
echo "🎫 Generare self-signed certificate (valabil 365 zile)..."
openssl x509 -req -days 365 -in "$OUTPUT_DIR/client-2048.csr" -signkey "$OUTPUT_DIR/client-2048.key" -out "$OUTPUT_DIR/client-2048.crt"

if [ $? -eq 0 ]; then
    echo "✅ Certificat generat: $OUTPUT_DIR/client-2048.crt"
else
    echo "❌ Eroare la generare certificat"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ CERTIFICAT GENERAT CU SUCCES!"
echo "=================================="
echo ""
echo "📂 Fișiere generate în $OUTPUT_DIR/:"
echo "   1. client-2048.key  - Private Key (NU îl împărtăși cu nimeni!)"
echo "   2. client-2048.csr  - Certificate Signing Request (nu e necesar pentru Betfair)"
echo "   3. client-2048.crt  - Certificat SSL (acesta se uploadează pe Betfair)"
echo ""
echo "=================================="
echo "📋 URMĂTORII PAȘI:"
echo "=================================="
echo ""
echo "1. Deschide Betfair.ro și loghează-te"
echo "2. My Account → My Betfair Account → My Details → Security Settings"
echo "3. Găsește 'Automated Betting Program Access' și click 'Edit'"
echo "4. Upload fișierul: $OUTPUT_DIR/client-2048.crt"
echo "5. Salvează"
echo ""
echo "6. După upload, Betfair îți va genera automat un App Key"
echo "7. Copiază App Key-ul (16 caractere)"
echo "8. Trimite-mi:"
echo "   - App Key"
echo "   - Fișierul client-2048.crt"
echo "   - Fișierul client-2048.key"
echo ""
echo "=================================="
