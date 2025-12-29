"""
Script pentru verificare pariuri active prin Betfair API
Afișează toate pariurile PENDING/EXECUTABLE pentru Octavian
"""
import sys
import os
import asyncio
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.betfair_client import BetfairClient
from app.services.encryption import encryption_service
from app.database import SessionLocal
from app.models.user import User
from app.models.betfair_credentials import BetfairCredentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_user_credentials(email: str):
    """Get user and decrypt Betfair credentials"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.error(f"User {email} not found")
            return None, None

        credentials = db.query(BetfairCredentials).filter(
            BetfairCredentials.user_id == user.id
        ).first()

        if not credentials:
            logger.error(f"No Betfair credentials found for {email}")
            return None, None

        # Decrypt credentials
        app_key = encryption_service.decrypt(credentials.app_key_encrypted)
        username = encryption_service.decrypt(credentials.username_encrypted)
        password = encryption_service.decrypt(credentials.password_encrypted)

        return user, {
            'app_key': app_key,
            'username': username,
            'password': password
        }
    finally:
        db.close()


async def check_active_bets(betfair_client: BetfairClient):
    """
    Check all active bets via Betfair API

    Returns:
        List of active bets
    """
    try:
        logger.info("Querying Betfair API for active bets...")

        # Use the correct method from BetfairClient
        current_orders = await betfair_client.get_current_orders()

        logger.info(f"Found {len(current_orders)} active bets")

        return current_orders

    except Exception as e:
        logger.error(f"Error checking active bets: {e}")
        return []


async def main():
    """Main function to check active bets"""
    email = "Octavianmatei1990@gmail.com"

    logger.info(f"Checking active bets for {email}...")

    # Get user and credentials
    user, credentials = await get_user_credentials(email)
    if not user or not credentials:
        logger.error("Failed to get user credentials")
        return

    logger.info(f"User found: {user.email}")

    # Initialize Betfair client
    betfair_client = BetfairClient()
    betfair_client.configure(
        app_key=credentials['app_key'],
        username=credentials['username'],
        password=credentials['password'],
        use_env_fallback=False
    )

    # Connect to Betfair
    await betfair_client.connect()
    if not betfair_client.is_connected():
        logger.error("Failed to connect to Betfair")
        return

    logger.info("✅ Connected to Betfair")

    # Get active bets
    active_bets = await check_active_bets(betfair_client)

    if not active_bets:
        logger.info("No active bets found")
        await betfair_client.disconnect()
        return

    # Display bet details
    logger.info(f"\n{'='*80}")
    logger.info(f"ACTIVE BETS SUMMARY - {email}")
    logger.info(f"{'='*80}\n")

    total_stake = 0
    total_liability = 0

    for idx, bet in enumerate(active_bets, 1):
        bet_id = bet.get("betId", "N/A")
        market_id = bet.get("marketId", "N/A")
        selection_id = bet.get("selectionId", "N/A")
        side = bet.get("side", "N/A")
        status = bet.get("status", "N/A")
        price_matched = bet.get("priceMatched", 0)
        size_matched = bet.get("sizeMatched", 0)
        placed_date = bet.get("placedDate", "N/A")

        # Calculate stake/liability
        if side == "BACK":
            stake = size_matched
            liability = 0
        else:  # LAY
            stake = 0
            liability = size_matched * (price_matched - 1)

        total_stake += stake
        total_liability += liability

        logger.info(f"Bet #{idx}:")
        logger.info(f"  Bet ID: {bet_id}")
        logger.info(f"  Market ID: {market_id}")
        logger.info(f"  Selection ID: {selection_id}")
        logger.info(f"  Side: {side}")
        logger.info(f"  Status: {status}")
        logger.info(f"  Price: {price_matched}")
        logger.info(f"  Size: {size_matched} RON")
        logger.info(f"  Stake: {stake:.2f} RON")
        logger.info(f"  Liability: {liability:.2f} RON")
        logger.info(f"  Placed: {placed_date}")
        logger.info("")

    logger.info(f"{'='*80}")
    logger.info(f"TOTAL ACTIVE BETS: {len(active_bets)}")
    logger.info(f"TOTAL STAKE: {total_stake:.2f} RON")
    logger.info(f"TOTAL LIABILITY: {total_liability:.2f} RON")
    logger.info(f"{'='*80}\n")

    # Cleanup
    await betfair_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
