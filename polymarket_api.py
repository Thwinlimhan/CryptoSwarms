"""
Polymarket API Integration
Fetches prediction market data and trading signals
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
import json


class PolymarketAPI:
    """Client for Polymarket API"""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_markets(self, limit: int = 20) -> List[Dict]:
        """Get active prediction markets"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(
                f"{self.BASE_URL}/markets",
                params={"limit": limit, "active": "true"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                return []
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return self._get_mock_markets()
    
    async def get_market_prices(self, market_id: str) -> Dict:
        """Get current prices for a specific market"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(
                f"{self.BASE_URL}/markets/{market_id}/prices"
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            print(f"Error fetching market prices: {e}")
            return {}
    
    async def get_trading_signals(self) -> List[Dict]:
        """Generate trading signals based on market analysis"""
        markets = await self.get_markets(limit=10)
        signals = []
        
        for market in markets:
            try:
                # Extract market data
                question = market.get("question", "Unknown Market")
                yes_price = float(market.get("outcomePrices", ["0.5", "0.5"])[0])
                volume = float(market.get("volume", 0))
                
                # Simple signal generation logic
                signal = self._generate_signal(yes_price, volume)
                
                signals.append({
                    "market": question[:35],  # Truncate for display
                    "yes": yes_price * 100,  # Convert to percentage
                    "volume": volume,
                    "signal": signal,
                    "market_id": market.get("id", ""),
                    "timestamp": datetime.now().isoformat()
                })
            except (ValueError, KeyError, TypeError):
                continue
        
        return signals
    
    def _generate_signal(self, yes_price: float, volume: float) -> str:
        """Generate trading signal based on price and volume"""
        # Simple momentum-based signal generation
        if yes_price > 0.7 and volume > 100000:
            return "LONG"
        elif yes_price < 0.3 and volume > 100000:
            return "SHORT"
        elif volume < 50000:
            return "LOW_VOL"
        else:
            return "NEUTRAL"
    
    def _get_mock_markets(self) -> List[Dict]:
        """Return mock market data for testing"""
        return [
            {
                "id": "btc-100k-eoy-2026",
                "question": "BTC > $100k by EOY 2026",
                "outcomePrices": ["0.675", "0.325"],
                "volume": "1250000",
                "active": True
            },
            {
                "id": "eth-etf-q2-2026",
                "question": "ETH ETF Approval Q2 2026",
                "outcomePrices": ["0.452", "0.548"],
                "volume": "890000",
                "active": True
            },
            {
                "id": "fed-rate-cut-march-2026",
                "question": "Fed Rate Cut March 2026",
                "outcomePrices": ["0.821", "0.179"],
                "volume": "2100000",
                "active": True
            },
            {
                "id": "ai-regulation-bill",
                "question": "AI Regulation Bill Passes",
                "outcomePrices": ["0.287", "0.713"],
                "volume": "567000",
                "active": True
            },
            {
                "id": "sol-500-q4-2026",
                "question": "SOL > $500 by Q4 2026",
                "outcomePrices": ["0.734", "0.266"],
                "volume": "1890000",
                "active": True
            },
            {
                "id": "recession-2026",
                "question": "Recession in 2026",
                "outcomePrices": ["0.348", "0.652"],
                "volume": "3450000",
                "active": True
            }
        ]


class PolymarketBot:
    """Automated trading bot for Polymarket"""
    
    def __init__(self, strategy: str = "momentum"):
        self.api = PolymarketAPI()
        self.strategy = strategy
        self.positions: List[Dict] = []
        self.signals_history: List[Dict] = []
    
    async def scan_markets(self) -> List[Dict]:
        """Scan markets and generate signals"""
        async with self.api as api:
            signals = await api.get_trading_signals()
            
            # Store signals history
            self.signals_history.extend(signals)
            
            # Keep only last 100 signals
            if len(self.signals_history) > 100:
                self.signals_history = self.signals_history[-100:]
            
            return signals
    
    async def execute_strategy(self, signals: List[Dict]) -> List[Dict]:
        """Execute trading strategy based on signals"""
        actions = []
        
        for signal in signals:
            if signal["signal"] == "LONG" and signal["yes"] < 80:
                actions.append({
                    "action": "BUY_YES",
                    "market": signal["market"],
                    "confidence": self._calculate_confidence(signal),
                    "suggested_size": self._calculate_position_size(signal)
                })
            elif signal["signal"] == "SHORT" and signal["yes"] > 20:
                actions.append({
                    "action": "BUY_NO",
                    "market": signal["market"],
                    "confidence": self._calculate_confidence(signal),
                    "suggested_size": self._calculate_position_size(signal)
                })
        
        return actions
    
    def _calculate_confidence(self, signal: Dict) -> float:
        """Calculate confidence score for a signal"""
        volume_score = min(signal["volume"] / 1000000, 1.0)  # Normalize volume
        
        if signal["signal"] == "LONG":
            price_score = (100 - signal["yes"]) / 100  # Higher confidence for lower yes price
        elif signal["signal"] == "SHORT":
            price_score = signal["yes"] / 100  # Higher confidence for higher yes price
        else:
            price_score = 0.5
        
        return (volume_score + price_score) / 2
    
    def _calculate_position_size(self, signal: Dict) -> float:
        """Calculate suggested position size"""
        confidence = self._calculate_confidence(signal)
        base_size = 100  # Base position size in USD
        
        return base_size * confidence


async def test_polymarket_api():
    """Test the Polymarket API integration"""
    async with PolymarketAPI() as api:
        print("Testing Polymarket API...")
        
        # Test markets
        print("\nFetching markets...")
        markets = await api.get_markets(limit=5)
        print(f"Got {len(markets)} markets")
        
        if markets:
            print("\nSample markets:")
            for market in markets[:3]:
                question = market.get("question", "Unknown")
                prices = market.get("outcomePrices", ["0", "0"])
                volume = market.get("volume", "0")
                print(f"  {question[:50]}: Yes={float(prices[0])*100:.1f}% Vol=${float(volume):,.0f}")
        
        # Test signals
        print("\nGenerating trading signals...")
        signals = await api.get_trading_signals()
        print(f"Generated {len(signals)} signals")
        
        if signals:
            print("\nTop signals:")
            for signal in signals[:3]:
                print(f"  {signal['market']}: {signal['signal']} "
                      f"(Yes: {signal['yes']:.1f}%, Vol: ${signal['volume']:,.0f})")


if __name__ == "__main__":
    asyncio.run(test_polymarket_api())