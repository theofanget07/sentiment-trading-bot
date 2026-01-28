"""Article Scraper V2 - With Jina AI Reader Fallback

Extracts clean text from crypto news article URLs.
Uses Jina AI Reader API as fallback for sites with anti-bot protection.

Jina AI Reader: https://jina.ai/reader
- Free to use
- Bypasses Cloudflare and anti-bot protection
- Returns clean markdown/text
- Works with all major news sites
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
TIMEOUT = 10

# Enhanced headers to look more like a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Jina AI Reader API endpoint
JINA_READER_API = "https://r.jina.ai/"


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
    # Remove markdown headers (# ##, etc.)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    return text


def extract_with_jina(url: str) -> Optional[str]:
    """Extract article using Jina AI Reader API.
    
    Jina AI Reader bypasses anti-bot protection and returns clean text.
    Free to use, no API key required.
    
    Args:
        url: Article URL to scrape
        
    Returns:
        Extracted article text or None if failed
    """
    try:
        logger.info(f"Trying Jina AI Reader for: {url}")
        
        # Jina Reader API: prepend https://r.jina.ai/ to any URL
        jina_url = f"{JINA_READER_API}{url}"
        
        response = requests.get(
            jina_url,
            headers={'Accept': 'text/plain'},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        text = response.text
        text = clean_text(text)
        
        # Validate minimum length
        if len(text) > 100:
            logger.info(f"✅ Jina AI Reader: extracted {len(text)} characters")
            return text
        else:
            logger.warning(f"Jina returned short text: {len(text)} chars")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Jina AI timeout for: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Jina AI error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Jina AI: {e}")
        return None


def extract_with_beautifulsoup(url: str) -> Optional[str]:
    """Extract article using direct scraping with BeautifulSoup.
    
    Args:
        url: Article URL to scrape
        
    Returns:
        Extracted article text or None if failed
    """
    try:
        logger.info(f"Trying direct scraping for: {url}")
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Add Referer
        domain = urlparse(url).netloc
        session.headers['Referer'] = f"https://{domain}/"
        
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.select('script, style, nav, footer, header, aside, .ad, .advertisement'):
            element.decompose()
        
        # Try to find article content
        article_content = None
        for selector in ['article', 'main', '[role="main"]', 'div.content', 'div.article']:
            article_content = soup.select_one(selector)
            if article_content:
                break
        
        # Fallback to paragraphs
        if not article_content:
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text() for p in paragraphs])
                text = clean_text(text)
                
                if len(text) > 100:
                    logger.info(f"✅ Direct scraping: extracted {len(text)} characters (fallback)")
                    return text
        
        if article_content:
            text = article_content.get_text(separator=' ', strip=True)
            text = clean_text(text)
            
            if len(text) > 100:
                logger.info(f"✅ Direct scraping: extracted {len(text)} characters")
                return text
        
        return None
        
    except Exception as e:
        logger.warning(f"Direct scraping failed: {e}")
        return None


def extract_article(url: str) -> Optional[str]:
    """Extract article text from URL.
    
    Strategy:
    1. Try Jina AI Reader first (bypasses anti-bot protection)
    2. If Jina fails, try direct scraping
    
    Args:
        url: Article URL to scrape
        
    Returns:
        Extracted article text or None if all methods failed
    """
    logger.info(f"Starting extraction for: {url}")
    
    # Try Jina AI Reader first (most reliable)
    text = extract_with_jina(url)
    if text:
        return text
    
    logger.info("Jina failed, trying direct scraping...")
    
    # Fallback to direct scraping
    text = extract_with_beautifulsoup(url)
    if text:
        return text
    
    logger.error(f"All extraction methods failed for: {url}")
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
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    return [url.rstrip('.,;:!?)') for url in urls]


if __name__ == "__main__":
    # Test with real crypto news URLs
    test_urls = [
        "https://www.coindesk.com/learn/what-is-bitcoin/",
        "https://cointelegraph.com/learn/what-is-bitcoin",
        "https://decrypt.co/resources/what-is-bitcoin",
    ]
    
    print("\n" + "="*70)
    print("ARTICLE SCRAPER V2 TEST (with Jina AI Reader)")
    print("="*70 + "\n")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing: {url}")
        print("-" * 70)
        
        article_text = extract_article(url)
        
        if article_text:
            print(f"✅ SUCCESS - Extracted {len(article_text):,} characters")
            print(f"\nPreview (first 200 chars):\n{article_text[:200]}...")
        else:
            print("❌ FAILED - Could not extract article")
        
        print("-" * 70)
    
    print("\n" + "="*70)
    print("Test complete!")
    print("="*70 + "\n")
