"""
Setup spreadsheet structure for testing
"""
from app.services.google_sheets_multi import google_sheets_multi_service
from app.config import get_settings

settings = get_settings()

def setup_spreadsheet():
    """Setup spreadsheet structure"""
    print("🔧 Setting up spreadsheet structure...")
    print("")

    spreadsheet_id = settings.google_sheets_spreadsheet_id

    try:
        spreadsheet = google_sheets_multi_service.get_spreadsheet(spreadsheet_id)
        print(f"📊 Spreadsheet: {spreadsheet.title}")
        print(f"🔗 URL: {spreadsheet.url}")
        print("")

        # Setup Index sheet
        print("1. Setting up Index sheet...")
        try:
            # Try to get Index sheet
            index_sheet = spreadsheet.worksheet("Index")
            print("   ✅ Index sheet already exists")
        except:
            # Rename Sheet1 to Index or create new
            try:
                sheet1 = spreadsheet.sheet1
                sheet1.update_title("Index")
                index_sheet = sheet1
                print("   ✅ Renamed Sheet1 to Index")
            except:
                index_sheet = spreadsheet.add_worksheet(title="Index", rows=1000, cols=20)
                print("   ✅ Created Index sheet")

        # Setup headers
        headers = [
            "id",
            "name",
            "betfair_id",
            "sport",
            "league",
            "country",
            "cumulative_loss",
            "last_stake",
            "progression_step",
            "status",
            "created_at",
            "updated_at",
            "initial_stake"
        ]

        index_sheet.update('A1:M1', [headers])

        # Format header
        index_sheet.format('A1:M1', {
            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
        })

        print("   ✅ Headers configured")
        print("")

        # Add example team
        print("2. Adding example team...")
        team_data = {
            'id': 'team-test-001',
            'name': 'Barcelona',
            'betfair_id': '12345',
            'sport': 'Football',
            'league': 'La Liga',
            'country': 'Spain',
            'cumulative_loss': 0,
            'last_stake': 0,
            'progression_step': 0,
            'status': 'active',
            'created_at': '2025-11-30',
            'updated_at': '2025-11-30',
            'initial_stake': 100
        }

        google_sheets_multi_service.update_team_in_index(
            spreadsheet_id=spreadsheet_id,
            team_id='team-test-001',
            team_data=team_data
        )

        print("   ✅ Example team added to Index")
        print("")

        # Create team sheet
        print("3. Creating team sheet...")
        google_sheets_multi_service.add_team_sheet(
            spreadsheet_id=spreadsheet_id,
            team_name="Barcelona"
        )
        print("   ✅ Barcelona sheet created")
        print("")

        print("✅ Spreadsheet setup complete!")
        print(f"🔗 Open: {spreadsheet.url}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_spreadsheet()
