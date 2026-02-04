"""Fetch real-time crypto prices from CoinGecko API.

Free tier limits:
- 50 calls/minute
- Rate limited but sufficient for our use case

Caching strategy:
- Cache prices for 5 minutes to reduce API calls
- Cache stored in-memory (simple dict)
"""
import os
import time
import urllib.request
import urllib.error
import json
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

# Symbol to CoinGecko ID mapping
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "XLM": "stellar",
}

# Simple in-memory cache
_price_cache: Dict[str, tuple[float, float]] = {}  # symbol -> (price, timestamp)
CACHE_TTL_SECONDS = 300  # 5 minutes

def is_symbol_supported(symbol: str) -> bool:
    """Check if crypto symbol is supported.
    
    Args:
        symbol: Crypto symbol (BTC, ETH, etc.)
        
    Returns:
        True if supported, False otherwise
    """
    return symbol.upper() in SYMBOL_TO_ID

def get_crypto_price(symbol: str, force_refresh: bool = False, max_retries: int = 3) -> Optional[float]:
    """Get current price for crypto symbol in USD.
    
    Args:
        symbol: Crypto symbol (BTC, ETH, SOL, etc.)
        force_refresh: Bypass cache and fetch fresh price
        max_retries: Maximum number of API retry attempts
        
    Returns:
        Price in USD or None if error
    """
    symbol = symbol.upper()
    
    # Validate symbol first
    if not is_symbol_supported(symbol):
        logger.warning(f"⚠️ Unknown crypto symbol: {symbol}")
        return None
    
    # Check cache first (unless force refresh)
    if not force_refresh and symbol in _price_cache:
        price, cached_at = _price_cache[symbol]
        age = time.time() - cached_at
        if age < CACHE_TTL_SECONDS:
            logger.debug(f"✅ Cache hit for {symbol}: ${price:.2f} (age: {age:.0f}s)")
            return price
        else:
            logger.debug(f"⏰ Cache expired for {symbol} (age: {age:.0f}s)")
    
    # Map symbol to CoinGecko ID
    coin_id = SYMBOL_TO_ID[symbol]
    
    # Fetch from CoinGecko with retries
    for attempt in range(1, max_retries + 1):
        try:
            url = f"{COINGECKO_API_BASE}/simple/price?ids={coin_id}&vs_currencies=usd"
            logger.info(f"🔍 Fetching {symbol} price from CoinGecko (attempt {attempt}/{max_retries})...")
            
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "sentiment-trading-bot/1.0",
                    "Accept": "application/json",
                },
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            price = data.get(coin_id, {}).get("usd")
            if price is None:
                logger.error(f"❌ No price data for {symbol} (coin_id: {coin_id}). Response: {data}")
                
                # Try cache on last attempt
                if attempt == max_retries and symbol in _price_cache:
                    old_price, _ = _price_cache[symbol]
                    logger.warning(f"⚠️ Using stale cache for {symbol}: ${old_price:.2f}")
                    return old_price
                
                return None
            
            # Update cache
            _price_cache[symbol] = (price, time.time())
            logger.info(f"✅ Fetched price for {symbol}: ${price:,.2f}")
            
            return float(price)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else 'No body'
            logger.error(f"❌ CoinGecko API HTTP error for {symbol} (attempt {attempt}/{max_retries}): {e.code} {e.reason}")
            logger.error(f"   Response body: {error_body}")
            
            # Retry on rate limit (429) or server error (5xx)
            if e.code in [429, 500, 502, 503, 504] and attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                logger.info(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Return cached value on last attempt
            if symbol in _price_cache:
                old_price, _ = _price_cache[symbol]
                logger.warning(f"⚠️ Using stale cache for {symbol}: ${old_price:.2f}")
                return old_price
            
            return None
            
        except urllib.error.URLError as e:
            logger.error(f"❌ Network error fetching {symbol} (attempt {attempt}/{max_retries}): {e.reason}")
            
            # Retry on network error
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Return cached value on last attempt
            if symbol in _price_cache:
                old_price, _ = _price_cache[symbol]
                logger.warning(f"⚠️ Using stale cache for {symbol}: ${old_price:.2f}")
                return old_price
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching price for {symbol} (attempt {attempt}/{max_retries}): {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Retry on unexpected error
            if attempt < max_retries:
                wait_time = 2 ** attempt
                logger.info(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Return cached value on last attempt
            if symbol in _price_cache:
                old_price, _ = _price_cache[symbol]
                logger.warning(f"⚠️ Using stale cache for {symbol}: ${old_price:.2f}")
                return old_price
            
            return None
    
    # Should never reach here
    return None

def get_multiple_prices(symbols: list[str], force_refresh: bool = False) -> Dict[str, Optional[float]]:
    """Get prices for multiple crypto symbols.
    
    Args:
        symbols: List of crypto symbols
        force_refresh: Bypass cache
        
    Returns:
        Dict mapping symbol to price (None if error)
    """
    # Filter to valid symbols
    valid_symbols = [s.upper() for s in symbols if s.upper() in SYMBOL_TO_ID]
    
    if not valid_symbols:
        logger.warning("⚠️ No valid symbols provided to get_multiple_prices")
        return {}
    
    logger.info(f"🔍 Fetching prices for {len(valid_symbols)} symbols: {valid_symbols}")
    
    # Map to CoinGecko IDs
    coin_ids = [SYMBOL_TO_ID[s] for s in valid_symbols]
    ids_param = ",".join(coin_ids)
    
    try:
        url = f"{COINGECKO_API_BASE}/simple/price?ids={ids_param}&vs_currencies=usd"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "sentiment-trading-bot/1.0",
                "Accept": "application/json",
            },
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        logger.info(f"✅ CoinGecko API response received: {len(data)} coins")
        
        # Build result dict
        results = {}
        for symbol in valid_symbols:
            coin_id = SYMBOL_TO_ID[symbol]
            price = data.get(coin_id, {}).get("usd")
            
            if price is not None:
                results[symbol] = float(price)
                _price_cache[symbol] = (float(price), time.time())
                logger.info(f"  {symbol}: ${price:,.2f}")
            else:
                logger.warning(f"⚠️ No price for {symbol} in response")
                # Try cache
                if symbol in _price_cache:
                    old_price, _ = _price_cache[symbol]
                    results[symbol] = old_price
                    logger.warning(f"  Using cached {symbol}: ${old_price:,.2f}")
                else:
                    results[symbol] = None
        
        return results
        
    except urllib.error.HTTPError as e:
        logger.error(f"❌ CoinGecko API HTTP error: {e.code} {e.reason}")
        # Fallback to cache
        return {s: _price_cache.get(s, (None, 0))[0] for s in valid_symbols}
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch multiple prices: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Fallback to cache
        return {s: _price_cache.get(s, (None, 0))[0] for s in valid_symbols}

def calculate_pnl(avg_buy_price: float, current_price: float) -> float:
    """Calculate profit/loss percentage.
    
    Args:
        avg_buy_price: Average buy price
        current_price: Current market price
        
    Returns:
        P&L percentage (positive = profit, negative = loss)
    """
    if avg_buy_price <= 0:
        return 0.0
    
    return ((current_price - avg_buy_price) / avg_buy_price) * 100

def format_price(price: float) -> str:
    """Format price for display.
    
    Args:
        price: Price in USD
        
    Returns:
        Formatted string (e.g., "$45,123.45")
    """
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.2f}"
    else:
        return f"${price:.6f}"

if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    print("Testing CoinGecko price fetcher...")
    print()
    
    # Test single price
    btc_price = get_crypto_price("BTC")
    print(f"BTC: {format_price(btc_price) if btc_price else 'Error'}")
    
    # Test multiple prices
    prices = get_multiple_prices(["BTC", "ETH", "SOL"])
    for symbol, price in prices.items():
        print(f"{symbol}: {format_price(price) if price else 'Error'}")
    
    # Test cache
    print("\nTesting cache (should be instant):")
    btc_price_cached = get_crypto_price("BTC")
    print(f"BTC (cached): {format_price(btc_price_cached) if btc_price_cached else 'Error'}")
    
    # Test P&L calculation
    print("\nTesting P&L calculation:")
    if btc_price:
        pnl = calculate_pnl(40000, btc_price)
        print(f"Bought BTC at $40,000, current: {format_price(btc_price)}")
        print(f"P&L: {pnl:+.2f}%")
