"""Article Scraper Module

Extracts clean text from crypto news article URLs.
Supports: CoinDesk, CoinTelegraph, Bitcoin.com, Decrypt, The Block, and more.
"""

import logging
import re
from typing import Optional, Dict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request timeout (seconds)
TIMEOUT = 5

# User agent to avoid blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Site-specific selectors (most reliable tags for article content)
SITE_SELECTORS = {
    'coindesk.com': {
        'article': ['article', 'div.article-content', 'div.content-body'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.advertisement', '.social-share']
    },
    'cointelegraph.com': {
        'article': ['article', 'div.post-content', 'div.post__content'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.promo', '.ad-block']
    },
    'bitcoin.com': {
        'article': ['article', 'div.entry-content', 'div.post-content'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.advertisement']
    },
    'decrypt.co': {
        'article': ['article', 'div.article-body', 'div.post-content'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.ad-wrapper']
    },
    'theblock.co': {
        'article': ['article', 'div.article-content', 'main'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.advertisement']
    },
    'cryptoslate.com': {
        'article': ['article', 'div.post-content', 'div.entry-content'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.ad-unit']
    },
    'cryptonews.com': {
        'article': ['article', 'div.article-body', 'div.post-content'],
        'remove': ['script', 'style', 'nav', 'footer', 'aside', '.advertisement']
    },
    # Generic fallback for unknown sites
    'default': {
        'article': ['article', 'main', 'div.content', 'div.article', 'div.post'],
        'remove': ['script', 'style', 'nav', 'footer', 'header', 'aside', '.ad', '.advertisement', '.social']
    }
}


def get_site_config(url: str) -> Dict:
    """Get site-specific configuration based on URL.
    
    Args:
        url: Article URL
        
    Returns:
        Configuration dict with selectors
    """
    try:
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        # Check if we have specific config for this domain
        for site_domain, config in SITE_SELECTORS.items():
            if site_domain in domain:
                logger.info(f"Using specific config for: {site_domain}")
                return config
        
        logger.info("Using default config")
        return SITE_SELECTORS['default']
    except Exception as e:
        logger.error(f"Error getting site config: {e}")
        return SITE_SELECTORS['default']


def clean_text(text: str) -> str:
    """Clean extracted text by removing extra whitespace and formatting.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Remove multiple newlines
    text = re.sub(r'\n+', '\n', text)
    return text


def extract_article(url: str) -> Optional[str]:
    """Extract article text from URL.
    
    Args:
        url: Article URL to scrape
        
    Returns:
        Extracted article text or None if failed
    """
    try:
        logger.info(f"Scraping article: {url}")
        
        # Fetch the page
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get site-specific configuration
        config = get_site_config(url)
        
        # Remove unwanted elements
        for selector in config['remove']:
            for element in soup.select(selector):
                element.decompose()
        
        # Try to find article content using site-specific selectors
        article_content = None
        for selector in config['article']:
            article_content = soup.select_one(selector)
            if article_content:
                logger.info(f"Found article using selector: {selector}")
                break
        
        # If no article found, try to get all paragraphs as fallback
        if not article_content:
            logger.warning("No article container found, using paragraph fallback")
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text() for p in paragraphs])
                text = clean_text(text)
                
                if len(text) > 100:
                    logger.info(f"Successfully extracted {len(text)} characters using fallback")
                    return text
                else:
                    logger.error("Extracted text too short")
                    return None
        
        # Extract text from article container
        if article_content:
            # Get all text, excluding certain tags
            text = article_content.get_text(separator=' ', strip=True)
            text = clean_text(text)
            
            # Validate minimum length
            if len(text) > 100:
                logger.info(f"Successfully extracted {len(text)} characters")
                return text
            else:
                logger.error("Extracted text too short")
                return None
        
        logger.error("Could not extract article content")
        return None
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout ({TIMEOUT}s) while fetching: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error scraping {url}: {e}")
        return None


def is_valid_url(text: str) -> bool:
    """Check if text contains a valid URL.
    
    Args:
        text: Text to check
        
    Returns:
        True if valid URL found
    """
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except:
        return False


def extract_urls(text: str) -> list:
    """Extract all URLs from text.
    
    Args:
        text: Text containing URLs
        
    Returns:
        List of URLs found
    """
    # Simple URL regex pattern
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    return [url.rstrip('.,;:!?)') for url in urls]  # Remove trailing punctuation


if __name__ == "__main__":
    # Test with sample URLs
    test_urls = [
        "https://www.coindesk.com/markets/2024/01/10/bitcoin-etf-approval-sends-prices-soaring/",
        "https://cointelegraph.com/news/ethereum-upgrade-delayed-developers-say",
        "https://decrypt.co/latest-crypto-market-analysis",
    ]
    
    print("\n" + "="*60)
    print("ARTICLE SCRAPER TEST")
    print("="*60 + "\n")
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        print("-" * 60)
        
        article_text = extract_article(url)
        
        if article_text:
            print(f"✅ Success! Extracted {len(article_text)} characters")
            print(f"\nPreview (first 200 chars):\n{article_text[:200]}...")
        else:
            print("❌ Failed to extract article")
        
        print("-" * 60)
