#!/usr/bin/env python3
"""
Script pentru creare App Key pe Betfair folosind certificatul SSL
Acum că certificatul este uploadat, putem crea App Key-ul
"""

import httpx
import json
import sys
import os

# Paths to certificate files
CERT_PATH = "betfair_certificates/client-2048.crt"
KEY_PATH = "betfair_certificates/client-2048.key"

# Betfair credentials
USERNAME = "Octavianmatei1990@gmail.com"
PASSWORD = "Rx313504."

# Betfair endpoints
IDENTITY_URL = "https://identitysso-cert.betfair.ro/api/certlogin"
ACCOUNT_API_URL = "https://api.betfair.com/exchange/account/json-rpc/v1"

def login_with_certificate():
    """Login pe Betfair folosind certificatul SSL"""
    print("🔐 Login pe Betfair cu certificat SSL...")

    try:
        client = httpx.Client(
            cert=(CERT_PATH, KEY_PATH),
            timeout=30.0,
            verify=True
        )

        response = client.post(
            IDENTITY_URL,
            data={
                'username': USERNAME,
                'password': PASSWORD
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get('loginStatus') == 'SUCCESS':
                session_token = data.get('sessionToken')
                print(f"✅ Login reușit cu certificat!")
                print(f"📝 Session Token: {session_token[:20]}...")
                return session_token, client
            else:
                print(f"❌ Login eșuat: {data.get('loginStatus')}")
                return None, None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Eroare la login: {e}")
        return None, None

def create_app_key(session_token, client, app_name="BetixOctavian2024"):
    """Creează App Key folosind session token-ul obținut cu certificatul"""
    print(f"\n🔑 Creare App Key: {app_name}")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "AccountAPING/v1.0/createDeveloperAppKeys",
            "params": {
                "appName": app_name
            },
            "id": 1
        }

        response = client.post(
            ACCOUNT_API_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Authentication': session_token
            }
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if 'result' in data:
                result = data['result']
                print(f"\n✅ App Keys create cu succes!")
                print(f"=" * 80)

                # Delayed App Key
                if result.get('appVersions'):
                    for version in result['appVersions']:
                        app_key = version.get('applicationKey')
                        version_str = version.get('version', '')

                        if 'DELAY' in version_str:
                            print(f"\n🟢 DELAYED APP KEY (Active):")
                            print(f"   {app_key}")
                        else:
                            print(f"\n🔴 LIVE APP KEY (Inactive - necesită activare £299):")
                            print(f"   {app_key}")

                print(f"\n" + "=" * 80)
                return result
            elif 'error' in data:
                error = data['error']
                print(f"❌ Eroare API: {error.get('message')}")
                print(f"   Code: {error.get('code')}")

                if 'APP_KEY_CREATION_FAILED' in str(error):
                    print(f"\n💡 App Key deja există! Încearcă getDeveloperAppKeys")

                return None
            else:
                print(f"❌ Răspuns neașteptat: {data}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Eroare la creare App Key: {e}")
        return None

def get_existing_app_keys(session_token, client):
    """Recuperează App Keys existente"""
    print(f"\n🔍 Verificare App Keys existente...")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "AccountAPING/v1.0/getDeveloperAppKeys",
            "params": {},
            "id": 1
        }

        response = client.post(
            ACCOUNT_API_URL,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Authentication': session_token
            }
        )

        if response.status_code == 200:
            data = response.json()

            if 'result' in data:
                result = data['result']

                if not result:
                    print("ℹ️ Nu există App Keys. Creăm unul nou...")
                    return None

                print(f"\n✅ App Keys găsite!")
                print(f"=" * 80)

                for app in result:
                    app_name = app.get('appName')
                    print(f"\nAplicație: {app_name}")

                    for version in app.get('appVersions', []):
                        app_key = version.get('applicationKey')
                        version_str = version.get('version')

                        if 'DELAY' in version_str:
                            print(f"  🟢 DELAYED APP KEY: {app_key}")
                        else:
                            print(f"  🔴 LIVE APP KEY: {app_key}")

                print(f"\n" + "=" * 80)
                return result
            else:
                print(f"❌ Răspuns neașteptat: {data}")
                return None
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Eroare: {e}")
        return None

def main():
    print("=" * 80)
    print("🔑 BETFAIR APP KEY GENERATOR (CU CERTIFICAT SSL)")
    print("=" * 80)
    print()

    # Check certificate files
    if not os.path.exists(CERT_PATH):
        print(f"❌ Certificat nu găsit: {CERT_PATH}")
        sys.exit(1)

    if not os.path.exists(KEY_PATH):
        print(f"❌ Private key nu găsit: {KEY_PATH}")
        sys.exit(1)

    print(f"✅ Certificat găsit: {CERT_PATH}")
    print(f"✅ Private key găsit: {KEY_PATH}")
    print()

    # Login with certificate
    session_token, client = login_with_certificate()

    if not session_token:
        print("\n❌ Nu s-a putut obține session token")
        sys.exit(1)

    # Check for existing app keys
    existing_keys = get_existing_app_keys(session_token, client)

    if existing_keys:
        print("\n✅ App Keys deja există!")
        print("\n💾 Salvează Delayed App Key-ul pentru BETIX!")
    else:
        # Create new app keys
        result = create_app_key(session_token, client)

        if result:
            print("\n✅ App Keys create cu succes!")
            print("\n💾 Salvează Delayed App Key-ul pentru BETIX!")
        else:
            print("\n❌ Nu s-au putut crea App Keys")
            sys.exit(1)

    client.close()

    print("\n" + "=" * 80)
    print("✅ Script finalizat!")
    print("=" * 80)

if __name__ == "__main__":
    main()
