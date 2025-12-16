"""
Test trial system
"""
from app.database import SessionLocal
from app.models.user import User
from app.services.trial_service import trial_service

def test_trial():
    """Test trial functionality"""
    print("🧪 Testing trial system...")
    print("")

    db = SessionLocal()

    try:
        # Get admin user
        user = db.query(User).filter(User.email == "admin@betix.com").first()

        if not user:
            print("❌ User not found")
            return

        print(f"👤 User: {user.email}")
        print(f"   Plan: {user.subscription_plan}")
        print(f"   Status: {user.subscription_status}")
        print(f"   Max Teams: {user.max_teams}")
        print(f"   Trial Ends: {user.trial_ends_at}")
        print("")

        # Check if expired
        is_expired = trial_service.check_trial_expired(user)
        print(f"🕐 Trial Expired: {is_expired}")

        # Days remaining
        days = trial_service.get_trial_days_remaining(user)
        print(f"📅 Days Remaining: {days}")
        print("")

        if days > 0:
            print(f"✅ Trial active for {days} more days!")
        else:
            print("⚠️ Trial expired!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_trial()
