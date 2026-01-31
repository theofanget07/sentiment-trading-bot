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

def get_crypto_price(symbol: str, force_refresh: bool = False) -> Optional[float]:
    """Get current price for crypto symbol in USD.
    
    Args:
        symbol: Crypto symbol (BTC, ETH, SOL, etc.)
        force_refresh: Bypass cache and fetch fresh price
        
    Returns:
        Price in USD or None if error
    """
    symbol = symbol.upper()
    
    # Check cache first (unless force refresh)
    if not force_refresh and symbol in _price_cache:
        price, cached_at = _price_cache[symbol]
        age = time.time() - cached_at
        if age < CACHE_TTL_SECONDS:
            logger.debug(f"Cache hit for {symbol}: ${price:.2f} (age: {age:.0f}s)")
            return price
    
    # Map symbol to CoinGecko ID
    coin_id = SYMBOL_TO_ID.get(symbol)
    if not coin_id:
        logger.warning(f"Unknown crypto symbol: {symbol}")
        return None
    
    # Fetch from CoinGecko
    try:
        url = f"{COINGECKO_API_BASE}/simple/price?ids={coin_id}&vs_currencies=usd"
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
            logger.error(f"No price data for {symbol} (coin_id: {coin_id})")
            return None
        
        # Update cache
        _price_cache[symbol] = (price, time.time())
        logger.info(f"Fetched price for {symbol}: ${price:.2f}")
        
        return price
        
    except urllib.error.HTTPError as e:
        logger.error(f"CoinGecko API error for {symbol}: {e.code} {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {e}")
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
        return {}
    
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
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Build result dict
        results = {}
        for symbol in valid_symbols:
            coin_id = SYMBOL_TO_ID[symbol]
            price = data.get(coin_id, {}).get("usd")
            results[symbol] = price
            
            # Update cache
            if price is not None:
                _price_cache[symbol] = (price, time.time())
        
        logger.info(f"Fetched {len(results)} prices from CoinGecko")
        return results
        
    except Exception as e:
        logger.error(f"Failed to fetch multiple prices: {e}")
        return {s: None for s in valid_symbols}

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
