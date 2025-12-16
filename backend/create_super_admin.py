"""
Create super admin user with unlimited access
"""
from app.database import SessionLocal
from app.services.auth_service import auth_service
from app.models.user import User
from datetime import datetime, timedelta

def create_super_admin():
    """Create super admin user"""
    print("🔧 Creating super admin...")

    db = SessionLocal()

    try:
        # Admin credentials
        email = "admin@betix.ro"
        password = "admin123"
        full_name = "Super Admin"

        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == email).first()

        if existing_admin:
            print(f"⚠️  Admin {email} already exists!")
            print(f"   Updating to super admin privileges...")

            # Update existing admin
            existing_admin.subscription_plan = "premium"
            existing_admin.subscription_status = "active"
            existing_admin.max_teams = -1  # Unlimited
            existing_admin.is_verified = True
            existing_admin.subscription_ends_at = datetime.utcnow() + timedelta(days=36500)  # 100 years
            existing_admin.trial_ends_at = None

            db.commit()
            print(f"   ✅ Updated {email} to super admin")
        else:
            # Create new super admin
            print(f"   Creating new admin: {email}")

            user = auth_service.create_user(
                db=db,
                email=email,
                password=password,
                full_name=full_name
            )

            # Upgrade to super admin
            user.subscription_plan = "premium"
            user.subscription_status = "active"
            user.max_teams = -1  # Unlimited teams
            user.is_verified = True
            user.subscription_ends_at = datetime.utcnow() + timedelta(days=36500)  # 100 years
            user.trial_ends_at = None

            db.commit()
            db.refresh(user)

            print(f"   ✅ Super admin created!")

        print("")
        print("=" * 60)
        print("🎉 SUPER ADMIN CREDENTIALS")
        print("=" * 60)
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print(f"   Plan:     Premium (Unlimited)")
        print(f"   Teams:    Unlimited (-1)")
        print(f"   Status:   Active (100 years)")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
