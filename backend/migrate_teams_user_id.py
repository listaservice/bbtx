"""
Migration: Add user_id to teams table
"""
from sqlalchemy import create_engine, text
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def migrate():
    """Add user_id column to teams table"""
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        try:
            # Add user_id column
            logger.info("Adding user_id column to teams table...")
            conn.execute(text("""
                ALTER TABLE teams
                ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE
            """))
            conn.commit()
            logger.info("✅ Added user_id column")

            # Get admin user ID (pentru echipele existente)
            result = conn.execute(text("""
                SELECT id FROM users WHERE email = 'admin@betix.ro' LIMIT 1
            """))
            admin_user = result.fetchone()

            if admin_user:
                admin_id = admin_user[0]
                logger.info(f"Found admin user: {admin_id}")

                # Update existing teams to belong to admin
                logger.info("Updating existing teams to admin user...")
                conn.execute(text("""
                    UPDATE teams
                    SET user_id = :admin_id
                    WHERE user_id IS NULL
                """), {"admin_id": admin_id})
                conn.commit()
                logger.info("✅ Updated existing teams")

            # Make user_id NOT NULL
            logger.info("Making user_id NOT NULL...")
            conn.execute(text("""
                ALTER TABLE teams
                ALTER COLUMN user_id SET NOT NULL
            """))
            conn.commit()
            logger.info("✅ Made user_id NOT NULL")

            # Create index for faster queries
            logger.info("Creating index on user_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_teams_user_id ON teams(user_id)
            """))
            conn.commit()
            logger.info("✅ Created index")

            logger.info("🎉 Migration completed successfully!")

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
