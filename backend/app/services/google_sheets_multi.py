"""
Google Sheets service for multi-user (SaaS)
Each user gets their own dedicated spreadsheet
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsMultiService:
    """Service for managing Google Sheets per user"""

    def __init__(self):
        """Initialize Google Sheets client"""
        self.credentials = None
        self.client = None
        self._cache: dict = {}
        self._cache_timestamps: dict = {}
        self._cache_ttl = 60  # Cache TTL in seconds
        self._initialize_client()

    def _get_cached(self, key: str):
        """Get cached value if not expired."""
        import time
        if key in self._cache:
            if time.time() - self._cache_timestamps.get(key, 0) < self._cache_ttl:
                return self._cache[key]
        return None

    def _set_cached(self, key: str, value):
        """Set cached value with timestamp."""
        import time
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()

    def invalidate_cache(self, key: str = None):
        """Invalidate cache for a specific key or all."""
        if key:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()

    def _initialize_client(self):
        """Initialize Google Sheets client with service account"""
        try:
            self.credentials = Credentials.from_service_account_file(
                settings.google_sheets_credentials_path,
                scopes=SCOPES
            )
            self.client = gspread.authorize(self.credentials)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise

    def create_user_spreadsheet(self, user_email: str, user_id: str) -> str:
        """
        Allocate an available spreadsheet from the pool for a new user.
        Spreadsheets are pre-created manually in the Betix-Users folder.

        Args:
            user_email: User's email address
            user_id: User's ID

        Returns:
            Spreadsheet ID
        """
        try:
            from googleapiclient.discovery import build

            BETIX_USERS_FOLDER_ID = "1z5I-19J719ox1IIbs6ZZGs8JEcoTwukj"

            drive_service = build('drive', 'v3', credentials=self.credentials)

            results = drive_service.files().list(
                q=f"'{BETIX_USERS_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and name contains 'Betix-User-'",
                fields='files(id, name)',
                orderBy='name'
            ).execute()

            available_files = results.get('files', [])

            if not available_files:
                raise Exception("Nu mai sunt spreadsheet-uri disponibile în pool. Contactează administratorul.")

            selected_file = available_files[0]
            spreadsheet_id = selected_file['id']

            spreadsheet = self.client.open_by_key(spreadsheet_id)
            new_title = f"Betix - {user_email}"
            spreadsheet.update_title(new_title)

            logger.info(f"Allocated spreadsheet {selected_file['name']} -> {new_title} for user {user_email}")

            # Share spreadsheet cu "anyone with link" (Editor access)
            try:
                drive_service.permissions().create(
                    fileId=spreadsheet_id,
                    body={
                        'type': 'anyone',
                        'role': 'writer'
                    }
                ).execute()
                logger.info(f"✅ Spreadsheet shared as 'anyone with link' (Editor access) for {user_email}")
            except Exception as e:
                logger.error(f"❌ Failed to share spreadsheet for {user_email}: {e}")
                # Nu aruncăm eroare - spreadsheet-ul e alocat, doar share-ul a eșuat

            return spreadsheet_id

        except Exception as e:
            logger.error(f"Failed to allocate spreadsheet for {user_email}: {e}")
            raise

    def _setup_spreadsheet_structure(self, spreadsheet):
        """
        Setup initial structure for user spreadsheet

        Args:
            spreadsheet: gspread Spreadsheet object
        """
        try:
            # Rename first sheet to "Index"
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Index")

            # Setup Index sheet headers
            headers = [
                "id",
                "name",
                "betfair_id",
                "sport",
                "league",
                "country",
                "cumulative_loss",
                "last_stake",
                "progression_step",
                "status",
                "created_at",
                "updated_at",
                "initial_stake",
                "total_matches",
                "matches_won",
                "total_profit"
            ]

            worksheet.update('A1:P1', [headers])

            # Format header row
            worksheet.format('A1:P1', {
                "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER"
            })

            logger.info(f"Setup structure for spreadsheet: {spreadsheet.id}")

        except Exception as e:
            logger.error(f"Failed to setup spreadsheet structure: {e}")
            raise

    def get_spreadsheet(self, spreadsheet_id: str):
        """
        Get spreadsheet by ID

        Args:
            spreadsheet_id: Spreadsheet ID

        Returns:
            gspread Spreadsheet object
        """
        try:
            return self.client.open_by_key(spreadsheet_id)
        except Exception as e:
            logger.error(f"Failed to open spreadsheet {spreadsheet_id}: {e}")
            raise

    def add_team_sheet(self, spreadsheet_id: str, team_name: str) -> bool:
        """
        Add a new sheet for a team

        Args:
            spreadsheet_id: Spreadsheet ID
            team_name: Team name

        Returns:
            True if successful
        """
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)

            # Check if sheet already exists
            try:
                spreadsheet.worksheet(team_name)
                logger.info(f"Sheet '{team_name}' already exists")
                return True
            except gspread.exceptions.WorksheetNotFound:
                pass

            # Create new sheet
            worksheet = spreadsheet.add_worksheet(title=team_name, rows=1000, cols=20)

            # Setup headers for team sheet (same order as PARIURI)
            headers = [
                "Data",           # A: Match date (YYYY-MM-DDTHH:MM format)
                "Meci",           # B: Match name
                "Competiție",     # C: Competition name
                "Cotă",           # D: Odds
                "Miză",           # E: Stake
                "Status",         # F: Status (PROGRAMAT, PENDING, WON, LOST)
                "Profit",         # G: Profit or loss amount
                "Bet ID"          # H: Betfair bet ID
            ]

            worksheet.update('A1:H1', [headers])

            # Format header row
            worksheet.format('A1:H1', {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.4},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER"
            })

            logger.info(f"Created sheet '{team_name}' in spreadsheet {spreadsheet_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add team sheet '{team_name}': {e}")
            return False

    def update_team_in_index(
        self,
        spreadsheet_id: str,
        team_id: str,
        team_data: dict
    ) -> bool:
        """
        Update or add team in Index sheet

        Args:
            spreadsheet_id: Spreadsheet ID
            team_id: Team ID
            team_data: Team data dictionary

        Returns:
            True if successful
        """
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            index_sheet = spreadsheet.worksheet("Index")

            # Get all records
            records = index_sheet.get_all_records()

            # Find row with team_id
            row_index = None
            for i, record in enumerate(records, start=2):  # Start from row 2 (after header)
                if record.get('id') == team_id:
                    row_index = i
                    break

            # Prepare row data
            row_data = [
                team_data.get('id', team_id),
                team_data.get('name', ''),
                team_data.get('betfair_id', ''),
                team_data.get('sport', 'Football'),
                team_data.get('league', ''),
                team_data.get('country', ''),
                team_data.get('cumulative_loss', 0),
                team_data.get('last_stake', 0),
                team_data.get('progression_step', 0),
                team_data.get('status', 'active'),
                team_data.get('created_at', ''),
                team_data.get('updated_at', ''),
                team_data.get('initial_stake', 100)
            ]

            if row_index:
                # Update existing row
                index_sheet.update(f'A{row_index}:M{row_index}', [row_data])
                logger.info(f"Updated team {team_id} in Index")
            else:
                # Append new row
                index_sheet.append_row(row_data)
                logger.info(f"Added team {team_id} to Index")

            self.invalidate_cache(f"index_{spreadsheet_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update team in Index: {e}")
            return False

    def load_team(self, spreadsheet_id: str, team_name: str) -> Optional[dict]:
        """
        Load team data from Index sheet (cu cache 60s)

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name

        Returns:
            Team data dict or None
        """
        try:
            cache_key = f"index_{spreadsheet_id}"
            records = self._get_cached(cache_key)

            if records is None:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
                index_sheet = spreadsheet.worksheet("Index")
                records = index_sheet.get_all_records()
                self._set_cached(cache_key, records)

            for record in records:
                if record.get("name") == team_name:
                    return {
                        "id": str(record.get("id", "")),
                        "name": record.get("name", ""),
                        "cumulative_loss": float(record.get("cumulative_loss", 0)),
                        "progression_step": int(record.get("progression_step", 0)),
                        "last_stake": float(record.get("last_stake", 100)),
                        "initial_stake": float(record.get("initial_stake", 100)),
                        "status": record.get("status", "active")
                    }

            return None

        except Exception as e:
            logger.error(f"Error loading team {team_name}: {e}")
            return None

    def get_pending_bets(self, spreadsheet_id: str, team_name: str = None) -> list:
        """
        Get pending bets from all team sheets or specific team (cu cache 60s pentru Index)

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Optional team name filter

        Returns:
            List of pending bets
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)

            cache_key = f"index_{spreadsheet_id}"
            teams = self._get_cached(cache_key)
            if teams is None:
                index_sheet = spreadsheet.worksheet("Index")
                teams = index_sheet.get_all_records()
                self._set_cached(cache_key, teams)

            pending_bets = []

            for team_record in teams:
                t_name = team_record.get("name", "")
                if team_name and t_name != team_name:
                    continue

                try:
                    # Cache team sheet reads to avoid rate limits
                    team_cache_key = f"team_sheet_{spreadsheet_id}_{t_name}"
                    matches = self._get_cached(team_cache_key)

                    if matches is None:
                        team_sheet = spreadsheet.worksheet(t_name)
                        matches = team_sheet.get_all_records()
                        self._set_cached(team_cache_key, matches)

                    for match in matches:
                        status = str(match.get("Status", "")).strip().upper()
                        if status == "PENDING":
                            pending_bets.append({
                                "team_name": t_name,
                                "Meci": match.get("Meci", ""),
                                "Data": match.get("Data", ""),
                                "Cotă": match.get("Cotă", ""),
                                "Miză": match.get("Miză", ""),
                                "Bet ID": match.get("Bet ID", ""),
                                "Status": status
                            })
                except Exception as e:
                    logger.warning(f"Could not read team sheet {t_name}: {e}")
                    continue

            return pending_bets

        except Exception as e:
            logger.error(f"Error getting pending bets: {e}")
            return []

    def get_scheduled_matches(self, spreadsheet_id: str, team_name: str) -> list:
        """
        Get scheduled matches (without status) from team sheet (cu cache 60s)

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name

        Returns:
            List of scheduled matches
        """
        try:
            cache_key = f"matches_{spreadsheet_id}_{team_name}"
            matches = self._get_cached(cache_key)

            if matches is None:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
                team_sheet = spreadsheet.worksheet(team_name)
                matches = team_sheet.get_all_records()
                self._set_cached(cache_key, matches)

            scheduled = []
            for match in matches:
                status = str(match.get("Status", "")).strip().upper()
                # Include matches with PROGRAMAT status or no status
                if not status or status == "" or status == "PROGRAMAT":
                    scheduled.append({
                        "Meci": match.get("Meci", ""),
                        "Data": match.get("Data", ""),
                        "Cotă": match.get("Cotă", ""),
                        "Competiție": match.get("Competiție", "")
                    })

            return scheduled

        except Exception as e:
            logger.error(f"Error getting scheduled matches for {team_name}: {e}")
            return []

    def update_match_status(
        self,
        spreadsheet_id: str,
        team_name: str,
        event_name: str,
        status: str,
        stake: float = None,
        profit_loss: float = None,
        bet_id: str = None
    ) -> bool:
        """
        Update match status in team sheet

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name
            event_name: Match name
            status: New status (PENDING, WON, LOST, ERROR)
            stake: Stake amount
            profit_loss: Profit or loss amount
            bet_id: Betfair bet ID

        Returns:
            Success boolean
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            team_sheet = spreadsheet.worksheet(team_name)

            # Find the row with this match
            cell = team_sheet.find(event_name)
            if not cell:
                logger.warning(f"Match {event_name} not found in {team_name} sheet")
                return False

            row = cell.row

            # Update columns (A=Data, B=Meci, C=Competiție, D=Cotă, E=Miză, F=Status, G=Profit, H=Bet ID)
            updates = []
            if stake is not None:
                updates.append({'range': f'E{row}', 'values': [[stake]]})  # Miză column (E)
            if status:
                updates.append({'range': f'F{row}', 'values': [[status]]})  # Status column (F)
            if profit_loss is not None:
                updates.append({'range': f'G{row}', 'values': [[profit_loss]]})  # Profit column (G)
            if bet_id:
                updates.append({'range': f'H{row}', 'values': [[bet_id]]})  # Bet ID column (H)

            if updates:
                team_sheet.batch_update(updates)
                self.invalidate_cache(f"matches_{spreadsheet_id}_{team_name}")
                logger.info(f"Updated match {event_name} in {team_name}: status={status}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating match status: {e}")
            return False

    def update_team_progression(
        self,
        spreadsheet_id: str,
        team_name: str,
        cumulative_loss: float,
        progression_step: int,
        won: bool = None,
        profit: float = 0
    ) -> bool:
        """
        Update team progression in Index sheet
        Actualizează și statisticile: total_matches, matches_won, total_profit

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name
            cumulative_loss: New cumulative loss
            progression_step: New progression step
            won: True dacă a câștigat, False dacă a pierdut, None pentru skip statistici
            profit: Profitul/pierderea din acest pariu

        Returns:
            Success boolean
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            index_sheet = spreadsheet.worksheet("Index")

            # Find the row with this team
            cell = index_sheet.find(team_name)
            if not cell:
                logger.warning(f"Team {team_name} not found in Index")
                return False

            row = cell.row

            # Update cumulative_loss (column G) and progression_step (column I)
            updates = [
                {'range': f'G{row}', 'values': [[cumulative_loss]]},
                {'range': f'I{row}', 'values': [[progression_step]]}
            ]

            # Actualizare statistici dacă won e specificat
            if won is not None:
                row_values = index_sheet.row_values(row)
                current_total_matches = int(row_values[13]) if len(row_values) > 13 and row_values[13] else 0
                current_matches_won = int(row_values[14]) if len(row_values) > 14 and row_values[14] else 0
                current_total_profit = float(row_values[15]) if len(row_values) > 15 and row_values[15] else 0

                new_total_matches = current_total_matches + 1
                new_matches_won = current_matches_won + (1 if won else 0)
                new_total_profit = current_total_profit + profit

                updates.extend([
                    {'range': f'N{row}', 'values': [[new_total_matches]]},
                    {'range': f'O{row}', 'values': [[new_matches_won]]},
                    {'range': f'P{row}', 'values': [[new_total_profit]]}
                ])

            index_sheet.batch_update(updates)
            self.invalidate_cache(f"teams_{spreadsheet_id}")
            logger.info(f"Updated {team_name} progression: loss={cumulative_loss}, step={progression_step}")
            return True

        except Exception as e:
            logger.error(f"Error updating team progression: {e}")
            return False

    def update_last_stake(self, spreadsheet_id: str, team_name: str, stake: float) -> bool:
        """
        Update last_stake in Index sheet

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name
            stake: New stake value

        Returns:
            Success boolean
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            index_sheet = spreadsheet.worksheet("Index")

            # Find the row with this team
            cell = index_sheet.find(team_name)
            if not cell:
                logger.warning(f"Team {team_name} not found in Index")
                return False

            row = cell.row

            # Update last_stake (column H)
            index_sheet.update(f'H{row}', [[stake]])
            logger.info(f"Updated {team_name} last_stake: {stake}")
            return True

        except Exception as e:
            logger.error(f"Error updating last_stake: {e}")
            return False

    def save_match_for_team(
        self,
        spreadsheet_id: str,
        team_name: str,
        match_data: dict
    ) -> bool:
        """
        Save a match to team sheet

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_name: Team name
            match_data: Match data dict

        Returns:
            Success boolean
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            team_sheet = spreadsheet.worksheet(team_name)

            # Append new row (A=Data, B=Meci, C=Competiție, D=Cotă, E=Miză, F=Status, G=Profit, H=Bet ID)
            row = [
                match_data.get('start_time', ''),      # A: Data
                match_data.get('event_name', ''),      # B: Meci
                match_data.get('competition', ''),     # C: Competiție
                match_data.get('odds', ''),            # D: Cotă
                '',                                     # E: Miză (empty - filled when bet placed)
                'PROGRAMAT',                           # F: Status
                '',                                     # G: Profit (empty - filled when settled)
                ''                                      # H: Bet ID (empty - filled when bet placed)
            ]

            team_sheet.append_row(row)
            logger.info(f"Saved match {match_data.get('event_name')} for {team_name}")
            return True

        except Exception as e:
            logger.error(f"Error saving match: {e}")
            return False

    def get_betting_stats(self, spreadsheet_id: str) -> dict:
        """
        Get betting statistics from all team sheets.

        Args:
            spreadsheet_id: User's spreadsheet ID

        Returns:
            dict with total_bets, won_bets, lost_bets, pending_bets, total_profit, total_staked
        """
        stats = {
            'total_bets': 0,
            'won_bets': 0,
            'lost_bets': 0,
            'pending_bets': 0,
            'total_profit': 0.0,
            'total_staked': 0.0
        }

        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            index_sheet = spreadsheet.worksheet("Index")
            teams = index_sheet.get_all_records()

            for team_record in teams:
                team_name = team_record.get("name", "")
                if not team_name:
                    continue

                try:
                    team_sheet = spreadsheet.worksheet(team_name)
                    matches = team_sheet.get_all_records()

                    for match in matches:
                        status = str(match.get("Status", "")).strip().upper()
                        stake = 0.0
                        profit_loss = 0.0

                        try:
                            stake = float(match.get("Miză", 0) or 0)
                        except:
                            pass

                        try:
                            profit_loss = float(match.get("Profit/Loss", 0) or 0)
                        except:
                            pass

                        if status == "WON":
                            stats['total_bets'] += 1
                            stats['won_bets'] += 1
                            stats['total_staked'] += stake
                            stats['total_profit'] += profit_loss
                        elif status == "LOST":
                            stats['total_bets'] += 1
                            stats['lost_bets'] += 1
                            stats['total_staked'] += stake
                            stats['total_profit'] += profit_loss  # profit_loss is negative for losses
                        elif status == "PENDING":
                            stats['total_bets'] += 1
                            stats['pending_bets'] += 1
                            stats['total_staked'] += stake

                except Exception as e:
                    logger.warning(f"Could not read team sheet {team_name}: {e}")
                    continue

            # Round values
            stats['total_profit'] = round(stats['total_profit'], 2)
            stats['total_staked'] = round(stats['total_staked'], 2)

            return stats

        except Exception as e:
            logger.error(f"Error getting betting stats: {e}")
            return stats

    def delete_team_from_index(self, spreadsheet_id: str, team_id: str, team_name: str) -> bool:
        """
        Delete a team from Index sheet and delete team's sheet.

        Args:
            spreadsheet_id: User's spreadsheet ID
            team_id: Team ID to delete
            team_name: Team name (for deleting the sheet)

        Returns:
            True if successful
        """
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            index_sheet = spreadsheet.worksheet("Index")

            # Find and delete row in Index
            try:
                cell = index_sheet.find(team_id)
                if cell:
                    index_sheet.delete_rows(cell.row)
                    logger.info(f"Deleted team {team_id} from Index")
            except Exception as e:
                logger.warning(f"Could not find team {team_id} in Index: {e}")

            # Delete team's sheet
            try:
                team_sheet = spreadsheet.worksheet(team_name)
                spreadsheet.del_worksheet(team_sheet)
                logger.info(f"Deleted sheet '{team_name}'")
            except Exception as e:
                logger.warning(f"Could not delete sheet '{team_name}': {e}")

            return True

        except Exception as e:
            logger.error(f"Error deleting team from sheets: {e}")
            return False

    def delete_user_spreadsheet(self, spreadsheet_id: str) -> bool:
        """
        Delete user spreadsheet (use with caution!)

        Args:
            spreadsheet_id: Spreadsheet ID

        Returns:
            True if successful
        """
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            self.client.del_spreadsheet(spreadsheet_id)
            logger.info(f"Deleted spreadsheet: {spreadsheet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete spreadsheet {spreadsheet_id}: {e}")
            return False


# Singleton instance
google_sheets_multi_service = GoogleSheetsMultiService()
