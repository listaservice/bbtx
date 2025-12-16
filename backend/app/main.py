import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.api.betfair_setup import router as betfair_router
from app.api.websocket import websocket_endpoint, broadcast_bot_state, broadcast_notification
from app.config import get_settings
from app.services.trial_service import trial_service
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = AsyncIOScheduler()


async def scheduled_bot_run():
    """
    Funcție executată de scheduler la ora configurată.
    Rulează bot-ul pentru TOȚI userii activi.
    """
    logger.info("🤖 Starting scheduled multi-user bot run")

    await broadcast_notification("Botul începe execuția programată pentru toți userii", "info")

    # Import aici pentru a evita circular imports
    from app.services.multi_user_scheduler import multi_user_scheduler

    # Rulează pentru toți userii
    result = await multi_user_scheduler.run_for_all_users()

    await broadcast_bot_state()

    if result.get('successful_users', 0) > 0:
        await broadcast_notification(
            f"✅ Ciclu complet: {result['successful_users']}/{result['total_users']} useri, "
            f"{result['total_teams_processed']} echipe, {result['total_bets_placed']} pariuri",
            "success"
        )
    else:
        await broadcast_notification(
            f"Eroare: {result.get('message', 'Eroare necunoscută')}",
            "error"
        )

    logger.info(f"Rezultat execuție programată: {result}")


async def scheduled_results_check():
    """
    Verifică rezultatele pariurilor pentru TOȚI userii activi.
    Rulează separat de scheduled_bot_run - NU interferează cu plasarea pariurilor.
    """
    logger.info("🔍 Verificare programată rezultate pariuri (multi-user)")

    await broadcast_notification("Verificare rezultate pariuri pentru toți userii...", "info")

    # Import aici pentru a evita circular imports
    from app.services.multi_user_scheduler import multi_user_scheduler

    # Verifică pentru toți userii
    result = await multi_user_scheduler.check_results_for_all_users()

    await broadcast_bot_state()

    if result.get('successful_users', 0) > 0:
        msg = f"✅ Verificare: {result['total_won']} WIN, {result['total_lost']} LOST, {result['total_still_pending']} PENDING"
        await broadcast_notification(msg, "success")
    else:
        await broadcast_notification(
            f"Eroare verificare: {result.get('error', 'Eroare necunoscută')}",
            "error"
        )

    logger.info(f"Rezultat verificare: {result}")


async def scheduled_trial_check():
    """Verifică și suspendă subscription-urile expirate (TOATE planurile)."""
    logger.info("Verificare subscription-uri expirate")

    db = SessionLocal()
    try:
        count = trial_service.suspend_expired_subscriptions(db)
        if count > 0:
            await broadcast_notification(
                f"{count} utilizatori cu subscription expirat au fost suspendați",
                "info"
            )
    except Exception as e:
        logger.error(f"Eroare verificare subscription-uri: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager pentru aplicație."""
    logger.info("Pornire aplicație...")

    timezone = pytz.timezone(settings.bot_timezone)
    trigger = CronTrigger(
        hour=settings.bot_run_hour,
        minute=settings.bot_run_minute,
        timezone=timezone
    )

    scheduler.add_job(
        scheduled_bot_run,
        trigger=trigger,
        id="daily_bot_run",
        name="Execuție zilnică bot",
        replace_existing=True
    )

    # Job NOU pentru verificare rezultate - rulează la fiecare 30 minute
    # ID diferit: "check_results_job" vs "daily_bot_run"
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler.add_job(
        scheduled_results_check,
        trigger=IntervalTrigger(minutes=30),
        id="check_results_job",
        name="Verificare rezultate pariuri",
        replace_existing=True
    )

    # Job pentru verificare subscription-uri expirate - rulează zilnic la 00:00
    scheduler.add_job(
        scheduled_trial_check,
        trigger=CronTrigger(hour=0, minute=0, timezone=timezone),
        id="subscription_check_job",
        name="Verificare subscription-uri expirate",
        replace_existing=True
    )

    scheduler.start()
    logger.info(
        f"Scheduler pornit - Bot programat la {settings.bot_run_hour:02d}:{settings.bot_run_minute:02d} "
        f"({settings.bot_timezone})"
    )
    logger.info("Verificare rezultate programată la fiecare 30 minute")
    logger.info("Verificare subscription-uri programată zilnic la 00:00")

    yield

    logger.info("Oprire aplicație...")
    scheduler.shutdown()
    logger.info("Scheduler oprit")


app = FastAPI(
    title="Betix SaaS API",
    description="Multi-tenant betting bot platform for Betfair Exchange",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")     # Auth endpoints: /api/auth/*
app.include_router(betfair_router, prefix="/api")  # Betfair setup: /api/betfair/*
app.include_router(api_router, prefix="/api")      # Legacy endpoints: /api/*

app.add_api_websocket_route("/ws", websocket_endpoint)


# Serve frontend static files in production
# In Docker: /app/backend/app/main.py -> /app/frontend/dist
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes."""
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Betfair Bot API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "scheduled_run": f"{settings.bot_run_hour:02d}:{settings.bot_run_minute:02d} {settings.bot_timezone}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
