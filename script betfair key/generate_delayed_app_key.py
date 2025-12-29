#!/usr/bin/env python3
"""
Script pentru generare automată Delayed App Key pe Betfair
Folosește API-ul Betfair pentru a obține ssoid și a crea App Keys
"""

import httpx
import json
import sys
from typing import Optional, Dict


class BetfairAppKeyGenerator:
    """Generator pentru Betfair Delayed App Key"""

    IDENTITY_URL = "https://identitysso.betfair.ro/api/login"
    ACCOUNT_API_URL = "https://api.betfair.com/exchange/account/json-rpc/v1"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.ssoid: Optional[str] = None
        self.client = httpx.Client(timeout=30.0)

    def login(self) -> bool:
        """
        Login pe Betfair și obținere ssoid (Session Token)
        """
        print(f"🔐 Login pe Betfair cu username: {self.username}")

        try:
            response = self.client.post(
                self.IDENTITY_URL,
                data={
                    'username': self.username,
                    'password': self.password
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
                    self.ssoid = data.get('sessionToken')
                    print(f"✅ Login reușit!")
                    print(f"📝 Session Token (ssoid): {self.ssoid[:20]}...")
                    return True
                else:
                    print(f"❌ Login eșuat: {data.get('loginStatus')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Eroare la login: {e}")
            return False

    def create_app_keys(self, app_name: str) -> Optional[Dict]:
        """
        Creează Delayed și Live App Keys folosind Account API
        """
        if not self.ssoid:
            print("❌ Nu există ssoid. Rulează login() mai întâi.")
            return None

        print(f"\n🔑 Creare App Keys pentru aplicația: {app_name}")

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "AccountAPING/v1.0/createDeveloperAppKeys",
                "params": {
                    "appName": app_name
                },
                "id": 1
            }

            response = self.client.post(
                self.ACCOUNT_API_URL,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Authentication': self.ssoid
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
                    delayed_key = result.get('appVersions', [{}])[0].get('applicationKey')
                    print(f"\n🟢 DELAYED APP KEY (Active):")
                    print(f"   Application Key: {delayed_key}")
                    print(f"   Version: 1.0-DELAY")
                    print(f"   Status: Active")

                    # Live App Key
                    if len(result.get('appVersions', [])) > 1:
                        live_key = result['appVersions'][1].get('applicationKey')
                        print(f"\n🔴 LIVE APP KEY (Inactive):")
                        print(f"   Application Key: {live_key}")
                        print(f"   Version: 1.0")
                        print(f"   Status: Inactive (necesită activare £299)")

                    print(f"\n" + "=" * 80)

                    return {
                        'delayed_app_key': delayed_key,
                        'app_name': app_name,
                        'result': result
                    }
                elif 'error' in data:
                    error = data['error']
                    print(f"❌ Eroare API: {error.get('message')}")
                    print(f"   Code: {error.get('code')}")

                    if 'APP_KEY_CREATION_FAILED' in str(error):
                        print(f"\n💡 Posibil App Keys deja există pentru acest cont.")
                        print(f"   Încearcă să le recuperezi cu get_app_keys()")

                    return None
                else:
                    print(f"❌ Răspuns neașteptat: {data}")
                    return None
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Eroare la creare App Keys: {e}")
            return None

    def get_app_keys(self) -> Optional[Dict]:
        """
        Recuperează App Keys existente
        """
        if not self.ssoid:
            print("❌ Nu există ssoid. Rulează login() mai întâi.")
            return None

        print(f"\n🔍 Recuperare App Keys existente...")

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "AccountAPING/v1.0/getDeveloperAppKeys",
                "params": {},
                "id": 1
            }

            response = self.client.post(
                self.ACCOUNT_API_URL,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Authentication': self.ssoid
                }
            )

            if response.status_code == 200:
                data = response.json()

                if 'result' in data:
                    result = data['result']

                    if not result:
                        print("ℹ️ Nu există App Keys create pentru acest cont.")
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

                    # Return first delayed key
                    for app in result:
                        for version in app.get('appVersions', []):
                            if 'DELAY' in version.get('version', ''):
                                return {
                                    'delayed_app_key': version.get('applicationKey'),
                                    'app_name': app.get('appName'),
                                    'result': result
                                }

                    return None
                else:
                    print(f"❌ Răspuns neașteptat: {data}")
                    return None
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Eroare la recuperare App Keys: {e}")
            return None

    def close(self):
        """Închide conexiunea HTTP"""
        self.client.close()


def main():
    """Main function"""
    print("=" * 80)
    print("🔑 BETFAIR DELAYED APP KEY GENERATOR")
    print("=" * 80)
    print()

    # Credențiale
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
        app_name = sys.argv[3] if len(sys.argv) >= 4 else "BetixApp"
    else:
        print("Usage: python generate_delayed_app_key.py <username> <password> [app_name]")
        print()
        print("Exemplu:")
        print("  python generate_delayed_app_key.py user@email.com mypassword BetixOctavian")
        sys.exit(1)

    generator = BetfairAppKeyGenerator(username, password)

    try:
        # Step 1: Login
        if not generator.login():
            print("\n❌ Login eșuat. Verifică credențialele.")
            sys.exit(1)

        # Step 2: Încearcă să recuperezi App Keys existente
        existing_keys = generator.get_app_keys()

        if existing_keys:
            print(f"\n✅ DELAYED APP KEY GĂSIT:")
            print(f"   {existing_keys['delayed_app_key']}")
            print(f"\n💾 Salvează acest App Key pentru BETIX!")
        else:
            # Step 3: Creează App Keys noi
            print(f"\nℹ️ Nu există App Keys. Creăm unele noi...")
            result = generator.create_app_keys(app_name)

            if result:
                print(f"\n✅ DELAYED APP KEY CREAT:")
                print(f"   {result['delayed_app_key']}")
                print(f"\n💾 Salvează acest App Key pentru BETIX!")
            else:
                print("\n❌ Nu s-au putut crea App Keys.")
                sys.exit(1)

    finally:
        generator.close()

    print("\n" + "=" * 80)
    print("✅ Script finalizat!")
    print("=" * 80)


if __name__ == "__main__":
    main()
