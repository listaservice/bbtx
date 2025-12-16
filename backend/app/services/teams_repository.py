"""
Teams Repository - Database operations for teams
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.models.schemas import Team, TeamCreate, TeamUpdate, TeamStatus, Sport
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TeamsRepository:
    """Repository for teams database operations"""

    def __init__(self):
        self.engine = create_engine(settings.database_url)

    def get_user_teams(self, user_id: str, active_only: bool = False) -> List[Team]:
        """Get all teams for a user"""
        with self.engine.connect() as conn:
            if active_only:
                result = conn.execute(text("""
                    SELECT * FROM teams
                    WHERE user_id = :user_id AND status = 'active'
                    ORDER BY created_at DESC
                """), {"user_id": user_id})
            else:
                result = conn.execute(text("""
                    SELECT * FROM teams
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """), {"user_id": user_id})

            teams = []
            for row in result:
                teams.append(Team(
                    id=row.id,
                    user_id=row.user_id,
                    name=row.name,
                    betfair_id=row.betfair_id,
                    sport=Sport(row.sport),
                    league=row.league,
                    country=row.country,
                    cumulative_loss=row.cumulative_loss,
                    last_stake=row.last_stake,
                    progression_step=row.progression_step,
                    initial_stake=float(row.initial_stake) if hasattr(row, 'initial_stake') else 100.0,
                    status=TeamStatus(row.status),
                    total_matches=0,
                    matches_won=0,
                    matches_lost=0,
                    total_profit=0.0,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                ))

            return teams

    def get_team(self, team_id: str, user_id: str) -> Optional[Team]:
        """Get a specific team (verify ownership)"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM teams
                WHERE id = :team_id AND user_id = :user_id
            """), {"team_id": team_id, "user_id": user_id})

            row = result.fetchone()
            if not row:
                return None

            return Team(
                id=row.id,
                user_id=row.user_id,
                name=row.name,
                betfair_id=row.betfair_id,
                sport=Sport(row.sport),
                league=row.league,
                country=row.country,
                cumulative_loss=row.cumulative_loss,
                last_stake=row.last_stake,
                progression_step=row.progression_step,
                initial_stake=float(row.initial_stake) if hasattr(row, 'initial_stake') else 100.0,
                status=TeamStatus(row.status),
                total_matches=0,
                matches_won=0,
                matches_lost=0,
                total_profit=0.0,
                created_at=row.created_at,
                updated_at=row.updated_at
            )

    def count_user_teams(self, user_id: str, active_only: bool = True) -> int:
        """Count teams for a user"""
        with self.engine.connect() as conn:
            if active_only:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM teams
                    WHERE user_id = :user_id AND status = 'active'
                """), {"user_id": user_id})
            else:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM teams
                    WHERE user_id = :user_id
                """), {"user_id": user_id})

            return result.scalar()

    def create_team(self, team: Team) -> Team:
        """Create a new team"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO teams (
                    id, user_id, name, betfair_id, sport, league, country,
                    cumulative_loss, last_stake, progression_step, initial_stake, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id, :name, :betfair_id, :sport, :league, :country,
                    :cumulative_loss, :last_stake, :progression_step, :initial_stake, :status,
                    :created_at, :updated_at
                )
            """), {
                "id": team.id,
                "user_id": team.user_id,
                "name": team.name,
                "betfair_id": team.betfair_id,
                "sport": team.sport.value,
                "league": team.league,
                "country": team.country,
                "cumulative_loss": team.cumulative_loss,
                "last_stake": team.last_stake,
                "progression_step": team.progression_step,
                "initial_stake": team.initial_stake,
                "status": team.status.value,
                "created_at": team.created_at,
                "updated_at": team.updated_at
            })
            conn.commit()

            logger.info(f"Created team {team.id} for user {team.user_id}")
            return team

    def update_team(self, team_id: str, user_id: str, update: TeamUpdate) -> Optional[Team]:
        """Update a team (verify ownership)"""
        with self.engine.connect() as conn:
            # Build dynamic update query
            updates = []
            params = {"team_id": team_id, "user_id": user_id, "updated_at": datetime.utcnow()}

            if update.name is not None:
                updates.append("name = :name")
                params["name"] = update.name
            if update.betfair_id is not None:
                updates.append("betfair_id = :betfair_id")
                params["betfair_id"] = update.betfair_id
            if update.sport is not None:
                updates.append("sport = :sport")
                params["sport"] = update.sport.value
            if update.league is not None:
                updates.append("league = :league")
                params["league"] = update.league
            if update.country is not None:
                updates.append("country = :country")
                params["country"] = update.country
            if update.status is not None:
                updates.append("status = :status")
                params["status"] = update.status.value
            if update.cumulative_loss is not None:
                updates.append("cumulative_loss = :cumulative_loss")
                params["cumulative_loss"] = update.cumulative_loss
            if update.progression_step is not None:
                updates.append("progression_step = :progression_step")
                params["progression_step"] = update.progression_step
            if update.initial_stake is not None:
                updates.append("initial_stake = :initial_stake")
                params["initial_stake"] = update.initial_stake

            if not updates:
                return self.get_team(team_id, user_id)

            updates.append("updated_at = :updated_at")
            query = f"""
                UPDATE teams
                SET {', '.join(updates)}
                WHERE id = :team_id AND user_id = :user_id
            """

            conn.execute(text(query), params)
            conn.commit()

            logger.info(f"Updated team {team_id} for user {user_id}")
            return self.get_team(team_id, user_id)

    def delete_team(self, team_id: str, user_id: str) -> bool:
        """Delete a team (verify ownership)"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                DELETE FROM teams
                WHERE id = :team_id AND user_id = :user_id
            """), {"team_id": team_id, "user_id": user_id})
            conn.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted team {team_id} for user {user_id}")

            return deleted


# Singleton instance
teams_repository = TeamsRepository()
