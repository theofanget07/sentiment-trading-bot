"""Perplexity AI API client wrapper.

Provides a clean interface to interact with Perplexity AI API for:
- Sentiment analysis
- Market recommendations
- News summarization
"""

import os
import logging
import requests
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Wrapper for Perplexity AI API interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key (defaults to PERPLEXITY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not provided")
        
        self.base_url = "https://api.perplexity.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def analyze_crypto_sentiment(self, crypto_symbol: str, text: str) -> Dict:
        """Analyze sentiment for a specific crypto from text.
        
        Args:
            crypto_symbol: Crypto symbol (e.g., 'BTC', 'ETH')
            text: Text to analyze
        
        Returns:
            Dict with sentiment, confidence, reasoning
        """
        prompt = f"""
Analyze the sentiment for {crypto_symbol} based on the following information:

{text}

Provide your analysis in the following format:
1. Sentiment: Bullish/Bearish/Neutral
2. Confidence: Score from 0-100
3. Key Points: 2-3 bullet points explaining your reasoning

Focus on factual analysis and avoid speculation.
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are a crypto market analyst."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse response (simple extraction)
            sentiment = "Neutral"
            confidence = 50
            reasoning = content
            
            if "Bullish" in content:
                sentiment = "Bullish"
            elif "Bearish" in content:
                sentiment = "Bearish"
            
            # Try to extract confidence score
            for line in content.split("\n"):
                if "Confidence" in line:
                    try:
                        confidence = int(''.join(filter(str.isdigit, line)))
                    except:
                        pass
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "reasoning": reasoning,
                "raw_response": content,
            }
        
        except Exception as e:
            logger.error(f"Perplexity API error for {crypto_symbol}: {e}")
            return {
                "sentiment": "Unknown",
                "confidence": 0,
                "reasoning": f"Error: {str(e)}",
                "raw_response": None,
            }
    
    def get_market_recommendation(self, crypto_symbol: str, position_data: Dict) -> Dict:
        """Get BUY/SELL/HOLD recommendation for a crypto position.
        
        Args:
            crypto_symbol: Crypto symbol (e.g., 'BTC')
            position_data: Dict with qty, avg_price, current_price, pnl_pct
        
        Returns:
            Dict with recommendation, reasoning, confidence
        """
        prompt = f"""
Analyze this {crypto_symbol} position and provide a recommendation:

Position Details:
- Quantity: {position_data.get('qty', 'N/A')}
- Average Buy Price: ${position_data.get('avg_price', 'N/A'):,.2f}
- Current Price: ${position_data.get('current_price', 'N/A'):,.2f}
- Unrealized P&L: {position_data.get('pnl_pct', 'N/A')}%

Based on current market conditions, news, and technical analysis:

1. Recommendation: BUY/SELL/HOLD
2. Reasoning: 2-3 key points
3. Confidence: Score from 0-100
4. Risk Level: Low/Medium/High

Provide actionable insights for a retail investor.
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {"role": "system", "content": "You are a professional crypto trading advisor."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Parse recommendation with improved logic
            recommendation = self._extract_recommendation(content)
            confidence = self._extract_confidence(content)
            
            logger.info(
                f"Parsed recommendation for {crypto_symbol}: {recommendation} "
                f"(confidence: {confidence}%)"
            )
            
            return {
                "recommendation": recommendation,
                "reasoning": content,
                "confidence": confidence,
                "raw_response": content,
            }
        
        except Exception as e:
            logger.error(f"Perplexity API error for recommendation {crypto_symbol}: {e}")
            return {
                "recommendation": "HOLD",
                "reasoning": f"Error: {str(e)}",
                "confidence": 0,
                "raw_response": None,
            }
    
    def _extract_recommendation(self, content: str) -> str:
        """Extract BUY/SELL/HOLD recommendation from AI response.
        
        Looks for structured format like:
        - "1. Recommendation: BUY"
        - "Recommendation: HOLD"
        - "**Recommendation**: SELL"
        
        Args:
            content: AI response text
        
        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        # Try structured patterns first (highest priority)
        patterns = [
            r"1\.\s*Recommendation:\s*(BUY|SELL|HOLD)",  # "1. Recommendation: BUY"
            r"Recommendation:\s*\*\*?(BUY|SELL|HOLD)\*\*?",  # "Recommendation: **BUY**"
            r"\*\*Recommendation\*\*:\s*(BUY|SELL|HOLD)",  # "**Recommendation**: BUY"
            r"Action:\s*(BUY|SELL|HOLD)",  # "Action: BUY"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                rec = match.group(1).upper()
                logger.debug(f"Extracted recommendation '{rec}' using pattern: {pattern}")
                return rec
        
        # Fallback: Look for standalone keywords (less reliable)
        # But avoid false positives like "don't BUY" or "avoid SELL"
        content_upper = content.upper()
        
        # Check for negative context
        negative_patterns = [
            r"DON'?T\s+(BUY|SELL)",
            r"AVOID\s+(BUY|SELL)",
            r"NOT\s+(BUY|SELL)",
        ]
        
        for neg_pattern in negative_patterns:
            if re.search(neg_pattern, content_upper):
                logger.debug("Found negative context, defaulting to HOLD")
                return "HOLD"
        
        # Count occurrences of each action
        buy_count = len(re.findall(r'\bBUY\b', content_upper))
        sell_count = len(re.findall(r'\bSELL\b', content_upper))
        hold_count = len(re.findall(r'\bHOLD\b', content_upper))
        
        logger.debug(f"Keyword counts - BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}")
        
        # Return most frequent (with BUY/SELL priority over HOLD if tied)
        if buy_count > sell_count and buy_count > hold_count:
            return "BUY"
        elif sell_count > buy_count and sell_count > hold_count:
            return "SELL"
        elif hold_count > 0:
            return "HOLD"
        
        # Default to HOLD if nothing found
        logger.warning("Could not extract clear recommendation, defaulting to HOLD")
        return "HOLD"
    
    def _extract_confidence(self, content: str) -> int:
        """Extract confidence score from AI response.
        
        Looks for patterns like:
        - "Confidence: 75"
        - "Confidence Score: 85"
        - "75%"
        - "Score: 80"
        
        Args:
            content: AI response text
        
        Returns:
            Confidence score (0-100), defaults to 60 if not found
        """
        patterns = [
            r"Confidence(?:\s+Score)?:\s*(\d{1,3})",  # "Confidence: 75" or "Confidence Score: 75"
            r"(\d{1,3})%",  # "75%"
            r"Score:\s*(\d{1,3})",  # "Score: 80"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    confidence = int(match)
                    if 0 <= confidence <= 100:
                        logger.debug(f"Extracted confidence {confidence}% using pattern: {pattern}")
                        return confidence
                except ValueError:
                    continue
        
        # Default to medium confidence
        logger.debug("Could not extract confidence, defaulting to 60%")
        return 60
    
    def get_crypto_news_summary(self, crypto_symbols: List[str]) -> str:
        """Get latest news summary for multiple cryptos.
        
        Args:
            crypto_symbols: List of crypto symbols (e.g., ['BTC', 'ETH'])
        
        Returns:
            Formatted news summary string
        """
        symbols_str = ", ".join(crypto_symbols)
        prompt = f"""
Provide a brief market update for these cryptocurrencies: {symbols_str}

Include:
1. Most important news from the last 24 hours
2. Major price movements
3. Key market sentiment

Keep it concise (under 300 words) and focus on actionable information.
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {"role": "system", "content": "You are a crypto news analyst."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"Perplexity API error for news summary: {e}")
            return "Unable to fetch news summary at this time."


# Singleton instance
_client = None


def get_perplexity_client() -> PerplexityClient:
    """Get or create Perplexity client singleton."""
    global _client
    if _client is None:
        _client = PerplexityClient()
    return _client
