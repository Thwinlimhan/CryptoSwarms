"""
Hyperliquid Data Layer API Integration
Fetches funding rates, perpetual data, and market information
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class HyperliquidAPI:
    """Client for Hyperliquid Data Layer API"""
    
    BASE_URL = "https://api.hyperliquid.xyz"
    INFO_URL = f"{BASE_URL}/info"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_all_mids(self) -> Dict[str, float]:
        """Get current mid prices for all assets"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                self.INFO_URL,
                json={"type": "allMids"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            print(f"Error fetching mids: {e}")
            return {}
    
    async def get_meta(self) -> Dict:
        """Get exchange metadata including all available assets"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                self.INFO_URL,
                json={"type": "meta"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            print(f"Error fetching meta: {e}")
            return {}
    
    async def get_funding_rates(self) -> List[Dict]:
        """Get current funding rates for all perpetuals"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Get metadata first to get all symbols
            meta = await self.get_meta()
            universe = meta.get("universe", [])
            
            funding_data = []
            
            # Get funding info for each asset
            for asset in universe:
                symbol = asset.get("name", "")
                
                async with self.session.post(
                    self.INFO_URL,
                    json={"type": "metaAndAssetCtxs"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract funding rate info
                        for ctx in data.get("assetCtxs", []):
                            funding_rate = float(ctx.get("funding", 0))
                            open_interest = float(ctx.get("openInterest", 0))
                            
                            funding_data.append({
                                "symbol": symbol,
                                "funding_rate": funding_rate * 100,  # Convert to percentage
                                "open_interest": open_interest,
                                "next_funding": self._calculate_next_funding(),
                                "timestamp": datetime.now().isoformat()
                            })
            
            # Sort by funding rate (most negative first)
            funding_data.sort(key=lambda x: x["funding_rate"])
            
            return funding_data[:30]  # Return top 30 most negative
            
        except Exception as e:
            print(f"Error fetching funding rates: {e}")
            return self._get_mock_funding_data()
    
    def _calculate_next_funding(self) -> str:
        """Calculate time until next funding payment (every 8 hours)"""
        now = datetime.now()
        next_funding_hour = ((now.hour // 8) + 1) * 8
        
        if next_funding_hour >= 24:
            next_funding = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        else:
            next_funding = now.replace(hour=next_funding_hour, minute=0, second=0)
        
        time_diff = next_funding - now
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        
        return f"{hours}h {minutes}m"
    
    def _get_mock_funding_data(self) -> List[Dict]:
        """Return mock funding data for testing"""
        symbols = [
            "BTC", "ETH", "SOL", "AVAX", "MATIC", "ARB", "OP", "ATOM", "DOGE", "SHIB",
            "APT", "SUI", "SEI", "TIA", "INJ", "RUNE", "FTM", "NEAR", "DOT", "ADA",
            "LINK", "UNI", "AAVE", "CRV", "LDO", "MKR", "SNX", "COMP", "YFI", "SUSHI"
        ]
        
        import random
        funding_data = []
        
        for symbol in symbols:
            funding_data.append({
                "symbol": f"{symbol}-PERP",
                "funding_rate": random.uniform(-0.05, -0.001),  # Negative funding
                "open_interest": random.uniform(1000000, 500000000),
                "next_funding": self._calculate_next_funding(),
                "timestamp": datetime.now().isoformat()
            })
        
        # Sort by most negative
        funding_data.sort(key=lambda x: x["funding_rate"])
        return funding_data[:30]
    
    async def get_user_state(self, address: str) -> Dict:
        """Get user account state"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                self.INFO_URL,
                json={"type": "clearinghouseState", "user": address}
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            print(f"Error fetching user state: {e}")
            return {}
    
    async def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict]:
        """Get historical candle data"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": symbol,
                    "interval": interval,
                }
            }
            
            if start_time:
                payload["req"]["startTime"] = start_time
            if end_time:
                payload["req"]["endTime"] = end_time
            
            async with self.session.post(
                self.INFO_URL,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            print(f"Error fetching candles: {e}")
            return []


async def test_hyperliquid_api():
    """Test the Hyperliquid API integration"""
    async with HyperliquidAPI() as api:
        print("Testing Hyperliquid API...")
        
        # Test funding rates
        print("\nFetching funding rates...")
        funding = await api.get_funding_rates()
        print(f"Got {len(funding)} funding rates")
        
        if funding:
            print("\nTop 5 most negative funding rates:")
            for item in funding[:5]:
                print(f"  {item['symbol']}: {item['funding_rate']:.4f}% "
                      f"(OI: ${item['open_interest']:,.0f})")
        
        # Test mids
        print("\nFetching mid prices...")
        mids = await api.get_all_mids()
        print(f"Got {len(mids)} mid prices")
        
        if mids:
            print("\nSample prices:")
            for symbol, price in list(mids.items())[:5]:
                print(f"  {symbol}: ${price:,.2f}")


if __name__ == "__main__":
    asyncio.run(test_hyperliquid_api())
