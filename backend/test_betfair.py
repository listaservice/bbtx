"""
Test Betfair API connection
"""
import asyncio
from app.services.betfair_client import betfair_client

async def test_betfair():
    """Test Betfair connection"""
    print("🔍 Testing Betfair API connection...")
    print("")

    try:
        # Connect to Betfair
        print("1. Connecting to Betfair...")
        await betfair_client.connect()
        print("   ✅ Connected successfully!")
        if hasattr(betfair_client, 'session_token') and betfair_client.session_token:
            print(f"   Session Token: {betfair_client.session_token[:20]}...")
        print("")

        # List football events
        print("2. Fetching football events...")
        events = await betfair_client.list_events(event_type_id="1")  # 1 = Football

        if events:
            print(f"   ✅ Found {len(events)} football events")
            print("")
            print("   📊 First 5 events:")
            for i, event in enumerate(events[:5], 1):
                event_name = event.get('event', {}).get('name', 'Unknown')
                competition = event.get('competition', {}).get('name', 'Unknown')
                market_count = event.get('marketCount', 0)
                print(f"   {i}. {event_name}")
                print(f"      Competition: {competition}")
                print(f"      Markets: {market_count}")
                print("")
        else:
            print("   ⚠️ No events found")

        print("✅ Betfair API is working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_betfair())
