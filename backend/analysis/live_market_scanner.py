#!/usr/bin/env python3
"""
Live Market Scanner - Analizează piețe Betfair în timp real
Identifică oportunități concrete bazate pe date live
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from app.services.betfair_client import betfair_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveMarketScanner:
    """Scanner pentru piețe live Betfair"""

    def __init__(self):
        self.client = betfair_client
        self.opportunities = []

    async def scan_football_markets(self) -> List[Dict[str, Any]]:
        """Scanează piețe de fotbal pentru oportunități"""
        logger.info("🔍 Scanning live football markets...")

        # Get live events
        events = await self.client.list_events(
            event_type_id="1",  # Football
            text_query=None
        )

        logger.info(f"Found {len(events)} football events")

        opportunities = []

        for event in events[:10]:  # Analizează primele 10
            event_data = event.get('event', {})
            event_id = event_data.get('id')
            event_name = event_data.get('name')

            logger.info(f"\n📊 Analyzing: {event_name}")

            # Get markets for this event
            markets = await self.client.list_market_catalogue(
                event_ids=[event_id],
                market_type_codes=["MATCH_ODDS", "OVER_UNDER_25", "BOTH_TEAMS_TO_SCORE"]
            )

            for market in markets:
                market_id = market.get('marketId')
                market_name = market.get('marketName')

                # Get live prices
                market_books = await self.client.list_market_book([market_id])

                if not market_books:
                    continue

                market_book = market_books[0]

                # Analizează runners și prețuri
                analysis = self._analyze_market(market, market_book)

                if analysis:
                    opportunities.append({
                        'event_name': event_name,
                        'market_name': market_name,
                        'analysis': analysis,
                        'timestamp': datetime.now().isoformat()
                    })

        return opportunities

    def _analyze_market(self, market: Dict, market_book: Dict) -> Dict[str, Any]:
        """Analizează o piață pentru oportunități"""

        runners = market.get('runners', [])
        runner_prices = {
            r['selectionId']: r
            for r in market_book.get('runners', [])
        }

        total_matched = market_book.get('totalMatched', 0)
        status = market_book.get('status')

        analysis = {
            'total_matched': total_matched,
            'status': status,
            'runners': []
        }

        # Analizează fiecare runner
        for runner in runners:
            selection_id = runner.get('selectionId')
            runner_name = runner.get('runnerName')

            price_data = runner_prices.get(selection_id, {})
            ex = price_data.get('ex', {})

            back_prices = ex.get('availableToBack', [])
            lay_prices = ex.get('availableToLay', [])

            if back_prices and lay_prices:
                best_back = back_prices[0]
                best_lay = lay_prices[0]

                back_price = best_back.get('price')
                back_size = best_back.get('size')
                lay_price = best_lay.get('price')
                lay_size = best_lay.get('size')

                # Calculează spread
                spread = lay_price - back_price if back_price and lay_price else None
                spread_pct = (spread / back_price * 100) if spread and back_price else None

                runner_analysis = {
                    'name': runner_name,
                    'back_price': back_price,
                    'back_size': back_size,
                    'lay_price': lay_price,
                    'lay_size': lay_size,
                    'spread': spread,
                    'spread_pct': spread_pct
                }

                analysis['runners'].append(runner_analysis)

        # Identifică oportunități
        opportunities = self._identify_opportunities(analysis)

        if opportunities:
            analysis['opportunities'] = opportunities
            return analysis

        return None

    def _identify_opportunities(self, analysis: Dict) -> List[Dict]:
        """Identifică oportunități concrete în analiza pieței"""
        opportunities = []

        runners = analysis.get('runners', [])
        total_matched = analysis.get('total_matched', 0)

        # 1. Spread mic (< 2%) cu lichiditate mare
        for runner in runners:
            spread_pct = runner.get('spread_pct')
            back_size = runner.get('back_size', 0)
            lay_size = runner.get('lay_size', 0)

            if spread_pct and spread_pct < 2 and back_size > 100 and lay_size > 100:
                opportunities.append({
                    'type': 'LOW_SPREAD_HIGH_LIQUIDITY',
                    'runner': runner['name'],
                    'spread_pct': spread_pct,
                    'liquidity': min(back_size, lay_size),
                    'description': f"Spread mic ({spread_pct:.2f}%) cu lichiditate mare"
                })

        # 2. Lichiditate mare (> £50k matched)
        if total_matched > 50000:
            opportunities.append({
                'type': 'HIGH_LIQUIDITY_MARKET',
                'total_matched': total_matched,
                'description': f"Piață cu lichiditate mare: £{total_matched:,.0f}"
            })

        # 3. Arbitraj potențial (suma probabilităților < 100%)
        if len(runners) >= 2:
            implied_probs = []
            for runner in runners:
                back_price = runner.get('back_price')
                if back_price:
                    implied_prob = (1 / back_price) * 100
                    implied_probs.append(implied_prob)

            if implied_probs:
                total_prob = sum(implied_probs)
                if total_prob < 98:  # Sub 100% = oportunitate arbitraj
                    opportunities.append({
                        'type': 'ARBITRAGE_OPPORTUNITY',
                        'total_probability': total_prob,
                        'edge': 100 - total_prob,
                        'description': f"Arbitraj potențial: {100 - total_prob:.2f}% edge"
                    })

        return opportunities

    async def run_scan(self):
        """Rulează scan complet"""
        logger.info("=" * 80)
        logger.info("🚀 Starting Betfair Live Market Scanner")
        logger.info("=" * 80)

        # Connect to Betfair
        if not self.client.is_connected():
            logger.info("Connecting to Betfair...")
            connected = await self.client.connect()
            if not connected:
                logger.error("❌ Failed to connect to Betfair")
                return

        logger.info("✅ Connected to Betfair\n")

        # Scan markets
        opportunities = await self.scan_football_markets()

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info(f"📈 SCAN RESULTS: Found {len(opportunities)} markets with opportunities")
        logger.info("=" * 80)

        for i, opp in enumerate(opportunities, 1):
            logger.info(f"\n{i}. {opp['event_name']} - {opp['market_name']}")
            logger.info(f"   Status: {opp['analysis']['status']}")
            logger.info(f"   Total Matched: £{opp['analysis']['total_matched']:,.0f}")

            if 'opportunities' in opp['analysis']:
                logger.info(f"   🎯 Opportunities found:")
                for opportunity in opp['analysis']['opportunities']:
                    logger.info(f"      - {opportunity['description']}")

            logger.info(f"   Runners:")
            for runner in opp['analysis']['runners']:
                logger.info(f"      {runner['name']}:")
                logger.info(f"         Back: {runner['back_price']} (£{runner['back_size']})")
                logger.info(f"         Lay:  {runner['lay_price']} (£{runner['lay_size']})")
                if runner.get('spread_pct'):
                    logger.info(f"         Spread: {runner['spread_pct']:.2f}%")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Scan complete")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    scanner = LiveMarketScanner()
    await scanner.run_scan()


if __name__ == "__main__":
    asyncio.run(main())
