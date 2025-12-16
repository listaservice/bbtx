"""
Migrează date din Google Sheets în Database
Rulează o singură dată după deployment pentru a sincroniza datele existente

Usage:
    python migrate_sheets_to_db.py
"""
from sqlalchemy import create_engine, text
from app.config import get_settings
from app.services.google_sheets_multi import google_sheets_multi_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def migrate():
    """Migrează date din Google Sheets în Database"""
    engine = create_engine(settings.database_url)

    logger.info("=" * 80)
    logger.info("🔄 Starting migration from Google Sheets to Database")
    logger.info("=" * 80)

    with engine.connect() as conn:
        # Get all users with google_sheets_id
        users = conn.execute(text("""
            SELECT id, email, google_sheets_id
            FROM users
            WHERE google_sheets_id IS NOT NULL
        """))

        total_users = 0
        total_teams_migrated = 0

        for user in users:
            total_users += 1
            logger.info(f"\n📋 Migrating data for {user.email}")
            logger.info(f"   Spreadsheet ID: {user.google_sheets_id}")

            try:
                # Get teams from database
                teams = conn.execute(text("""
                    SELECT id, name FROM teams WHERE user_id = :user_id
                """), {"user_id": user.id})

                teams_count = 0
                for team in teams:
                    try:
                        # Load from Google Sheets
                        team_data = google_sheets_multi_service.load_team(
                            user.google_sheets_id,
                            team.name
                        )

                        if team_data:
                            # Update database with data from sheets
                            conn.execute(text("""
                                UPDATE teams
                                SET cumulative_loss = :cumulative_loss,
                                    progression_step = :progression_step,
                                    initial_stake = :initial_stake,
                                    last_stake = :last_stake,
                                    updated_at = NOW()
                                WHERE id = :team_id
                            """), {
                                "team_id": team.id,
                                "cumulative_loss": float(team_data.get("cumulative_loss", 0)),
                                "progression_step": int(team_data.get("progression_step", 0)),
                                "initial_stake": float(team_data.get("initial_stake", 100)),
                                "last_stake": float(team_data.get("last_stake", 100))
                            })

                            teams_count += 1
                            total_teams_migrated += 1
                            logger.info(f"   ✅ Migrated {team.name}")
                            logger.info(f"      - cumulative_loss: {team_data.get('cumulative_loss', 0)}")
                            logger.info(f"      - progression_step: {team_data.get('progression_step', 0)}")
                            logger.info(f"      - initial_stake: {team_data.get('initial_stake', 100)}")
                        else:
                            logger.warning(f"   ⚠️  Team {team.name} not found in Google Sheets")

                    except Exception as e:
                        logger.error(f"   ❌ Error migrating team {team.name}: {e}")
                        continue

                conn.commit()
                logger.info(f"   ✅ Migrated {teams_count} teams for {user.email}")

            except Exception as e:
                logger.error(f"   ❌ Error processing user {user.email}: {e}")
                conn.rollback()
                continue

    logger.info("\n" + "=" * 80)
    logger.info(f"✅ Migration completed!")
    logger.info(f"   Total users processed: {total_users}")
    logger.info(f"   Total teams migrated: {total_teams_migrated}")
    logger.info("=" * 80)

    logger.info("\n📝 IMPORTANT:")
    logger.info("   - Database is now the source of truth")
    logger.info("   - Google Sheets will be updated from database going forward")
    logger.info("   - You can now run the application normally")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        exit(1)
