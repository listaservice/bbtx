#!/usr/bin/env python3
"""
Script pentru verificare și fix permisiuni Google Sheets
"""
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def check_and_fix_permissions(spreadsheet_id):
    """Verifică și fixează permisiunile pentru un spreadsheet"""

    # Initialize credentials
    creds = Credentials.from_service_account_file(
        './credentials/google_service_account.json',
        scopes=SCOPES
    )

    drive_service = build('drive', 'v3', credentials=creds)

    # Get current permissions
    print(f"\n🔍 Verificare permisiuni pentru spreadsheet: {spreadsheet_id}")
    permissions = drive_service.permissions().list(
        fileId=spreadsheet_id,
        fields='permissions(id,type,role,emailAddress)'
    ).execute()

    print("\n📋 Permisiuni actuale:")
    has_anyone_writer = False
    for perm in permissions.get('permissions', []):
        perm_type = perm.get('type')
        perm_role = perm.get('role')
        perm_email = perm.get('emailAddress', 'N/A')
        print(f"  - Type: {perm_type}, Role: {perm_role}, Email: {perm_email}")

        if perm_type == 'anyone' and perm_role == 'writer':
            has_anyone_writer = True

    # Add "anyone with link" permission if missing
    if not has_anyone_writer:
        print("\n⚠️  Permisiunea 'anyone with link' (writer) LIPSEȘTE!")
        print("🔧 Adăugare permisiune...")

        try:
            drive_service.permissions().create(
                fileId=spreadsheet_id,
                body={
                    'type': 'anyone',
                    'role': 'writer'
                }
            ).execute()
            print("✅ Permisiune 'anyone with link' (writer) adăugată cu succes!")
        except Exception as e:
            print(f"❌ Eroare la adăugare permisiune: {e}")
    else:
        print("\n✅ Permisiunea 'anyone with link' (writer) există deja!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 fix_permissions.py <spreadsheet_id>")
        sys.exit(1)

    spreadsheet_id = sys.argv[1]
    check_and_fix_permissions(spreadsheet_id)
