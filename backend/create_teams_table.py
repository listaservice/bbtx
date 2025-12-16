"""
Create teams table with user_id
"""
from sqlalchemy import create_engine, text
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def create_table():
    """Create teams table"""
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        try:
            logger.info("Creating teams table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS teams (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    betfair_id VARCHAR(255),
                    sport VARCHAR(50) DEFAULT 'football',
                    league VARCHAR(255),
                    country VARCHAR(100),
                    cumulative_loss FLOAT DEFAULT 0.0,
                    last_stake FLOAT DEFAULT 10.0,
                    progression_step INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("✅ Created teams table")

            # Create indexes
            logger.info("Creating indexes...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_teams_user_id ON teams(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_teams_status ON teams(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_teams_user_status ON teams(user_id, status)
            """))
            conn.commit()
            logger.info("✅ Created indexes")

            logger.info("🎉 Teams table created successfully!")

        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    create_table()
