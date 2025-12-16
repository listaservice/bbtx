"""
Script to create admin user
Run: python create_admin.py
"""
from app.database import SessionLocal
from app.services.auth_service import auth_service

def create_admin_user():
    """Create admin user"""
    db = SessionLocal()

    try:
        # Admin credentials
        email = "admin@betix.com"
        password = "admin123"
        full_name = "Admin User"

        print(f"Creating admin user: {email}")

        # Check if user already exists
        from app.models.user import User
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            print(f"❌ User {email} already exists!")
            print(f"   User ID: {existing_user.id}")
            return

        # Create user
        user = auth_service.create_user(
            db=db,
            email=email,
            password=password,
            full_name=full_name
        )

        print(f"✅ Admin user created successfully!")
        print(f"   User ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Password: {password}")
        print(f"\n🔑 Login credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
