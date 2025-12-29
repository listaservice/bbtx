"""
Script pentru cashout automat la toate pariurile PENDING ale lui Octavian
Folosește Betfair API pentru a face cashout la pariurile active
"""
import sys
import os
import asyncio
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.betfair_client import BetfairClient
from app.services.google_sheets_multi import google_sheets_multi_service
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


async def get_pending_bets(spreadsheet_id: str):
    """Get all pending bets from Google Sheets"""
    pending_bets = google_sheets_multi_service.get_pending_bets(spreadsheet_id)
    return pending_bets


async def cashout_bet(betfair_client: BetfairClient, bet_id: str, team_name: str):
    """
    Cashout a single bet using Betfair API

    Args:
        betfair_client: Authenticated Betfair client
        bet_id: Betfair bet ID
        team_name: Team name for logging

    Returns:
        dict with success status and cashout amount
    """
    try:
        # Get current bet status and cashout value
        logger.info(f"Getting cashout value for bet {bet_id} ({team_name})...")

        # Call Betfair API to list current orders
        response = await betfair_client._call_api(
            "listCurrentOrders",
            {
                "betIds": [bet_id]
            }
        )

        if not response or "currentOrders" not in response:
            logger.error(f"Failed to get bet info for {bet_id}")
            return {"success": False, "error": "Failed to get bet info"}

        current_orders = response.get("currentOrders", [])
        if not current_orders:
            logger.warning(f"Bet {bet_id} not found or already settled")
            return {"success": False, "error": "Bet not found"}

        bet = current_orders[0]
        bet_status = bet.get("status")

        if bet_status != "EXECUTABLE":
            logger.warning(f"Bet {bet_id} status is {bet_status}, cannot cashout")
            return {"success": False, "error": f"Bet status: {bet_status}"}

        # Get market ID and selection ID
        market_id = bet.get("marketId")
        selection_id = bet.get("selectionId")
        size_matched = bet.get("sizeMatched", 0)
        price_matched = bet.get("priceMatched", 0)
        side = bet.get("side")  # BACK or LAY

        logger.info(f"Bet details: Market={market_id}, Selection={selection_id}, Size={size_matched}, Price={price_matched}, Side={side}")

        # Get current market prices to calculate cashout
        market_book = await betfair_client.list_market_book([market_id])

        if not market_book or not market_book[0].get("runners"):
            logger.error(f"Failed to get market prices for {market_id}")
            return {"success": False, "error": "Failed to get market prices"}

        # Find runner with our selection ID
        runners = market_book[0].get("runners", [])
        runner = next((r for r in runners if r.get("selectionId") == selection_id), None)

        if not runner:
            logger.error(f"Selection {selection_id} not found in market")
            return {"success": False, "error": "Selection not found"}

        # Get current back/lay prices
        ex = runner.get("ex", {})
        available_to_back = ex.get("availableToBack", [])
        available_to_lay = ex.get("availableToLay", [])

        if not available_to_back or not available_to_lay:
            logger.error(f"No prices available for selection {selection_id}")
            return {"success": False, "error": "No prices available"}

        current_back_price = available_to_back[0].get("price", 0)
        current_lay_price = available_to_lay[0].get("price", 0)

        logger.info(f"Current prices: Back={current_back_price}, Lay={current_lay_price}")

        # Calculate cashout by placing opposite bet
        if side == "BACK":
            # We backed, now we need to LAY to cashout
            cashout_price = current_lay_price
            cashout_side = "LAY"
        else:
            # We laid, now we need to BACK to cashout
            cashout_price = current_back_price
            cashout_side = "BACK"

        # Calculate cashout size to close position
        cashout_size = size_matched

        logger.info(f"Placing cashout bet: {cashout_side} {cashout_size} @ {cashout_price}")

        # Place opposite bet to cashout
        cashout_response = await betfair_client._call_api(
            "placeOrders",
            {
                "marketId": market_id,
                "instructions": [
                    {
                        "selectionId": selection_id,
                        "handicap": 0,
                        "side": cashout_side,
                        "orderType": "LIMIT",
                        "limitOrder": {
                            "size": cashout_size,
                            "price": cashout_price,
                            "persistenceType": "LAPSE"
                        }
                    }
                ]
            }
        )

        if not cashout_response or cashout_response.get("status") != "SUCCESS":
            error = cashout_response.get("errorCode", "Unknown error") if cashout_response else "No response"
            logger.error(f"Failed to place cashout bet: {error}")
            return {"success": False, "error": f"Cashout failed: {error}"}

        instruction_reports = cashout_response.get("instructionReports", [])
        if not instruction_reports or instruction_reports[0].get("status") != "SUCCESS":
            error = instruction_reports[0].get("errorCode", "Unknown") if instruction_reports else "No report"
            logger.error(f"Cashout instruction failed: {error}")
            return {"success": False, "error": f"Instruction failed: {error}"}

        cashout_bet_id = instruction_reports[0].get("betId")

        # Calculate profit/loss
        if side == "BACK":
            # Original BACK bet profit if wins: size_matched * (price_matched - 1)
            # Cashout LAY bet loss if wins: cashout_size * (cashout_price - 1)
            # Net profit: size_matched * (price_matched - 1) - cashout_size * (cashout_price - 1)
            profit_if_wins = size_matched * (price_matched - 1) - cashout_size * (cashout_price - 1)
            loss_if_loses = -size_matched + cashout_size
        else:
            # Original LAY bet profit if loses: size_matched
            # Cashout BACK bet loss if loses: cashout_size * (cashout_price - 1)
            profit_if_wins = size_matched - cashout_size * (cashout_price - 1)
            loss_if_loses = -size_matched * (price_matched - 1) + cashout_size

        guaranteed_profit = min(profit_if_wins, loss_if_loses)

        logger.info(f"✅ Cashout successful! Bet ID: {cashout_bet_id}")
        logger.info(f"Guaranteed profit: {guaranteed_profit:.2f} RON")

        return {
            "success": True,
            "cashout_bet_id": cashout_bet_id,
            "guaranteed_profit": guaranteed_profit,
            "original_bet_id": bet_id
        }

    except Exception as e:
        logger.error(f"Error cashing out bet {bet_id}: {e}")
        return {"success": False, "error": str(e)}


async def main():
    """Main function to cashout all Octavian's pending bets"""
    email = "Octavianmatei1990@gmail.com"

    logger.info(f"Starting cashout process for {email}...")

    # Get user and credentials
    user, credentials = await get_user_credentials(email)
    if not user or not credentials:
        logger.error("Failed to get user credentials")
        return

    logger.info(f"User found: {user.email}")
    logger.info(f"Google Sheets ID: {user.google_sheets_id}")

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

    # Get pending bets from Google Sheets
    pending_bets = await get_pending_bets(user.google_sheets_id)

    if not pending_bets:
        logger.info("No pending bets found")
        return

    logger.info(f"Found {len(pending_bets)} pending bets")

    # Cashout each bet
    results = []
    total_profit = 0

    for bet in pending_bets:
        team_name = bet.get("team_name", "Unknown")
        bet_id = bet.get("Bet ID", "")
        match_name = bet.get("Meci", "")
        stake = bet.get("Miză", "")

        if not bet_id:
            logger.warning(f"Skipping bet for {team_name} - no Bet ID")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {team_name} - {match_name}")
        logger.info(f"Stake: {stake} RON, Bet ID: {bet_id}")

        result = await cashout_bet(betfair_client, bet_id, team_name)
        results.append({
            "team": team_name,
            "match": match_name,
            "bet_id": bet_id,
            **result
        })

        if result["success"]:
            profit = result.get("guaranteed_profit", 0)
            total_profit += profit
            logger.info(f"✅ Cashout successful: {profit:.2f} RON")
        else:
            logger.error(f"❌ Cashout failed: {result.get('error', 'Unknown error')}")

        # Wait 1 second between requests
        await asyncio.sleep(1)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("CASHOUT SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total bets processed: {len(results)}")
    logger.info(f"Successful cashouts: {sum(1 for r in results if r['success'])}")
    logger.info(f"Failed cashouts: {sum(1 for r in results if not r['success'])}")
    logger.info(f"Total guaranteed profit: {total_profit:.2f} RON")
    logger.info(f"{'='*60}")

    # Cleanup
    await betfair_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
