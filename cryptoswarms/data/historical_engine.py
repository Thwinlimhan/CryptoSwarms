"""Real Historical Data Engine for CryptoSwarms.

Replaces fake backtesting with real historical data from Binance API.
Stores data in TimescaleDB for fast retrieval and pattern discovery.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger("cryptoswarms.data.historical")

@dataclass
class DataQualityReport:
    symbol: str
    interval: str
    total_candles: int
    missing_candles: int
    data_gaps: List[tuple[datetime, datetime]]
    outliers: List[dict]
    quality_score: float  # 0-1, where 1 is perfect
    issues: List[str]

@dataclass
class RegimePeriod:
    start_time: datetime
    end_time: datetime
    regime_type: str  # "trending_up", "trending_down", "ranging", "volatile"
    confidence: float
    characteristics: Dict[str, float]

class HistoricalDataEngine:
    """Real historical data engine using Binance API."""
    
    def __init__(self, binance_client, timescale_db):
        self.client = binance_client
        self.db = timescale_db
        self.rate_limiter = asyncio.Semaphore(10)  # Binance rate limits
        
    async def fetch_ohlcv(
        self, 
        symbol: str, 
        interval: str, 
        start_time: datetime, 
        end_time: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        """Fetch real OHLCV data from Binance API."""
        
        async with self.rate_limiter:
            try:
                # Convert to Binance timestamp format
                start_ts = int(start_time.timestamp() * 1000)
                end_ts = int(end_time.timestamp() * 1000)
                
                # Fetch from Binance
                klines = await self.client.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_str=start_ts,
                    end_str=end_ts,
                    limit=limit
                )
                
                if not klines:
                    logger.warning(f"No data returned for {symbol} {interval}")
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Clean and convert data types
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open'] = pd.to_numeric(df['open'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
                # Remove unnecessary columns
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                
                # Validate data quality
                df = self._clean_data(df, symbol, interval)
                
                logger.info(f"Fetched {len(df)} candles for {symbol} {interval}")
                return df
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol} {interval}: {e}")
                return pd.DataFrame()
    
    async def build_comprehensive_dataset(
        self,
        symbols: List[str] = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"],
        intervals: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d"],
        lookback_days: int = 365
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Build comprehensive historical dataset for all symbols and intervals."""
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=lookback_days)
        
        dataset = {}
        
        for symbol in symbols:
            dataset[symbol] = {}
            
            for interval in intervals:
                logger.info(f"Fetching {symbol} {interval} data...")
                
                # Fetch data in chunks to respect rate limits
                data_chunks = []
                current_start = start_time
                
                while current_start < end_time:
                    # Calculate chunk end time (max 1000 candles per request)
                    chunk_duration = self._get_chunk_duration(interval, 1000)
                    current_end = min(current_start + chunk_duration, end_time)
                    
                    # Fetch chunk
                    chunk_data = await self.fetch_ohlcv(
                        symbol=symbol,
                        interval=interval,
                        start_time=current_start,
                        end_time=current_end
                    )
                    
                    if not chunk_data.empty:
                        data_chunks.append(chunk_data)
                    
                    current_start = current_end
                    
                    # Rate limiting delay
                    await asyncio.sleep(0.1)
                
                # Combine chunks
                if data_chunks:
                    combined_data = pd.concat(data_chunks, ignore_index=True)
                    combined_data = combined_data.drop_duplicates(subset=['timestamp'])
                    combined_data = combined_data.sort_values('timestamp')
                    
                    # Store in database
                    await self.store_ohlcv(combined_data, symbol, interval)
                    
                    dataset[symbol][interval] = combined_data
                    logger.info(f"Stored {len(combined_data)} candles for {symbol} {interval}")
                else:
                    dataset[symbol][interval] = pd.DataFrame()
                    logger.warning(f"No data available for {symbol} {interval}")
        
        return dataset
    
    async def store_ohlcv(self, data: pd.DataFrame, symbol: str, interval: str):
        """Store OHLCV data in TimescaleDB with proper indexing."""
        
        if data.empty:
            return
            
        # Add metadata columns
        data = data.copy()
        data['symbol'] = symbol
        data['interval'] = interval
        data['created_at'] = datetime.now(timezone.utc)
        
        # Store in TimescaleDB
        await self.db.insert_ohlcv_batch(data)
        
        logger.info(f"Stored {len(data)} candles for {symbol} {interval} in database")
    
    async def query_data(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """Fast retrieval of historical data for backtesting."""
        
        try:
            data = await self.db.query_ohlcv(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            
            if data.empty:
                logger.warning(f"No data found for {symbol} {interval} between {start_time} and {end_time}")
                return pd.DataFrame()
            
            # Ensure proper sorting
            data = data.sort_values('timestamp')
            
            logger.info(f"Retrieved {len(data)} candles for {symbol} {interval}")
            return data
            
        except Exception as e:
            logger.error(f"Error querying data for {symbol} {interval}: {e}")
            return pd.DataFrame()
    
    def validate_data_quality(self, data: pd.DataFrame, symbol: str, interval: str) -> DataQualityReport:
        """Comprehensive data quality validation."""
        
        if data.empty:
            return DataQualityReport(
                symbol=symbol,
                interval=interval,
                total_candles=0,
                missing_candles=0,
                data_gaps=[],
                outliers=[],
                quality_score=0.0,
                issues=["No data available"]
            )
        
        issues = []
        
        # Check for missing data
        expected_interval = self._get_interval_seconds(interval)
        data_sorted = data.sort_values('timestamp')
        
        gaps = []
        missing_candles = 0
        
        for i in range(1, len(data_sorted)):
            time_diff = (data_sorted.iloc[i]['timestamp'] - data_sorted.iloc[i-1]['timestamp']).total_seconds()
            if time_diff > expected_interval * 1.5:  # Allow 50% tolerance
                gap_start = data_sorted.iloc[i-1]['timestamp']
                gap_end = data_sorted.iloc[i]['timestamp']
                gaps.append((gap_start, gap_end))
                missing_candles += int(time_diff / expected_interval) - 1
        
        if gaps:
            issues.append(f"Found {len(gaps)} data gaps")
        
        # Check for price outliers (>10% moves in single candle)
        outliers = []
        for i, row in data.iterrows():
            if row['high'] > row['low'] * 1.1:  # >10% range in single candle
                outliers.append({
                    'timestamp': row['timestamp'],
                    'type': 'high_range',
                    'range_pct': (row['high'] - row['low']) / row['low']
                })
        
        if outliers:
            issues.append(f"Found {len(outliers)} price outliers")
        
        # Check for zero/negative prices
        invalid_prices = data[(data['open'] <= 0) | (data['high'] <= 0) | 
                             (data['low'] <= 0) | (data['close'] <= 0)]
        if not invalid_prices.empty:
            issues.append(f"Found {len(invalid_prices)} invalid prices")
        
        # Check for zero volume
        zero_volume = data[data['volume'] == 0]
        if not zero_volume.empty:
            issues.append(f"Found {len(zero_volume)} zero volume candles")
        
        # Calculate quality score
        quality_score = 1.0
        quality_score -= min(0.3, len(gaps) / len(data))  # Gap penalty
        quality_score -= min(0.2, len(outliers) / len(data))  # Outlier penalty
        quality_score -= min(0.3, len(invalid_prices) / len(data))  # Invalid price penalty
        quality_score -= min(0.2, len(zero_volume) / len(data))  # Zero volume penalty
        
        return DataQualityReport(
            symbol=symbol,
            interval=interval,
            total_candles=len(data),
            missing_candles=missing_candles,
            data_gaps=gaps,
            outliers=outliers,
            quality_score=max(0.0, quality_score),
            issues=issues
        )
    
    def _clean_data(self, data: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
        """Clean and validate OHLCV data."""
        
        if data.empty:
            return data
        
        # Remove rows with invalid prices
        data = data[(data['open'] > 0) & (data['high'] > 0) & 
                   (data['low'] > 0) & (data['close'] > 0)]
        
        # Ensure OHLC consistency
        data = data[
            (data['high'] >= data['open']) & 
            (data['high'] >= data['close']) &
            (data['low'] <= data['open']) & 
            (data['low'] <= data['close'])
        ]
        
        # Remove extreme outliers (>50% single candle moves)
        for i in range(1, len(data)):
            prev_close = data.iloc[i-1]['close']
            current_open = data.iloc[i]['open']
            
            if abs(current_open - prev_close) / prev_close > 0.5:
                data = data.drop(data.index[i])
        
        return data.reset_index(drop=True)
    
    def _get_chunk_duration(self, interval: str, max_candles: int) -> timedelta:
        """Calculate duration for data chunk based on interval."""
        
        interval_seconds = self._get_interval_seconds(interval)
        total_seconds = interval_seconds * max_candles
        
        return timedelta(seconds=total_seconds)
    
    def _get_interval_seconds(self, interval: str) -> int:
        """Convert interval string to seconds."""
        
        interval_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        
        return interval_map.get(interval, 900)  # Default to 15m

class MarketRegimeClassifier:
    """Classify market regimes for regime-dependent analysis."""
    
    def classify_regime(self, data: pd.DataFrame, window: int = 50) -> pd.Series:
        """Classify market regimes using multiple indicators."""
        
        if len(data) < window:
            return pd.Series(['unknown'] * len(data), index=data.index)
        
        # Calculate indicators
        data = data.copy()
        data['returns'] = data['close'].pct_change()
        data['volatility'] = data['returns'].rolling(window).std()
        data['trend'] = data['close'].rolling(window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
        data['range_ratio'] = (data['high'] - data['low']) / data['close']
        
        regimes = []
        
        for i in range(len(data)):
            if i < window:
                regimes.append('unknown')
                continue
            
            vol = data.iloc[i]['volatility']
            trend = data.iloc[i]['trend']
            range_ratio = data.iloc[i]['range_ratio']
            
            # Classify regime
            vol_threshold = data['volatility'].quantile(0.7)
            trend_threshold = data['trend'].quantile(0.3)
            
            if vol > vol_threshold:
                regime = 'volatile'
            elif abs(trend) < trend_threshold:
                regime = 'ranging'
            elif trend > 0:
                regime = 'trending_up'
            else:
                regime = 'trending_down'
            
            regimes.append(regime)
        
        return pd.Series(regimes, index=data.index)
    
    def get_regime_periods(self, data: pd.DataFrame) -> List[RegimePeriod]:
        """Get distinct regime periods."""
        
        regimes = self.classify_regime(data)
        periods = []
        
        current_regime = None
        start_time = None
        
        for i, (timestamp, regime) in enumerate(zip(data['timestamp'], regimes)):
            if regime != current_regime:
                # End previous period
                if current_regime is not None and start_time is not None:
                    periods.append(RegimePeriod(
                        start_time=start_time,
                        end_time=timestamp,
                        regime_type=current_regime,
                        confidence=0.8,  # TODO: Calculate actual confidence
                        characteristics={}  # TODO: Add regime characteristics
                    ))
                
                # Start new period
                current_regime = regime
                start_time = timestamp
        
        # Add final period
        if current_regime is not None and start_time is not None:
            periods.append(RegimePeriod(
                start_time=start_time,
                end_time=data['timestamp'].iloc[-1],
                regime_type=current_regime,
                confidence=0.8,
                characteristics={}
            ))
        
        return periods