"""
Migration script to add trial_ends_at column and update existing users
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.user import User
from datetime import datetime, timedelta

def migrate():
    """Add trial_ends_at column and update existing users"""
    print("🔄 Starting migration...")

    db = SessionLocal()

    try:
        # Add column if not exists
        print("1. Adding trial_ends_at column...")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP WITHOUT TIME ZONE
            """))
            conn.commit()
        print("   ✅ Column added")

        # Update existing users
        print("2. Updating existing users...")
        users = db.query(User).all()

        for user in users:
            if user.subscription_status == "inactive":
                # Convert to trial with 3 days
                user.subscription_plan = "demo"
                user.subscription_status = "trial"
                user.max_teams = 5
                user.trial_ends_at = datetime.utcnow() + timedelta(days=10)
                print(f"   ✅ Updated {user.email} to trial (10 days)")

        db.commit()
        print(f"   ✅ Updated {len(users)} users")

        print("✅ Migration complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
