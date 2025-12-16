from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel

from app.models.schemas import (
    Team, TeamCreate, TeamUpdate, TeamStatus,
    Bet, BetStatus,
    BotState, BotStatus,
    DashboardStats, ApiResponse, Sport
)
from app.models.settings import AppSettings, SettingsUpdate
from app.services.staking import staking_service
from app.services.settings_manager import settings_manager
from app.services.google_sheets import google_sheets_client
from app.services.google_sheets_multi import google_sheets_multi_service
from app.services.betfair_client import betfair_client
from app.services.auth import authenticate, get_current_user
from app.dependencies import get_current_user as get_current_user_jwt
from app.models.user import User
from app.config import get_settings

settings = get_settings()

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Autentificare utilizator."""
    token = authenticate(request.username, request.password)
    if token:
        return LoginResponse(success=True, token=token, message="Autentificare reușită")
    return LoginResponse(success=False, message="Credențiale invalide")


@router.get("/auth/verify")
async def verify_auth(username: str = Depends(get_current_user)):
    """Verifică dacă token-ul este valid."""
    return {"valid": True, "username": username}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(get_current_user_jwt)):
    """Returnează statisticile pentru dashboard (per user)."""
    from app.services.teams_repository import teams_repository

    # Get user's teams
    teams = teams_repository.get_user_teams(current_user.id, active_only=False)

    # Get betting stats from Google Sheets
    betting_stats = {'total_bets': 0, 'won_bets': 0, 'lost_bets': 0, 'pending_bets': 0, 'total_profit': 0.0, 'total_staked': 0.0}

    if current_user.google_sheets_id:
        try:
            betting_stats = google_sheets_multi_service.get_betting_stats(current_user.google_sheets_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not get betting stats for {current_user.email}: {e}")

    # Calculate win rate
    total_settled = betting_stats['won_bets'] + betting_stats['lost_bets']
    win_rate = (betting_stats['won_bets'] / total_settled * 100) if total_settled > 0 else 0.0

    return DashboardStats(
        total_teams=len(teams),
        active_teams=len([t for t in teams if t.status == TeamStatus.ACTIVE]),
        total_bets=betting_stats['total_bets'],
        won_bets=betting_stats['won_bets'],
        lost_bets=betting_stats['lost_bets'],
        pending_bets=betting_stats['pending_bets'],
        total_profit=betting_stats['total_profit'],
        win_rate=round(win_rate, 1),
        total_staked=betting_stats['total_staked']
    )


@router.get("/bot/state", response_model=BotState)
async def get_bot_state():
    """Returnează starea globală a botului (scheduler status)."""
    # Global state - nu mai folosim bot_engine
    # Returnăm status simplu bazat pe scheduler
    return BotState(
        status=BotStatus.RUNNING,  # Scheduler rulează mereu
        last_run=None,  # TODO: Get from scheduler
        next_run=None,  # TODO: Get from scheduler
        last_error=None,
        bets_placed_today=0,
        total_stake_today=0.0
    )


@router.post("/bot/start", response_model=ApiResponse)
async def start_bot():
    """Pornește botul (DEPRECATED - scheduler rulează automat)."""
    return ApiResponse(
        success=True,
        message="Bot-ul rulează automat prin scheduler la ora programată"
    )


@router.post("/bot/stop", response_model=ApiResponse)
async def stop_bot():
    """Oprește botul (DEPRECATED - scheduler nu poate fi oprit din API)."""
    return ApiResponse(
        success=False,
        message="Bot-ul nu poate fi oprit din API. Scheduler rulează automat."
    )


@router.post("/bot/run-now", response_model=ApiResponse)
async def run_bot_now(current_user: User = Depends(get_current_user_jwt)):
    """Execută bot-ul manual pentru user-ul curent."""
    from app.services.user_bot_service import UserBotService

    try:
        # Create bot service pentru acest user
        bot_service = UserBotService(current_user)

        # Initialize
        initialized = await bot_service.initialize()
        if not initialized:
            return ApiResponse(
                success=False,
                message="Nu s-a putut inițializa bot-ul. Verifică credențialele Betfair."
            )

        # Run bot
        result = await bot_service.run_bot()

        # Cleanup
        await bot_service.cleanup()

        return ApiResponse(
            success=True,
            message=f"Bot executat: {result['teams_processed']} echipe procesate, {result['bets_placed']} pariuri plasate",
            data=result
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Eroare la execuția bot-ului: {str(e)}"
        )


@router.get("/teams/search-betfair")
async def search_teams_betfair(
    q: str = "",
    current_user: User = Depends(get_current_user_jwt)
):
    """
    Caută echipe pe Betfair API folosind credențialele user-ului.
    Returnează lista de echipe găsite pentru autocomplete.
    """
    if len(q) < 3:
        return []

    from app.services.betfair_client import BetfairClient
    from app.services.encryption import encryption_service
    from sqlalchemy import create_engine, text
    from app.config import get_settings
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()

    try:
        # Load user's Betfair credentials
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT username_encrypted, password_encrypted, app_key_encrypted
                FROM betfair_credentials
                WHERE user_id = :user_id
            """), {"user_id": current_user.id})
            row = result.fetchone()

        if not row:
            logger.warning(f"User {current_user.email} nu are credențiale Betfair configurate")
            return []

        # Decrypt credentials
        try:
            username = encryption_service.decrypt(row.username_encrypted)
            password = encryption_service.decrypt(row.password_encrypted)
            app_key = encryption_service.decrypt(row.app_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt Betfair credentials for {current_user.email}: {e}")
            return []

        # Create and configure Betfair client for this user
        user_betfair_client = BetfairClient()
        user_betfair_client.configure(
            app_key=app_key,
            username=username,
            password=password
        )

        # Connect
        await user_betfair_client.connect()
        if not user_betfair_client.is_connected():
            logger.warning(f"Nu s-a putut conecta la Betfair pentru {current_user.email}")
            return []

        # Search events
        events = await user_betfair_client.list_events(
            event_type_id="1",
            text_query=q
        )

        # Disconnect after search
        await user_betfair_client.disconnect()

        # Skip keywords pentru echipe rezerve/tineret
        skip_keywords = ["(Res)", "U19", "U21", "U23", "Women", "Feminin", "II", "B)", "(W)"]

        # Extragem numele unice ale echipelor din evenimente
        team_names = set()
        for event in events[:20]:
            event_name = event.get("event", {}).get("name", "")

            # Skip meciuri cu echipe rezerve/tineret
            if any(kw in event_name for kw in skip_keywords):
                continue

            # Evenimentele sunt "Team A v Team B"
            if " v " in event_name:
                parts = event_name.split(" v ")
                for part in parts:
                    part = part.strip()
                    # Filtram doar echipele care contin query-ul
                    if q.lower() in part.lower():
                        team_names.add(part)

        # Sortam alfabetic si returnam
        results = sorted(list(team_names))
        logger.info(f"Search Betfair '{q}' for {current_user.email}: {len(results)} echipe găsite")
        return results

    except Exception as e:
        logger.error(f"Eroare căutare Betfair pentru {current_user.email}: {e}")
        return []


@router.get("/teams", response_model=List[Team])
async def get_teams(
    active_only: bool = False,
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează lista de echipe pentru user-ul curent."""
    from app.services.teams_repository import teams_repository
    return teams_repository.get_user_teams(current_user.id, active_only)


@router.get("/teams/{team_id}", response_model=Team)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează o echipă după ID (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    team = teams_repository.get_team(team_id, current_user.id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită sau nu aparține acestui user"
        )
    return team


@router.post("/teams", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_create: TeamCreate,
    current_user: User = Depends(get_current_user_jwt)
):
    """Creează o echipă nouă și preia următoarele 20 de meciuri."""
    from app.services.betfair_client import BetfairClient
    from app.services.teams_repository import teams_repository
    from app.services.encryption import encryption_service
    from sqlalchemy import create_engine, text
    from app.config import get_settings
    import logging
    logger = logging.getLogger(__name__)
    settings = get_settings()

    # Verificare subscription activ
    if current_user.subscription_status not in ['active', 'trial']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subscription inactiv. Status: {current_user.subscription_status}"
        )

    # Verificare max_teams
    current_count = teams_repository.count_user_teams(current_user.id, active_only=True)
    max_teams = current_user.max_teams

    if max_teams != -1 and current_count >= max_teams:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ai atins limita de echipe pentru planul tău ({current_count}/{max_teams}). Upgrade pentru mai multe echipe."
        )

    team = Team(
        id=str(uuid4()),
        user_id=current_user.id,
        name=team_create.name,
        betfair_id=team_create.betfair_id,
        sport=team_create.sport,
        league=team_create.league,
        country=team_create.country,
        cumulative_loss=0.0,
        last_stake=settings.bot_initial_stake,
        progression_step=0,
        initial_stake=settings.bot_initial_stake,
        status=TeamStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Save to database (SINGURA SURSĂ)
    teams_repository.create_team(team)

    # Save to Google Sheets (user's spreadsheet) and fetch matches
    if current_user.google_sheets_id:
        # Save team to Index sheet
        team_data = {
            'id': team.id,
            'name': team.name,
            'betfair_id': team.betfair_id,
            'sport': team.sport.value,
            'league': team.league,
            'country': team.country,
            'cumulative_loss': 0.0,
            'last_stake': settings.bot_initial_stake,
            'progression_step': 0,
            'status': 'active',
            'created_at': team.created_at.isoformat(),
            'updated_at': team.updated_at.isoformat(),
            'initial_stake': settings.bot_initial_stake
        }

        google_sheets_multi_service.update_team_in_index(
            current_user.google_sheets_id,
            team.id,
            team_data
        )

        # Create team sheet
        google_sheets_multi_service.add_team_sheet(
            current_user.google_sheets_id,
            team.name
        )

        # Fetch next 20 matches from Betfair with odds (using user's credentials)
        user_betfair_client = None
        try:
            # Load user's Betfair credentials
            engine = create_engine(settings.database_url)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT username_encrypted, password_encrypted, app_key_encrypted
                    FROM betfair_credentials
                    WHERE user_id = :user_id
                """), {"user_id": current_user.id})
                row = result.fetchone()

            if not row:
                logger.warning(f"User {current_user.email} nu are credențiale Betfair - skip fetch matches")
            else:
                # Decrypt credentials
                username = encryption_service.decrypt(row.username_encrypted)
                password = encryption_service.decrypt(row.password_encrypted)
                app_key = encryption_service.decrypt(row.app_key_encrypted)

                # Create user's Betfair client
                user_betfair_client = BetfairClient()
                user_betfair_client.configure(
                    app_key=app_key,
                    username=username,
                    password=password
                )

                await user_betfair_client.connect()

            if user_betfair_client and user_betfair_client.is_connected():
                # Search for team matches
                event_type_id = "1" if team.sport == "football" else "7522"
                events = await user_betfair_client.list_events(
                    event_type_id=event_type_id,
                    text_query=team.name
                )

                matches = []
                for event in events[:20]:
                    event_data = event.get("event", {})
                    event_id = event_data.get("id", "")
                    event_name = event_data.get("name", "")
                    competition = event.get("competitionName", "")

                    # Skip reserve/youth teams
                    skip_keywords = ["(Res)", "U19", "U21", "U23", "Women", "Feminin", "II", "B)", "(W)"]
                    if any(kw in event_name for kw in skip_keywords):
                        logger.info(f"Skip echipă rezerve/tineret: {event_name}")
                        continue

                    # Get odds and start time from market catalogue
                    odds = ""
                    market_start_time = ""
                    if event_id:
                        try:
                            markets = await user_betfair_client.list_market_catalogue(
                                event_ids=[event_id],
                                market_type_codes=["MATCH_ODDS"]
                            )
                            if markets:
                                market = markets[0]
                                market_id = market.get("marketId", "")
                                market_start_time_utc = market.get("marketStartTime", "")

                                # Convert UTC to Europe/Bucharest
                                if market_start_time_utc:
                                    try:
                                        from datetime import datetime as dt
                                        import pytz
                                        utc_time = dt.fromisoformat(market_start_time_utc.replace("Z", "+00:00"))
                                        bucharest_tz = pytz.timezone("Europe/Bucharest")
                                        local_time = utc_time.astimezone(bucharest_tz)
                                        market_start_time = local_time.strftime("%Y-%m-%dT%H:%M")
                                    except:
                                        market_start_time = market_start_time_utc
                                else:
                                    market_start_time = ""

                                if market_id:
                                    # Get runner prices
                                    prices = await user_betfair_client.list_market_book([market_id])
                                    if prices and prices[0].get("runners"):
                                        price_runners = prices[0].get("runners", [])
                                        market_runners = market.get("runners", [])

                                        # Găsim runner-ul echipei noastre (match EXACT)
                                        team_selection_id = None
                                        for mr in market_runners:
                                            runner_name = mr.get("runnerName", "")
                                            if team.name.lower() == runner_name.lower():
                                                team_selection_id = mr.get("selectionId")
                                                break

                                        # Luăm cota pentru echipa noastră
                                        if team_selection_id:
                                            for pr in price_runners:
                                                if pr.get("selectionId") == team_selection_id:
                                                    back_prices = pr.get("ex", {}).get("availableToBack", [])
                                                    if back_prices:
                                                        odds = back_prices[0].get("price", "")
                                                    break
                                        else:
                                            # Fallback: dacă nu găsim, luăm primul runner
                                            if price_runners:
                                                back_prices = price_runners[0].get("ex", {}).get("availableToBack", [])
                                                if back_prices:
                                                    odds = back_prices[0].get("price", "")
                        except Exception as e:
                            logger.warning(f"Could not get odds for {event_name}: {e}")

                    matches.append({
                        "start_time": market_start_time,
                        "event_name": event_name,
                        "competition": competition,
                        "odds": str(odds) if odds else ""
                    })

                if matches:
                    # Sortare meciuri cronologic după start_time
                    matches_sorted = sorted(matches, key=lambda x: x.get("start_time", ""))

                    # Save matches to user's spreadsheet
                    for match in matches_sorted:
                        google_sheets_multi_service.save_match_for_team(
                            current_user.google_sheets_id,
                            team.name,
                            match
                        )

                    logger.info(f"Saved {len(matches_sorted)} matches for {team.name} (sorted by date)")

                    # Plasează pariu imediat pe primul meci dacă e azi și nu a început încă
                    if matches_sorted and user_betfair_client and user_betfair_client.is_connected():
                        first_match = matches_sorted[0]
                        first_match_time = first_match.get("start_time", "")
                        if first_match_time:
                            try:
                                import pytz
                                from datetime import datetime as dt
                                bucharest_tz = pytz.timezone("Europe/Bucharest")
                                now = dt.now(bucharest_tz)
                                match_dt = dt.fromisoformat(first_match_time)
                                if match_dt.tzinfo is None:
                                    match_dt = bucharest_tz.localize(match_dt)

                                # Dacă meciul e azi și nu a început încă, plasează pariul
                                if match_dt.date() == now.date() and match_dt > now:
                                    logger.info(f"Primul meci {team.name} e azi - plasare pariu imediat")
                                    from app.services.user_bot_service import UserBotService
                                    user_bot = UserBotService(current_user)
                                    bet_result = await user_bot.place_bet_for_team(team.name, team.initial_stake)
                                    if bet_result:
                                        logger.info(f"Pariu plasat cu succes pentru {team.name}")
                                    else:
                                        logger.warning(f"Nu s-a putut plasa pariul pentru {team.name}")
                            except Exception as e:
                                logger.warning(f"Eroare la verificarea/plasarea pariului imediat: {e}")
                else:
                    logger.warning(f"No matches found for {team.name}")

        except Exception as e:
            logger.error(f"Error fetching matches for {team.name}: {e}")
        finally:
            # Cleanup user's Betfair client
            if user_betfair_client and user_betfair_client.is_connected():
                await user_betfair_client.disconnect()

    return team


@router.put("/teams/{team_id}", response_model=Team)
async def update_team(
    team_id: str,
    team_update: TeamUpdate,
    current_user: User = Depends(get_current_user_jwt)
):
    """Actualizează o echipă (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    team = teams_repository.update_team(team_id, current_user.id, team_update)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită sau nu aparține acestui user"
        )
    return team


@router.delete("/teams/{team_id}", response_model=ApiResponse)
async def delete_team(
    team_id: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """Șterge o echipă (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    # Get team first to have the name for Google Sheets deletion
    team = teams_repository.get_team(team_id, current_user.id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită sau nu aparține acestui user"
        )

    # Delete from database
    success = teams_repository.delete_team(team_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la ștergerea echipei din baza de date"
        )

    # Delete from Google Sheets
    if current_user.google_sheets_id:
        google_sheets_multi_service.delete_team_from_index(
            current_user.google_sheets_id,
            team_id,
            team.name
        )

    return ApiResponse(success=True, message="Echipă ștearsă cu succes")


@router.post("/teams/{team_id}/pause", response_model=Team)
async def pause_team(
    team_id: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """Pune o echipă pe pauză (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    team_update = TeamUpdate(status=TeamStatus.PAUSED)
    team = teams_repository.update_team(team_id, current_user.id, team_update)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită sau nu aparține acestui user"
        )
    return team


@router.post("/teams/{team_id}/activate", response_model=Team)
async def activate_team(
    team_id: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """Activează o echipă (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    team_update = TeamUpdate(status=TeamStatus.ACTIVE)
    team = teams_repository.update_team(team_id, current_user.id, team_update)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Echipa cu ID {team_id} nu a fost găsită sau nu aparține acestui user"
        )
    return team


@router.post("/teams/{team_id}/reset", response_model=Team)
async def reset_team_progression(
    team_id: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """Resetează progresia unei echipe (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    # Verifică ownership
    team = teams_repository.get_team(team_id, current_user.id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Echipa nu a fost găsită sau nu aparține acestui user"
        )

    # Reset progression în database
    team_update = TeamUpdate(
        cumulative_loss=0.0,
        progression_step=0
    )
    updated_team = teams_repository.update_team(team_id, current_user.id, team_update)

    # Update în Google Sheets
    if current_user.google_sheets_id:
        google_sheets_multi_service.update_team_progression(
            current_user.google_sheets_id,
            team.name,
            cumulative_loss=0.0,
            progression_step=0
        )

    return updated_team


@router.get("/teams/{team_id}/progression")
async def get_team_progression(
    team_id: str,
    next_odds: float = 1.5,
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează informații despre progresia unei echipe (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    # Verifică ownership
    team = teams_repository.get_team(team_id, current_user.id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Echipa nu a fost găsită sau nu aparține acestui user"
        )

    return staking_service.get_progression_info(
        team.cumulative_loss,
        team.progression_step,
        next_odds
    )


@router.put("/teams/{team_id}/initial-stake")
async def update_team_initial_stake(
    team_id: str,
    initial_stake: float,
    current_user: User = Depends(get_current_user_jwt)
):
    """Actualizează miza inițială pentru o echipă (verifică ownership)."""
    from app.services.teams_repository import teams_repository

    # Verifică ownership
    team = teams_repository.get_team(team_id, current_user.id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Echipa nu a fost găsită sau nu aparține acestui user"
        )

    if initial_stake <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Miza inițială trebuie să fie > 0"
        )

    # 1. Update în DATABASE (source of truth)
    teams_repository.update_team(
        team_id,
        current_user.id,
        TeamUpdate(initial_stake=initial_stake)
    )

    # 2. Sync în Google Sheets (pentru vizualizare)
    if current_user.google_sheets_id:
        team_data = {
            'id': team.id,
            'name': team.name,
            'initial_stake': initial_stake
        }
        google_sheets_multi_service.update_team_in_index(
            current_user.google_sheets_id,
            team.id,
            team_data
        )

    return {"success": True, "message": f"Miză inițială actualizată: {initial_stake} RON"}


@router.get("/bets", response_model=List[Bet])
async def get_bets(
    team_id: Optional[str] = None,
    status_filter: Optional[BetStatus] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează lista de pariuri pentru user-ul curent (din Google Sheets)."""
    # TODO: Implement reading bets from Google Sheets
    # Pentru acum returnează listă goală
    # Va fi implementat în BUG #4 (migrare source of truth)
    return []


@router.get("/bets/pending", response_model=List[Bet])
async def get_pending_bets(current_user: User = Depends(get_current_user_jwt)):
    """Returnează pariurile în așteptare pentru user-ul curent."""
    # TODO: Implement reading pending bets from Google Sheets
    # Pentru acum returnează listă goală
    return []


@router.get("/bets/{bet_id}", response_model=Bet)
async def get_bet(bet_id: str, current_user: User = Depends(get_current_user_jwt)):
    """Returnează un pariu după ID (verifică ownership)."""
    # TODO: Implement reading bet from Google Sheets with ownership check
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Endpoint în curs de implementare"
    )


@router.post("/bets/{bet_id}/settle", response_model=Bet)
async def settle_bet(
    bet_id: str,
    won: bool,
    current_user: User = Depends(get_current_user_jwt)
):
    """Marchează un pariu ca câștigat sau pierdut (DEPRECATED - se face automat)."""
    # Acest endpoint nu mai e necesar - rezultatele se verifică automat prin scheduler
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Rezultatele se verifică automat prin scheduler. Acest endpoint nu mai e disponibil."
    )


@router.get("/calculate-stake")
async def calculate_stake(
    cumulative_loss: float = 0,
    odds: float = 1.5,
    progression_step: int = 0
):
    """Calculează miza pentru parametrii dați."""
    if odds <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cota trebuie să fie mai mare decât 1.0"
        )

    stake, stop_loss = staking_service.calculate_stake(
        cumulative_loss, odds, progression_step
    )

    potential_profit = 0.0
    if not stop_loss:
        potential_profit = staking_service.calculate_potential_profit(stake, odds)

    return {
        "stake": stake,
        "potential_profit": potential_profit,
        "stop_loss_reached": stop_loss,
        "cumulative_loss": cumulative_loss,
        "odds": odds,
        "progression_step": progression_step
    }


@router.get("/settings", response_model=AppSettings)
async def get_settings(
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează setările aplicației."""
    return settings_manager.get_settings()


@router.put("/settings", response_model=AppSettings)
async def update_settings(
    updates: SettingsUpdate,
    current_user: User = Depends(get_current_user_jwt)
):
    """Actualizează setările aplicației."""
    updated = settings_manager.update_settings(updates)

    if updates.initial_stake:
        staking_service.initial_stake = updates.initial_stake
    if updates.max_progression_steps:
        staking_service.max_progression_steps = updates.max_progression_steps

    # Update scheduler if time changed
    if updates.bot_run_hour is not None or updates.bot_run_minute is not None:
        from app.main import scheduler, scheduled_bot_run
        import pytz
        from apscheduler.triggers.cron import CronTrigger

        timezone = pytz.timezone("Europe/Bucharest")
        new_hour = updates.bot_run_hour if updates.bot_run_hour is not None else updated.bot_run_hour
        new_minute = updates.bot_run_minute if updates.bot_run_minute is not None else updated.bot_run_minute

        trigger = CronTrigger(
            hour=new_hour,
            minute=new_minute,
            timezone=timezone
        )

        # Remove old job and add new one
        try:
            scheduler.remove_job("daily_bot_run")
        except:
            pass

        scheduler.add_job(
            scheduled_bot_run,
            trigger=trigger,
            id="daily_bot_run",
            name="Execuție zilnică bot",
            replace_existing=True
        )

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scheduler reprogramat la {new_hour:02d}:{new_minute:02d}")

    return updated


@router.get("/settings/betfair-status")
async def get_betfair_status(
    current_user: User = Depends(get_current_user_jwt)
):
    """Returnează statusul conexiunii Betfair pentru user-ul curent."""
    from sqlalchemy import text, create_engine
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT is_configured FROM betfair_credentials WHERE user_id = :user_id
        """), {"user_id": current_user.id})
        row = result.fetchone()

    is_configured = row.is_configured if row else False

    return {
        "connected": is_configured,
        "configured": is_configured
    }


@router.post("/settings/test-betfair", response_model=ApiResponse)
async def test_betfair_connection(
    current_user: User = Depends(get_current_user_jwt)
):
    """Testează conexiunea la Betfair API pentru user-ul curent."""
    from app.services.betfair_client import BetfairClient
    from app.services.encryption import encryption_service
    from sqlalchemy import text
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)

    # Load user's credentials
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT username_encrypted, password_encrypted, app_key_encrypted
            FROM betfair_credentials WHERE user_id = :user_id
        """), {"user_id": current_user.id})
        row = result.fetchone()

    if not row:
        return ApiResponse(success=False, message="Credențiale Betfair neconfigurate")

    try:
        username = encryption_service.decrypt(row.username_encrypted)
        password = encryption_service.decrypt(row.password_encrypted)
        app_key = encryption_service.decrypt(row.app_key_encrypted)

        user_client = BetfairClient()
        user_client.configure(app_key=app_key, username=username, password=password)
        connected = await user_client.connect()

        if connected:
            await user_client.disconnect()
            return ApiResponse(success=True, message="Conectat la Betfair API")
        else:
            return ApiResponse(success=False, message="Conexiune eșuată la Betfair API")
    except Exception as e:
        return ApiResponse(success=False, message=f"Eroare: {str(e)}")


@router.post("/settings/test-google-sheets", response_model=ApiResponse)
async def test_google_sheets_connection(
    current_user: User = Depends(get_current_user_jwt)
):
    """Testează conexiunea la Google Sheets pentru user-ul curent."""
    if not current_user.google_sheets_id:
        return ApiResponse(
            success=False,
            message="Google Sheets nu este configurat pentru acest user"
        )

    try:
        spreadsheet = google_sheets_multi_service.get_spreadsheet(current_user.google_sheets_id)
        if spreadsheet:
            return ApiResponse(success=True, message="Conectat la Google Sheets")
        else:
            return ApiResponse(success=False, message="Spreadsheet-ul nu a fost găsit")
    except Exception as e:
        return ApiResponse(success=False, message=f"Eroare: {str(e)}")


# AI Chat endpoints
from app.services.ai_chat import ai_chat


class ChatRequest(BaseModel):
    message: str
    use_betfair: bool = True


class ChatResponse(BaseModel):
    response: str


@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_jwt)
):
    """Trimite un mesaj către AI și primește răspuns cu date live de pe Betfair."""
    if request.use_betfair:
        # Use chat_with_bets which handles both bets queries and match queries
        response = await ai_chat.chat_with_bets(request.message)
    else:
        response = await ai_chat.chat(request.message)
    return ChatResponse(response=response)


@router.post("/ai/clear")
async def clear_ai_chat(
    current_user: User = Depends(get_current_user_jwt)
):
    """Șterge istoricul conversației AI."""
    ai_chat.clear_history()
    return {"success": True, "message": "Istoric șters"}


@router.post("/sheets/apply-formatting")
async def apply_sheets_formatting(
    current_user: User = Depends(get_current_user_jwt)
):
    """Aplică conditional formatting pe toate sheet-urile echipelor user-ului."""
    if not current_user.google_sheets_id:
        return {"success": False, "message": "Google Sheets nu este configurat", "sheets_updated": 0}

    # TODO: Implement apply_formatting_to_all_teams in google_sheets_multi
    return {"success": True, "message": "Formatting aplicat automat la creare", "sheets_updated": 0}


@router.get("/logs")
async def get_logs(lines: int = 100):
    """Returnează ultimele N linii din logs."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "-u", "betfair-bot", "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )
        log_lines = result.stdout.strip().split("\n") if result.stdout else []
        return {"success": True, "logs": log_lines}
    except Exception as e:
        return {"success": False, "logs": [], "error": str(e)}
