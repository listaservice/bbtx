"""
Multi-User Scheduler - Rulează bot-ul pentru toți userii activi
"""
import logging
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy import create_engine, text

from app.models.user import User
from app.services.user_bot_service import UserBotService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MultiUserScheduler:
    """
    Scheduler care rulează bot-ul pentru toți userii activi.
    Execută în paralel cu limit controlat (max 5 useri simultan).
    """

    def __init__(self):
        self.engine = create_engine(settings.database_url)
        self.max_concurrent_users = 5  # Max 5 useri simultan
        self.delay_between_batches = 10  # 10 secunde între batch-uri

    def get_active_users(self) -> List[User]:
        """
        Query useri activi care pot rula bot-ul:
        - subscription_status = 'active' sau 'trial'
        - subscription_ends_at > NOW()
        - is_active = true
        - au betfair_credentials
        - au cel puțin 1 team activ
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT u.*
                FROM users u
                INNER JOIN betfair_credentials bc ON u.id = bc.user_id
                INNER JOIN teams t ON u.id = t.user_id
                WHERE u.is_active = true
                  AND u.subscription_status IN ('active', 'trial')
                  AND u.subscription_ends_at > NOW()
                  AND t.status = 'active'
                ORDER BY u.created_at ASC
            """))

            users = []
            for row in result:
                user = User(
                    id=row.id,
                    email=row.email,
                    password_hash=row.password_hash,
                    is_active=row.is_active,
                    is_verified=row.is_verified,
                    full_name=row.full_name,
                    subscription_plan=row.subscription_plan,
                    subscription_status=row.subscription_status,
                    max_teams=row.max_teams,
                    google_sheets_id=row.google_sheets_id,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    last_login=row.last_login,
                    trial_ends_at=row.trial_ends_at,
                    subscription_ends_at=row.subscription_ends_at
                )
                users.append(user)

            return users

    async def run_for_all_users(self) -> dict:
        """
        Rulează bot-ul pentru toți userii activi.
        Execută în paralel cu limit controlat (max 5 useri simultan).

        Returns:
            dict cu statistici globale
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info(f"🤖 Starting multi-user bot run at {start_time}")
        logger.info(f"🔥 Parallel execution: Max {self.max_concurrent_users} users at once")
        logger.info("=" * 80)

        global_stats = {
            'start_time': start_time.isoformat(),
            'total_users': 0,
            'successful_users': 0,
            'failed_users': 0,
            'total_teams_processed': 0,
            'total_bets_placed': 0,
            'user_results': []
        }

        try:
            # 1. Get active users
            users = self.get_active_users()
            global_stats['total_users'] = len(users)

            if not users:
                logger.info("No active users found")
                return global_stats

            logger.info(f"Found {len(users)} active users")

            # 2. Split în batch-uri de max_concurrent_users
            batches = [
                users[i:i + self.max_concurrent_users]
                for i in range(0, len(users), self.max_concurrent_users)
            ]

            logger.info(f"Split into {len(batches)} batches")

            # 3. Process fiecare batch în paralel
            for batch_idx, batch in enumerate(batches, 1):
                logger.info("-" * 80)
                logger.info(f"🚀 Processing batch {batch_idx}/{len(batches)} ({len(batch)} users)")
                logger.info(f"Users: {', '.join([u.email for u in batch])}")
                logger.info("-" * 80)

                # Run toți userii din batch în paralel
                tasks = [self._run_for_user(user) for user in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect results
                for user, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Exception for {user.email}: {result}")
                        global_stats['user_results'].append({
                            'user_id': user.id,
                            'user_email': user.email,
                            'success': False,
                            'errors': [str(result)]
                        })
                        global_stats['failed_users'] += 1
                    else:
                        global_stats['user_results'].append(result)
                        if result.get('success'):
                            global_stats['successful_users'] += 1
                            global_stats['total_teams_processed'] += result.get('teams_processed', 0)
                            global_stats['total_bets_placed'] += result.get('bets_placed', 0)
                        else:
                            global_stats['failed_users'] += 1

                # Delay între batch-uri (except ultimul)
                if batch_idx < len(batches):
                    logger.info(f"⏳ Waiting {self.delay_between_batches}s before next batch...")
                    await asyncio.sleep(self.delay_between_batches)

            # 4. Final stats
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info(f"✅ Multi-user bot run completed!")
            logger.info(f"Duration: {duration:.2f}s")
            logger.info(f"Users processed: {global_stats['successful_users']}/{global_stats['total_users']}")
            logger.info(f"Teams processed: {global_stats['total_teams_processed']}")
            logger.info(f"Bets placed: {global_stats['total_bets_placed']}")
            logger.info("=" * 80)

            global_stats['end_time'] = end_time.isoformat()
            global_stats['duration_seconds'] = duration

            return global_stats

        except Exception as e:
            logger.error(f"❌ Multi-user bot run failed: {e}")
            global_stats['error'] = str(e)
            return global_stats

    async def _run_for_user(self, user: User) -> dict:
        """
        Rulează bot-ul pentru un singur user.

        Returns:
            dict cu rezultatul pentru acest user
        """
        result = {
            'user_id': user.id,
            'user_email': user.email,
            'success': False,
            'teams_processed': 0,
            'bets_placed': 0,
            'errors': []
        }

        bot_service = None

        try:
            # 1. Create bot service pentru acest user
            bot_service = UserBotService(user)

            # 2. Initialize (load credentials, connect Betfair, etc.)
            initialized = await bot_service.initialize()
            if not initialized:
                result['errors'].append("Failed to initialize bot service")
                return result

            # 3. Run bot
            stats = await bot_service.run_bot()

            result['success'] = True
            result['teams_processed'] = stats.get('teams_processed', 0)
            result['bets_placed'] = stats.get('bets_placed', 0)
            result['errors'] = stats.get('errors', [])

            logger.info(f"✅ Bot completed for {user.email}: {stats}")

        except Exception as e:
            error_msg = f"Bot failed for {user.email}: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        finally:
            # Cleanup
            if bot_service:
                await bot_service.cleanup()

        return result

    async def check_results_for_all_users(self) -> dict:
        """
        Verifică rezultatele pariurilor pentru toți userii activi.
        Rulează separat de run_for_all_users - doar verificare, fără plasare.

        Returns:
            dict cu statistici globale
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info(f"🔍 Starting multi-user results check at {start_time}")
        logger.info("=" * 80)

        global_stats = {
            'start_time': start_time.isoformat(),
            'total_users': 0,
            'successful_users': 0,
            'failed_users': 0,
            'total_won': 0,
            'total_lost': 0,
            'total_still_pending': 0,
            'user_results': []
        }

        try:
            # Get active users
            users = self.get_active_users()
            global_stats['total_users'] = len(users)

            if not users:
                logger.info("No active users found")
                return global_stats

            logger.info(f"Checking results for {len(users)} active users")

            # Split în batch-uri
            batches = [
                users[i:i + self.max_concurrent_users]
                for i in range(0, len(users), self.max_concurrent_users)
            ]

            # Process fiecare batch în paralel
            for batch_idx, batch in enumerate(batches, 1):
                logger.info("-" * 80)
                logger.info(f"🔍 Checking batch {batch_idx}/{len(batches)} ({len(batch)} users)")
                logger.info(f"Users: {', '.join([u.email for u in batch])}")
                logger.info("-" * 80)

                tasks = [self._check_results_for_user(user) for user in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for user, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Exception for {user.email}: {result}")
                        global_stats['user_results'].append({
                            'user_email': user.email,
                            'success': False,
                            'error': str(result)
                        })
                        global_stats['failed_users'] += 1
                    else:
                        global_stats['user_results'].append(result)
                        if result.get('success'):
                            global_stats['successful_users'] += 1
                            global_stats['total_won'] += result.get('won', 0)
                            global_stats['total_lost'] += result.get('lost', 0)
                            global_stats['total_still_pending'] += result.get('still_pending', 0)
                        else:
                            global_stats['failed_users'] += 1

                # Delay între batch-uri
                if batch_idx < len(batches):
                    logger.info(f"⏳ Waiting {self.delay_between_batches}s before next batch...")
                    await asyncio.sleep(self.delay_between_batches)

            # Final stats
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 80)
            logger.info(f"✅ Results check completed!")
            logger.info(f"Duration: {duration:.2f}s")
            logger.info(f"Users processed: {global_stats['successful_users']}/{global_stats['total_users']}")
            logger.info(f"Won: {global_stats['total_won']}, Lost: {global_stats['total_lost']}, Pending: {global_stats['total_still_pending']}")
            logger.info("=" * 80)

            global_stats['end_time'] = end_time.isoformat()
            global_stats['duration_seconds'] = duration

            return global_stats

        except Exception as e:
            logger.error(f"❌ Multi-user results check failed: {e}")
            global_stats['error'] = str(e)
            return global_stats

    async def _check_results_for_user(self, user: User) -> dict:
        """
        Verifică rezultatele pentru un singur user.

        Returns:
            dict cu rezultatul pentru acest user
        """
        result = {
            'user_email': user.email,
            'success': False,
            'won': 0,
            'lost': 0,
            'still_pending': 0,
            'errors': []
        }

        bot_service = None

        try:
            # Create bot service
            bot_service = UserBotService(user)

            # Initialize
            initialized = await bot_service.initialize()
            if not initialized:
                result['errors'].append("Failed to initialize bot service")
                return result

            # Check results
            check_result = await bot_service.check_bet_results()

            result['success'] = True
            result['won'] = check_result.get('won', 0)
            result['lost'] = check_result.get('lost', 0)
            result['still_pending'] = check_result.get('still_pending', 0)
            result['errors'] = check_result.get('errors', [])

            logger.info(f"✅ Results checked for {user.email}: {result['won']} won, {result['lost']} lost")

        except Exception as e:
            error_msg = f"Results check failed for {user.email}: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        finally:
            if bot_service:
                await bot_service.cleanup()

        return result


# Singleton instance
multi_user_scheduler = MultiUserScheduler()
