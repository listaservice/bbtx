"""
Migration: Add subscription_ends_at column
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.user import User
from datetime import datetime, timedelta

def migrate():
    """Add subscription_ends_at column"""
    print("🔄 Adding subscription_ends_at column...")

    db = SessionLocal()

    try:
        # Add column
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMP WITHOUT TIME ZONE
            """))
            conn.commit()
        print("   ✅ Column added")

        # Update existing users
        print("📝 Updating existing users...")
        users = db.query(User).all()

        for user in users:
            if user.subscription_status == "trial" and user.subscription_plan == "demo":
                # Demo: subscription_ends_at = trial_ends_at
                user.subscription_ends_at = user.trial_ends_at
                print(f"   ✅ {user.email}: demo trial ends {user.subscription_ends_at}")

            elif user.subscription_status == "active":
                # Active paid: 30 days from now
                user.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
                print(f"   ✅ {user.email}: {user.subscription_plan} ends {user.subscription_ends_at}")

        db.commit()
        print(f"✅ Migration complete! Updated {len(users)} users")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
