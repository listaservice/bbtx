"""
Test Google Sheets multi-user service
"""
from app.services.google_sheets_multi import google_sheets_multi_service

def test_create_spreadsheet():
    """Test creating a spreadsheet for a user"""
    print("🔍 Testing Google Sheets multi-user service...")
    print("")

    try:
        # Test user
        test_email = "admin@betix.com"
        test_user_id = "test-user-123"

        print(f"1. Creating spreadsheet for: {test_email}")
        spreadsheet_id = google_sheets_multi_service.create_user_spreadsheet(
            user_email=test_email,
            user_id=test_user_id
        )

        print(f"   ✅ Spreadsheet created!")
        print(f"   Spreadsheet ID: {spreadsheet_id}")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print("")

        # Test adding a team sheet
        print("2. Adding team sheet...")
        success = google_sheets_multi_service.add_team_sheet(
            spreadsheet_id=spreadsheet_id,
            team_name="Barcelona"
        )

        if success:
            print("   ✅ Team sheet 'Barcelona' created!")
        print("")

        # Test updating team in Index
        print("3. Adding team to Index...")
        team_data = {
            'id': 'team-001',
            'name': 'Barcelona',
            'betfair_id': '12345',
            'sport': 'Football',
            'league': 'La Liga',
            'country': 'Spain',
            'cumulative_loss': 0,
            'last_stake': 0,
            'progression_step': 0,
            'status': 'active',
            'initial_stake': 100
        }

        success = google_sheets_multi_service.update_team_in_index(
            spreadsheet_id=spreadsheet_id,
            team_id='team-001',
            team_data=team_data
        )

        if success:
            print("   ✅ Team added to Index!")
        print("")

        print("✅ Google Sheets multi-user service is working!")
        print("")
        print(f"🔗 Open spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_create_spreadsheet()
