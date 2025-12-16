"""
Test Google Sheets with existing spreadsheet (no Drive API needed)
"""
from app.services.google_sheets_multi import google_sheets_multi_service
from app.config import get_settings

settings = get_settings()

def test_existing_spreadsheet():
    """Test using existing spreadsheet"""
    print("🔍 Testing Google Sheets with existing spreadsheet...")
    print("")

    # Use existing spreadsheet from VPS
    spreadsheet_id = settings.google_sheets_spreadsheet_id

    if not spreadsheet_id or spreadsheet_id == "your_test_spreadsheet_id":
        print("❌ No spreadsheet ID configured in .env")
        print("   Set GOOGLE_SHEETS_SPREADSHEET_ID in backend/.env")
        return

    try:
        print(f"1. Opening existing spreadsheet: {spreadsheet_id}")
        spreadsheet = google_sheets_multi_service.get_spreadsheet(spreadsheet_id)
        print(f"   ✅ Spreadsheet opened: {spreadsheet.title}")
        print(f"   URL: {spreadsheet.url}")
        print("")

        # Test adding a team sheet
        print("2. Adding test team sheet...")
        test_team = "Test_Team_Local"
        success = google_sheets_multi_service.add_team_sheet(
            spreadsheet_id=spreadsheet_id,
            team_name=test_team
        )

        if success:
            print(f"   ✅ Team sheet '{test_team}' created!")
        print("")

        print("✅ Google Sheets service is working!")
        print(f"🔗 Open spreadsheet: {spreadsheet.url}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_existing_spreadsheet()
