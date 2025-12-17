"""
User Bot Service - Bot engine per user
Gestionează bot-ul pentru un singur user
"""
import logging
from typing import List, Optional
from datetime import datetime

from app.models.schemas import Team, TeamStatus, TeamUpdate
from app.models.user import User
from app.services.teams_repository import teams_repository
from app.services.betfair_client import BetfairClient
from app.services.google_sheets_multi import GoogleSheetsMultiService
from app.services.encryption import encryption_service
from sqlalchemy import create_engine, text
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserBotService:
    """
    Bot service pentru un singur user.
    Izolează complet operațiile per user.
    """

    def __init__(self, user: User):
        self.user = user
        self.user_id = user.id
        self.betfair_client: Optional[BetfairClient] = None
        self.sheets_client: Optional[GoogleSheetsMultiService] = None
        self.engine = create_engine(settings.database_url)

    async def initialize(self) -> bool:
        """
        Inițializează serviciile pentru acest user:
        - Betfair credentials
        - Google Sheets
        """
        try:
            # 1. Load și decrypt Betfair credentials
            credentials = self._load_betfair_credentials()
            if not credentials:
                logger.warning(f"User {self.user.email} nu are Betfair credentials")
                return False

            # 2. Initialize Betfair client
            self.betfair_client = BetfairClient()
            self.betfair_client.configure(
                app_key=credentials['app_key'],
                username=credentials['username'],
                password=credentials['password']
            )

            # 3. Connect to Betfair
            await self.betfair_client.connect()
            if not self.betfair_client.is_connected():
                logger.error(f"Failed to connect to Betfair for user {self.user.email}")
                return False

            # 4. Initialize Google Sheets
            if self.user.google_sheets_id:
                self.sheets_client = GoogleSheetsMultiService()
                self.spreadsheet_id = self.user.google_sheets_id
            else:
                logger.warning(f"User {self.user.email} nu are Google Sheets ID")
                return False

            logger.info(f"✅ Initialized bot for user {self.user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize bot for user {self.user.email}: {e}")
            return False

    def _load_betfair_credentials(self) -> Optional[dict]:
        """Load și decrypt Betfair credentials pentru acest user"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT username_encrypted, password_encrypted, app_key_encrypted
                FROM betfair_credentials
                WHERE user_id = :user_id
            """), {"user_id": self.user_id})

            row = result.fetchone()
            if not row:
                return None

            try:
                return {
                    'username': encryption_service.decrypt(row.username_encrypted),
                    'password': encryption_service.decrypt(row.password_encrypted),
                    'app_key': encryption_service.decrypt(row.app_key_encrypted)
                }
            except Exception as e:
                logger.error(f"Failed to decrypt credentials for user {self.user.email}: {e}")
                return None

    def get_active_teams(self) -> List[Team]:
        """Get active teams pentru acest user din DATABASE"""
        return teams_repository.get_user_teams(self.user_id, active_only=True)

    async def run_bot(self) -> dict:
        """
        Rulează bot-ul pentru acest user.

        Returns:
            dict cu statistici: teams_processed, bets_placed, errors
        """
        stats = {
            'user_email': self.user.email,
            'teams_processed': 0,
            'bets_placed': 0,
            'errors': []
        }

        try:
            # 1. Get active teams
            teams = self.get_active_teams()
            if not teams:
                logger.info(f"User {self.user.email} nu are echipe active")
                return stats

            logger.info(f"Processing {len(teams)} teams for user {self.user.email}")

            # 2. Process fiecare echipă
            for team in teams:
                try:
                    process_result = await self._process_team(team)
                    stats['teams_processed'] += 1
                    if process_result.get('bet_placed'):
                        stats['bets_placed'] += 1
                except Exception as e:
                    error_msg = f"Error processing team {team.name}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)

            logger.info(f"✅ Bot completed for user {self.user.email}: {stats}")
            return stats

        except Exception as e:
            error_msg = f"Bot failed for user {self.user.email}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats

    async def _process_team(self, team: Team) -> dict:
        """
        Procesează o echipă - LOGICA DIN VPS ADAPTATĂ PER USER:
        1. Verifică dacă are pariu PENDING (skip dacă da)
        2. Citește meciuri programate din Google Sheets
        3. Ia primul meci fără status
        4. Calculează miză Martingale
        5. Găsește meciul pe Betfair (by date + name)
        6. Plasează pariu
        7. Update Google Sheets cu status PENDING

        Returns:
            dict cu 'bet_placed': True/False și alte detalii
        """
        from app.services.staking import staking_service
        from datetime import datetime

        result = {'bet_placed': False, 'team_name': team.name, 'reason': None}
        logger.info(f"Processing team {team.name} for user {self.user.email}")

        try:
            # 1. Verifică dacă echipa are deja un pariu PENDING
            pending_bets = self.sheets_client.get_pending_bets(self.spreadsheet_id, team.name)
            if pending_bets:
                logger.info(f"Skip {team.name} - are deja {len(pending_bets)} pariu(ri) PENDING")
                result['reason'] = 'has_pending_bet'
                return result

            # 2. Get scheduled matches from team's sheet
            scheduled_matches = self.sheets_client.get_scheduled_matches(self.spreadsheet_id, team.name)

            if not scheduled_matches:
                logger.info(f"Nu există meciuri programate pentru {team.name}")
                result['reason'] = 'no_scheduled_matches'
                return result

            # 3. Sort matches by date and take only the first one (closest date)
            sorted_matches = sorted(scheduled_matches, key=lambda x: x.get("Data", ""))
            match = sorted_matches[0] if sorted_matches else None

            if not match:
                result['reason'] = 'no_match_found'
                return result

            event_name = match.get("Meci", "")
            match_date_str = match.get("Data", "")  # Format: 2025-11-29T21:45
            odds_str = match.get("Cotă", "")

            if not odds_str:
                logger.warning(f"Lipsește cota pentru {event_name}")
                result['reason'] = 'missing_odds'
                return result

            try:
                odds = float(odds_str)
            except:
                logger.warning(f"Cotă invalidă pentru {event_name}: {odds_str}")
                result['reason'] = 'invalid_odds'
                return result

            # 4. Calculate stake - CITEȘTE DIN DATABASE (source of truth)
            cumulative_loss = team.cumulative_loss
            progression_step = team.progression_step
            team_initial_stake = team.initial_stake

            stake, stop_loss = staking_service.calculate_stake(
                cumulative_loss,
                odds,
                progression_step,
                team_initial_stake
            )

            logger.info(f"{team.name}: initial_stake={team_initial_stake}, loss={cumulative_loss}, step={progression_step} => miză={stake}")

            if stop_loss:
                logger.warning(f"Stop loss atins pentru {team.name}")
                # Pause team în DATABASE
                from app.services.teams_repository import teams_repository
                teams_repository.update_team(
                    team.id,
                    self.user_id,
                    TeamUpdate(status=TeamStatus.PAUSED)
                )

                # Sync status în Google Sheets
                try:
                    self.sheets_client.update_team_in_index(
                        self.spreadsheet_id,
                        team.id,
                        {'id': team.id, 'name': team.name, 'status': 'paused'}
                    )
                    logger.info(f"Sheets sincronizat: {team.name} -> PAUSED (stop loss)")
                except Exception as sheets_err:
                    logger.warning(f"Nu s-a putut sincroniza Sheets pentru {team.name}: {sheets_err}")

                result['reason'] = 'stop_loss_reached'
                return result

            logger.info(f"Plasare pariu: {team.name} - {event_name} - Miză: {stake} @ {odds}")

            # 5. Find market on Betfair and place bet
            # Extract main team name (remove FC, United, etc for better matching)
            search_terms = [team.name]
            for suffix in [" FC", " United FC", " United"]:
                if team.name.endswith(suffix):
                    search_terms.append(team.name[:-len(suffix)])

            events = None
            for search_term in search_terms:
                events = await self.betfair_client.list_events(
                    event_type_id="1",
                    text_query=search_term
                )
                if events:
                    logger.info(f"Găsit evenimente cu search term: {search_term}")
                    break

            if not events:
                logger.warning(f"Nu s-a găsit evenimentul pe Betfair: {event_name}")
                result['reason'] = 'event_not_found_betfair'
                return result

            # 6. Find matching event BY DATE
            match_date_only = match_date_str[:10] if match_date_str else ""  # "2025-11-29"

            event_id = None
            matched_event_name = None
            for ev in events:
                ev_data = ev.get("event", {})
                ev_name = ev_data.get("name", "")
                ev_open_date = ev_data.get("openDate", "")
                ev_date_only = ev_open_date[:10] if ev_open_date else ""

                # Verificăm dacă numele se potrivește ȘI data e aceeași
                name_matches = False
                for search_term in search_terms:
                    if search_term.lower() in ev_name.lower():
                        name_matches = True
                        break

                if name_matches and ev_date_only == match_date_only:
                    event_id = ev_data.get("id")
                    matched_event_name = ev_name
                    logger.info(f"Match găsit cu data corectă: {ev_name} (event_id: {event_id}, data: {ev_date_only})")
                    break

            if not event_id:
                logger.warning(f"Nu s-a găsit event_id pentru {team.name} cu data {match_date_only}")
                result['reason'] = 'event_id_not_found'
                return result

            # 7. Get market
            markets = await self.betfair_client.list_market_catalogue(
                event_ids=[event_id],
                market_type_codes=["MATCH_ODDS"]
            )

            if not markets:
                logger.warning(f"Nu s-a găsit piața pentru {event_name}")
                result['reason'] = 'market_not_found'
                return result

            market = markets[0]
            market_id = market.get("marketId", "")

            # 8. Get selection ID - găsim runner-ul care conține numele echipei noastre
            runners = market.get("runners", [])
            if not runners:
                logger.warning(f"Nu s-au găsit runners pentru {event_name}")
                result['reason'] = 'no_runners'
                return result

            # IMPORTANT: Folosim match EXACT pentru a evita meciuri greșite (ex: Arsenal vs Arsenal Wolves)
            selection_id = None
            selected_runner_name = None
            for runner in runners:
                runner_name = runner.get("runnerName", "")
                for search_term in search_terms:
                    if search_term.lower() == runner_name.lower():
                        selection_id = str(runner.get("selectionId", ""))
                        selected_runner_name = runner_name
                        break
                if selection_id:
                    break

            if not selection_id:
                logger.warning(f"Nu s-a găsit runner pentru echipa {team.name} în meciul {event_name}")
                logger.warning(f"  Runners disponibili: {[r.get('runnerName') for r in runners]}")
                result['reason'] = 'runner_not_found'
                return result

            logger.info(f"Selectat runner: {selected_runner_name} (ID: {selection_id}) pentru {team.name}")

            # 9. Place bet
            place_result = await self.betfair_client.place_bet(
                market_id=market_id,
                selection_id=selection_id,
                stake=stake,
                odds=odds
            )

            if place_result.success:
                # 10. Update Google Sheets - match status
                self.sheets_client.update_match_status(
                    self.spreadsheet_id, team.name, event_name, "PENDING",
                    stake=stake, bet_id=place_result.bet_id
                )

                # Update last_stake în Index
                self.sheets_client.update_last_stake(self.spreadsheet_id, team.name, stake)

                logger.info(
                    f"✅ Pariu plasat: {team.name} - {event_name} - "
                    f"Miză: {stake} RON @ {odds} - Bet ID: {place_result.bet_id}"
                )

                result['bet_placed'] = True
                result['bet_id'] = place_result.bet_id
                result['stake'] = stake
                result['odds'] = odds
                result['event_name'] = event_name
            else:
                logger.error(f"Eroare plasare pariu {team.name}: {place_result.error_message}")
                self.sheets_client.update_match_status(
                    self.spreadsheet_id, team.name, event_name, "ERROR"
                )
                result['reason'] = f'bet_placement_error: {place_result.error_message}'

            return result

        except Exception as e:
            logger.error(f"Error processing team {team.name}: {e}", exc_info=True)
            result['reason'] = f'exception: {str(e)}'
            raise

    async def check_bet_results(self) -> dict:
        """
        Verifică rezultatele pariurilor PENDING - LOGICA DIN VPS:
        1. Citește pariurile PENDING din Google Sheets
        2. Verifică pe Betfair dacă sunt settled
        3. Actualizează status (WON/LOST) în Google Sheets
        4. Actualizează progresia echipei (cumulative_loss, progression_step)
        """
        from app.services.staking import staking_service

        results = {
            'user_email': self.user.email,
            'pending_checked': 0,
            'settled_found': 0,
            'won': 0,
            'lost': 0,
            'still_pending': 0,
            'errors': []
        }

        try:
            # Get pending bets from Google Sheets
            pending_bets = self.sheets_client.get_pending_bets(self.spreadsheet_id)
            results['pending_checked'] = len(pending_bets)

            if not pending_bets:
                logger.info(f"Nu există pariuri PENDING pentru user {self.user.email}")
                return results

            logger.info(f"Verificare {len(pending_bets)} pariuri PENDING pentru {self.user.email}")

            # Get settled orders from Betfair (ultimele 3 zile)
            settled_orders = await self.betfair_client.get_settled_orders(days=3)

            # Create a map of bet_id -> settled order
            settled_map = {}
            for order in settled_orders:
                bet_id = str(order.get("betId", ""))
                if bet_id:
                    settled_map[bet_id] = order

            logger.info(f"Găsite {len(settled_map)} ordine settled pe Betfair pentru {self.user.email}")

            # Load all teams from DATABASE (source of truth)
            teams = self.get_active_teams()

            # Check each pending bet
            for bet in pending_bets:
                bet_id = str(bet.get("Bet ID", ""))
                team_name = bet.get("team_name", "")
                event_name = bet.get("Meci", "")
                stake = float(bet.get("Miză", 0))

                if not bet_id or bet_id not in settled_map:
                    results['still_pending'] += 1
                    continue

                # Bet is settled!
                settled_order = settled_map[bet_id]
                profit = float(settled_order.get("profit", 0))

                results['settled_found'] += 1

                # Find team in loaded teams
                from app.services.teams_repository import teams_repository
                team_obj = None
                for t in teams:
                    if t.name == team_name:
                        team_obj = t
                        break

                if not team_obj:
                    logger.warning(f"Nu s-a găsit echipa {team_name} în database")
                    continue

                cumulative_loss = team_obj.cumulative_loss
                progression_step = team_obj.progression_step

                if profit > 0:
                    # WON
                    results['won'] += 1
                    profit_amount, new_cumulative_loss, new_progression_step = staking_service.process_win(
                        stake, float(bet.get("Cotă", 0))
                    )

                    logger.info(f"✅ WON: {team_name} - {event_name} - Profit: {profit_amount} RON")

                    # Update DATABASE (source of truth)
                    teams_repository.update_team(
                        team_obj.id,
                        self.user_id,
                        TeamUpdate(
                            cumulative_loss=new_cumulative_loss,
                            progression_step=new_progression_step
                        )
                    )

                    # Sync Google Sheets (vizualizare)
                    try:
                        self.sheets_client.update_match_status(
                            self.spreadsheet_id, team_name, event_name, "WON",
                            profit_loss=profit_amount
                        )
                        self.sheets_client.update_team_progression(
                            self.spreadsheet_id, team_name,
                            cumulative_loss=new_cumulative_loss,
                            progression_step=new_progression_step,
                            won=True,
                            profit=profit_amount
                        )
                        logger.info(f"Sheets sincronizat: {team_name} WON")
                    except Exception as sheets_err:
                        logger.warning(f"Nu s-a putut sincroniza Sheets pentru {team_name} WON: {sheets_err}")

                else:
                    # LOST
                    results['lost'] += 1
                    loss_amount, new_cumulative_loss, new_progression_step = staking_service.process_loss(
                        stake, cumulative_loss, progression_step
                    )

                    logger.info(f"❌ LOST: {team_name} - {event_name} - Loss: {loss_amount} RON")

                    # Update DATABASE (source of truth)
                    teams_repository.update_team(
                        team_obj.id,
                        self.user_id,
                        TeamUpdate(
                            cumulative_loss=new_cumulative_loss,
                            progression_step=new_progression_step
                        )
                    )

                    # Sync Google Sheets (vizualizare)
                    try:
                        self.sheets_client.update_match_status(
                            self.spreadsheet_id, team_name, event_name, "LOST",
                            profit_loss=loss_amount
                        )
                        self.sheets_client.update_team_progression(
                            self.spreadsheet_id, team_name,
                            cumulative_loss=new_cumulative_loss,
                            progression_step=new_progression_step,
                            won=False,
                            profit=-loss_amount
                        )
                        logger.info(f"Sheets sincronizat: {team_name} LOST")
                    except Exception as sheets_err:
                        logger.warning(f"Nu s-a putut sincroniza Sheets pentru {team_name} LOST: {sheets_err}")

            logger.info(f"✅ Check results completed for {self.user.email}: {results}")
            return results

        except Exception as e:
            error_msg = f"Check results failed for {self.user.email}: {e}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            return results

    async def cleanup(self):
        """Cleanup resources"""
        if self.betfair_client and self.betfair_client.is_connected():
            await self.betfair_client.disconnect()

        logger.info(f"Cleaned up bot for user {self.user.email}")

    async def place_bet_for_team(self, team_name: str, initial_stake: float) -> bool:
        """
        Plasează pariu pentru o singură echipă (folosit la adăugarea echipei).

        Args:
            team_name: Numele echipei
            initial_stake: Miza inițială setată la adăugare

        Returns:
            True dacă pariul a fost plasat cu succes
        """
        from app.services.staking import staking_service

        try:
            # Initialize if not already
            if not self.betfair_client or not self.betfair_client.is_connected():
                initialized = await self.initialize()
                if not initialized:
                    logger.warning(f"Nu s-a putut inițializa bot-ul pentru {self.user.email}")
                    return False

            # Get scheduled matches from Google Sheets
            scheduled_matches = self.sheets_client.get_scheduled_matches(
                self.spreadsheet_id, team_name
            )
            if not scheduled_matches:
                logger.info(f"Nu există meciuri programate pentru {team_name}")
                return False

            # Get first match
            sorted_matches = sorted(scheduled_matches, key=lambda x: x.get("Data", ""))
            match = sorted_matches[0] if sorted_matches else None
            if not match:
                return False

            event_name = match.get("Meci", "")
            odds_str = match.get("Cotă", "")

            if not odds_str:
                logger.warning(f"Lipsește cota pentru {event_name}")
                return False

            try:
                odds = float(odds_str)
            except:
                logger.warning(f"Cotă invalidă pentru {event_name}: {odds_str}")
                return False

            # Calculate stake (pentru echipă nouă: cumulative_loss=0, progression_step=0)
            stake, stop_loss = staking_service.calculate_stake(0, odds, 0, initial_stake)

            if stop_loss:
                logger.warning(f"Stop loss pentru {team_name}")
                return False

            logger.info(f"Plasare pariu imediat: {team_name} - {event_name} - Miză: {stake} @ {odds}")

            # Find event on Betfair
            search_terms = [team_name]
            for suffix in [" FC", " United FC", " United"]:
                if team_name.endswith(suffix):
                    search_terms.append(team_name[:-len(suffix)])

            events = None
            for search_term in search_terms:
                events = await self.betfair_client.list_events(event_type_id="1", text_query=search_term)
                if events:
                    break

            if not events:
                logger.warning(f"Nu s-a găsit evenimentul pe Betfair: {event_name}")
                return False

            # Find matching event by date
            match_date_str = match.get("Data", "")
            match_date_only = match_date_str[:10] if match_date_str else ""
            event_id = None
            for ev in events:
                ev_data = ev.get("event", {})
                ev_name = ev_data.get("name", "")
                ev_open_date = ev_data.get("openDate", "")
                ev_date_only = ev_open_date[:10] if ev_open_date else ""

                name_matches = any(st.lower() in ev_name.lower() for st in search_terms)
                if name_matches and ev_date_only == match_date_only:
                    event_id = ev_data.get("id")
                    break

            if not event_id:
                logger.warning(f"Nu s-a găsit event_id pentru {team_name} cu data {match_date_only}")
                return False

            # Get market
            markets = await self.betfair_client.list_market_catalogue(event_ids=[event_id], market_type_codes=["MATCH_ODDS"])
            if not markets:
                logger.warning(f"Nu s-a găsit piața pentru {event_name}")
                return False

            market = markets[0]
            market_id = market.get("marketId", "")
            runners = market.get("runners", [])

            # Find runner (match EXACT)
            selection_id = None
            for runner in runners:
                runner_name = runner.get("runnerName", "")
                if any(st.lower() == runner_name.lower() for st in search_terms):
                    selection_id = str(runner.get("selectionId", ""))
                    break

            if not selection_id:
                logger.warning(f"Nu s-a găsit runner pentru {team_name}")
                return False

            # Place bet
            place_result = await self.betfair_client.place_bet(
                market_id=market_id,
                selection_id=selection_id,
                stake=stake,
                odds=odds
            )

            if place_result.success:
                # Update Google Sheets
                self.sheets_client.update_match_status(
                    self.spreadsheet_id, team_name, event_name, "PENDING",
                    stake=stake, bet_id=place_result.bet_id
                )
                self.sheets_client.update_last_stake(self.spreadsheet_id, team_name, stake)

                # Update database
                team_obj = teams_repository.get_team_by_name(team_name, self.user_id)
                if team_obj:
                    teams_repository.update_team(
                        team_obj.id,
                        self.user_id,
                        TeamUpdate(cumulative_loss=0, progression_step=0)
                    )

                logger.info(f"Pariu plasat cu succes: {team_name} - {event_name} - Miză: {stake} RON @ {odds}")
                return True
            else:
                logger.error(f"Eroare plasare pariu {team_name}: {place_result.error_message}")
                self.sheets_client.update_match_status(
                    self.spreadsheet_id, team_name, event_name, "ERROR"
                )
                return False

        except Exception as e:
            logger.error(f"Eroare la plasarea pariului pentru {team_name}: {e}")
            return False
