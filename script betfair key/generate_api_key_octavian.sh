#!/bin/bash
# Script pentru generare App Key pentru Octavianmatei1990@gmail.com
# Folosește backend-ul BETIX care are Master App Key configurat

echo "🔑 Generare Betfair App Key pentru Octavianmatei1990@gmail.com"
echo "================================================================"
echo ""

# 1. Login user și obține JWT token
echo "📝 Step 1: Login user..."
LOGIN_RESPONSE=$(curl -s -X POST "http://89.39.246.58/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "Octavianmatei1990@gmail.com",
    "password": "parola_betix_user"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login eșuat. Verifică că userul există în sistem."
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login reușit! Token obținut."
echo ""

# 2. Generează App Key folosind endpoint-ul backend
echo "📝 Step 2: Generare App Key..."
APP_KEY_RESPONSE=$(curl -s -X POST "http://89.39.246.58/api/betfair/generate-app-key" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "username": "Octavianmatei1990@gmail.com",
    "password": "Rx313504."
  }')

echo "Response:"
echo "$APP_KEY_RESPONSE" | jq '.'
echo ""

SUCCESS=$(echo $APP_KEY_RESPONSE | jq -r '.success')
APP_KEY=$(echo $APP_KEY_RESPONSE | jq -r '.app_key')

if [ "$SUCCESS" == "true" ]; then
  echo "================================================================"
  echo "✅ SUCCESS! App Key generat și salvat!"
  echo "================================================================"
  echo ""
  echo "🔑 DELAYED APP KEY:"
  echo "   $APP_KEY"
  echo ""
  echo "💾 App Key-ul a fost salvat automat în database (criptat AES-256)"
  echo "🎉 Userul poate acum să adauge echipe și să ruleze bot-ul!"
  echo ""
else
  echo "❌ Eroare la generare App Key"
  echo "Message: $(echo $APP_KEY_RESPONSE | jq -r '.message')"
fi
