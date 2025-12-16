import asyncio
import json
import logging
from typing import Set, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.services.bot_engine import bot_engine
from app.services.auth_service import auth_service
from app.database import SessionLocal
from app.models.user import User
from app.models.schemas import BotState, BotStatus, DashboardStats

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manager pentru conexiuni WebSocket cu suport multi-user."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[str, Set[WebSocket]] = {}  # user_id -> connections

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Acceptă o conexiune nouă."""
        await websocket.accept()
        self.active_connections.add(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

        logger.info(f"Client conectat. Total conexiuni: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Elimină o conexiune."""
        self.active_connections.discard(websocket)

        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"Client deconectat. Total conexiuni: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Trimite un mesaj către toți clienții conectați."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Eroare trimitere mesaj: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Trimite un mesaj către un client specific."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Eroare trimitere mesaj personal: {e}")


manager = ConnectionManager()


def get_user_from_token(token: str) -> Optional[User]:
    """Validează token-ul și returnează user-ul."""
    try:
        payload = auth_service.decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None


def get_user_stats(user: User) -> dict:
    """Obține statisticile pentru un user specific."""
    from app.services.google_sheets_multi import google_sheets_multi_service
    from app.services.teams_repository import teams_repository

    # Get teams count
    teams = teams_repository.get_user_teams(user.id, active_only=False)
    active_teams = [t for t in teams if t.status.value == 'active']

    # Get betting stats from Google Sheets
    betting_stats = {'total_bets': 0, 'won_bets': 0, 'lost_bets': 0, 'pending_bets': 0, 'total_profit': 0.0, 'total_staked': 0.0}
    if user.google_sheets_id:
        try:
            betting_stats = google_sheets_multi_service.get_betting_stats(user.google_sheets_id)
        except Exception as e:
            logger.warning(f"Could not get betting stats for {user.email}: {e}")

    # Calculate win rate
    total_settled = betting_stats['won_bets'] + betting_stats['lost_bets']
    win_rate = (betting_stats['won_bets'] / total_settled * 100) if total_settled > 0 else 0.0

    return {
        'total_teams': len(teams),
        'active_teams': len(active_teams),
        'total_bets': betting_stats['total_bets'],
        'won_bets': betting_stats['won_bets'],
        'lost_bets': betting_stats['lost_bets'],
        'pending_bets': betting_stats['pending_bets'],
        'total_profit': betting_stats['total_profit'],
        'win_rate': round(win_rate, 1),
        'total_staked': betting_stats['total_staked']
    }


async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pentru actualizări în timp real (multi-user)."""
    # Get token from query params
    token = websocket.query_params.get("token")
    user = None
    user_id = None

    if token:
        user = get_user_from_token(token)
        if user:
            user_id = user.id

    await manager.connect(websocket, user_id)

    try:
        # Send initial state
        bot_state = BotState(
            status=BotStatus.RUNNING,
            last_run=None,
            next_run=None,
            last_error=None,
            bets_placed_today=0,
            total_stake_today=0.0
        )

        if user:
            stats = get_user_stats(user)
        else:
            # Fallback for unauthenticated connections
            stats = bot_engine.get_dashboard_stats().model_dump()

        await manager.send_personal(websocket, {
            "type": "initial_state",
            "data": {
                "bot_state": bot_state.model_dump(),
                "stats": stats if isinstance(stats, dict) else stats.model_dump()
            },
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                message = json.loads(data)
                await handle_websocket_message(websocket, message, user)

            except asyncio.TimeoutError:
                await manager.send_personal(websocket, {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"Eroare WebSocket: {e}")
        manager.disconnect(websocket, user_id)


async def handle_websocket_message(websocket: WebSocket, message: dict, user: Optional[User] = None):
    """Procesează mesajele primite de la client (multi-user)."""
    from app.services.teams_repository import teams_repository

    msg_type = message.get("type")

    if msg_type == "pong":
        return

    elif msg_type == "get_state":
        bot_state = BotState(
            status=BotStatus.RUNNING,
            last_run=None,
            next_run=None,
            last_error=None,
            bets_placed_today=0,
            total_stake_today=0.0
        )
        await manager.send_personal(websocket, {
            "type": "bot_state",
            "data": bot_state.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })

    elif msg_type == "get_stats":
        if user:
            stats = get_user_stats(user)
        else:
            stats = bot_engine.get_dashboard_stats().model_dump()
        await manager.send_personal(websocket, {
            "type": "stats",
            "data": stats if isinstance(stats, dict) else stats.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })

    elif msg_type == "get_teams":
        if user:
            teams = teams_repository.get_user_teams(user.id, active_only=False)
            await manager.send_personal(websocket, {
                "type": "teams",
                "data": [t.model_dump() for t in teams],
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            teams = bot_engine.get_all_teams()
            await manager.send_personal(websocket, {
                "type": "teams",
                "data": [t.model_dump() for t in teams],
                "timestamp": datetime.utcnow().isoformat()
            })

    elif msg_type == "get_bets":
        # For now, return empty - bets are in Google Sheets per user
        await manager.send_personal(websocket, {
            "type": "bets",
            "data": [],
            "timestamp": datetime.utcnow().isoformat()
        })

    else:
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Tip mesaj necunoscut: {msg_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_bot_state():
    """Broadcast starea botului către toți clienții."""
    state = bot_engine.get_state()
    await manager.broadcast({
        "type": "bot_state",
        "data": state.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_stats():
    """Broadcast statisticile către toți clienții."""
    stats = bot_engine.get_dashboard_stats()
    await manager.broadcast({
        "type": "stats",
        "data": stats.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_bet_update(bet_id: str):
    """Broadcast actualizare pariu."""
    bet = bot_engine.get_bet(bet_id)
    if bet:
        await manager.broadcast({
            "type": "bet_update",
            "data": bet.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_team_update(team_id: str):
    """Broadcast actualizare echipă."""
    team = bot_engine.get_team(team_id)
    if team:
        await manager.broadcast({
            "type": "team_update",
            "data": team.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_notification(message: str, level: str = "info"):
    """Broadcast notificare."""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "message": message,
            "level": level
        },
        "timestamp": datetime.utcnow().isoformat()
    })
