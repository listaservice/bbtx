#!/usr/bin/env python3
"""
Script pentru găsirea celor mai bune 20 echipe cu win rate > 65%
Analizează rezultate istorice din Betfair API
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
from app.services.betfair_client import betfair_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TeamAnalyzer:
    """Analizează echipe pentru win rate"""

    def __init__(self):
        self.client = betfair_client
        self.team_stats = defaultdict(lambda: {'wins': 0, 'total': 0, 'team_name': ''})

    async def analyze_historical_results(self, days_back: int = 90):
        """Analizează rezultate istorice ultimele N zile din piețe Betfair"""

        logger.info(f"🔍 Analizare rezultate ultimele {days_back} zile...")

        # Connect to Betfair
        if not self.client.is_connected():
            logger.info("Connecting to Betfair...")
            connected = await self.client.connect()
            if not connected:
                logger.error("❌ Failed to connect to Betfair")
                return

        logger.info("✅ Connected to Betfair\n")

        # Analizează meciuri din ultimele zile
        logger.info("📊 Fetching football events from last 90 days...")

        # Pentru fiecare săptămână din ultimele 90 zile
        weeks = days_back // 7

        for week in range(weeks):
            start_date = datetime.utcnow() - timedelta(days=(week + 1) * 7)
            end_date = datetime.utcnow() - timedelta(days=week * 7)

            logger.info(f"Week {week + 1}/{weeks}: {start_date.date()} to {end_date.date()}")

            # Get events pentru această perioadă
            events = await self.client.list_events(
                event_type_id="1",  # Football
                text_query=None
            )

            if not events:
                continue

            # Analizează primele 50 evenimente
            for event in events[:50]:
                event_data = event.get('event', {})
                event_id = event_data.get('id')
                event_name = event_data.get('name', '')

                # Get market pentru acest event
                markets = await self.client.list_market_catalogue(
                    event_ids=[event_id],
                    market_type_codes=["MATCH_ODDS"]
                )

                if not markets:
                    continue

                market = markets[0]
                runners = market.get('runners', [])

                # Get market book pentru rezultat
                market_books = await self.client.list_market_book([market['marketId']])

                if not market_books:
                    continue

                market_book = market_books[0]

                # Verifică dacă meciul e finalizat
                if market_book.get('status') != 'CLOSED':
                    continue

                # Găsește câștigătorul
                for runner in market_book.get('runners', []):
                    if runner.get('status') == 'WINNER':
                        selection_id = runner.get('selectionId')

                        # Găsește numele echipei câștigătoare
                        for r in runners:
                            if r.get('selectionId') == selection_id:
                                team_name = r.get('runnerName', '')

                                # Skip Draw
                                if 'Draw' in team_name or 'draw' in team_name.lower():
                                    continue

                                # Contorizează victorie
                                self.team_stats[team_name]['team_name'] = team_name
                                self.team_stats[team_name]['wins'] += 1
                                self.team_stats[team_name]['total'] += 1
                                break
                        break

                # Contorizează și echipele care au pierdut
                for runner in runners:
                    team_name = runner.get('runnerName', '')

                    # Skip Draw
                    if 'Draw' in team_name or 'draw' in team_name.lower():
                        continue

                    # Dacă echipa nu a câștigat, a pierdut
                    if team_name not in [r.get('runnerName') for r in market_book.get('runners', []) if r.get('status') == 'WINNER']:
                        if self.team_stats[team_name]['team_name'] == '':
                            self.team_stats[team_name]['team_name'] = team_name
                        self.team_stats[team_name]['total'] += 1

            # Pauză între request-uri
            await asyncio.sleep(2)

        logger.info(f"✅ Analyzed {len(self.team_stats)} unique teams\n")

    def calculate_win_rates(self) -> List[Tuple[str, float, int, int]]:
        """Calculează win rate pentru fiecare echipă"""

        results = []

        for team_name, stats in self.team_stats.items():
            total = stats['total']
            wins = stats['wins']

            # Minimum 5 meciuri pentru statistică relevantă
            if total < 5:
                continue

            win_rate = (wins / total) * 100
            results.append((team_name, win_rate, wins, total))

        # Sortează după win rate
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_top_teams(self, min_win_rate: float = 65.0, limit: int = 20) -> List[Dict]:
        """Returnează top echipe cu win rate > threshold"""

        all_results = self.calculate_win_rates()

        # Filtrează după win rate
        top_teams = [
            {
                'team': team,
                'win_rate': round(win_rate, 1),
                'wins': wins,
                'total': total,
                'losses': total - wins
            }
            for team, win_rate, wins, total in all_results
            if win_rate >= min_win_rate
        ]

        return top_teams[:limit]

    async def run_analysis(self, days_back: int = 90, min_win_rate: float = 65.0):
        """Rulează analiza completă"""

        logger.info("=" * 80)
        logger.info("🏆 TOP TEAMS ANALYZER - Betfair Historical Data")
        logger.info("=" * 80)

        # Analizează rezultate
        await self.analyze_historical_results(days_back=days_back)

        # Get top teams
        top_teams = self.get_top_teams(min_win_rate=min_win_rate, limit=20)

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info(f"📈 TOP 20 TEAMS WITH WIN RATE > {min_win_rate}%")
        logger.info("=" * 80)

        if not top_teams:
            logger.warning(f"❌ No teams found with win rate > {min_win_rate}%")
            logger.info("Try lowering the threshold or increasing days_back")
            return

        logger.info(f"\nFound {len(top_teams)} teams:\n")

        for i, team in enumerate(top_teams, 1):
            logger.info(f"{i:2d}. {team['team']}")
            logger.info(f"    Win Rate: {team['win_rate']}%")
            logger.info(f"    Record: {team['wins']}W - {team['losses']}L ({team['total']} total)")
            logger.info("")

        # Summary
        logger.info("=" * 80)
        logger.info("📊 SUMMARY")
        logger.info("=" * 80)

        avg_win_rate = sum(t['win_rate'] for t in top_teams) / len(top_teams)
        total_matches = sum(t['total'] for t in top_teams)
        total_wins = sum(t['wins'] for t in top_teams)

        logger.info(f"Average Win Rate: {avg_win_rate:.1f}%")
        logger.info(f"Total Matches Analyzed: {total_matches}")
        logger.info(f"Total Wins: {total_wins}")
        logger.info(f"Period: Last {days_back} days")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Analysis complete!")
        logger.info("=" * 80)


async def main():
    """Main entry point"""

    # Parametri
    DAYS_BACK = 90  # Ultimele 3 luni
    MIN_WIN_RATE = 65.0  # Minimum 65% win rate

    analyzer = TeamAnalyzer()
    await analyzer.run_analysis(days_back=DAYS_BACK, min_win_rate=MIN_WIN_RATE)


if __name__ == "__main__":
    asyncio.run(main())
