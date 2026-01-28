"""Test script for article_scraper.py

Tests URL scraping with 5 different crypto news sources.
Run: python test_article_scraper.py
"""

import sys
import time
from article_scraper import extract_article, extract_urls, is_valid_url

# Test URLs from different crypto news sites
TEST_URLS = [
    # CoinDesk
    "https://www.coindesk.com/markets/",
    
    # CoinTelegraph
    "https://cointelegraph.com/news",
    
    # Bitcoin.com
    "https://news.bitcoin.com/",
    
    # Decrypt
    "https://decrypt.co/news",
    
    # The Block
    "https://www.theblock.co/latest",
]

# Alternative: Use specific article URLs if above don't work
SPECIFIC_ARTICLE_URLS = [
    "https://www.coindesk.com/policy/",
    "https://cointelegraph.com/tags/bitcoin",
    "https://decrypt.co/resources/what-is-bitcoin",
]

def test_url_detection():
    """Test URL extraction from text."""
    print("\n" + "="*70)
    print("TEST 1: URL DETECTION")
    print("="*70)
    
    test_cases = [
        "Check this out https://coindesk.com/article amazing!",
        "Multiple URLs: https://google.com and https://bitcoin.com/news",
        "No URL here just text",
        "https://cointelegraph.com/news/btc-rally",
    ]
    
    for text in test_cases:
        urls = extract_urls(text)
        print(f"\nText: {text[:50]}...")
        print(f"Found URLs: {urls if urls else 'None'}")
        print(f"Is valid: {is_valid_url(text) if urls else 'N/A'}")
    
    print("\n✅ URL detection test complete")

def test_article_scraping():
    """Test article scraping from real URLs."""
    print("\n\n" + "="*70)
    print("TEST 2: ARTICLE SCRAPING (5 URLs)")
    print("="*70)
    
    results = []
    
    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n[{i}/5] Testing: {url}")
        print("-" * 70)
        
        start_time = time.time()
        article_text = extract_article(url)
        elapsed = time.time() - start_time
        
        if article_text:
            char_count = len(article_text)
            word_count = len(article_text.split())
            
            print(f"✅ SUCCESS")
            print(f"   - Time: {elapsed:.2f}s")
            print(f"   - Characters: {char_count:,}")
            print(f"   - Words: {word_count:,}")
            print(f"   - Preview: {article_text[:150]}...")
            
            results.append({
                'url': url,
                'success': True,
                'chars': char_count,
                'time': elapsed
            })
        else:
            print(f"❌ FAILED")
            print(f"   - Time: {elapsed:.2f}s")
            print(f"   - Could not extract article content")
            
            results.append({
                'url': url,
                'success': False,
                'chars': 0,
                'time': elapsed
            })
        
        # Small delay between requests
        if i < len(TEST_URLS):
            time.sleep(0.5)
    
    return results

def test_error_handling():
    """Test error handling with invalid URLs."""
    print("\n\n" + "="*70)
    print("TEST 3: ERROR HANDLING")
    print("="*70)
    
    error_test_cases = [
        "https://this-site-definitely-does-not-exist-12345.com",
        "https://httpstat.us/404",  # Returns 404
        "https://httpstat.us/500",  # Returns 500
    ]
    
    for url in error_test_cases:
        print(f"\nTesting: {url}")
        result = extract_article(url)
        if result is None:
            print("✅ Correctly handled error (returned None)")
        else:
            print("⚠️ Unexpected success")
    
    print("\n✅ Error handling test complete")

def print_summary(results):
    """Print test summary."""
    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
    
    total_chars = sum(r['chars'] for r in results)
    avg_time = sum(r['time'] for r in results) / total_count if total_count > 0 else 0
    
    print(f"\n🎯 Success Rate: {success_count}/{total_count} ({success_rate:.1f}%)")
    print(f"⏱️  Average Time: {avg_time:.2f}s")
    print(f"📊 Total Characters Extracted: {total_chars:,}")
    
    if success_count >= 3:
        print("\n✅ 🎉 TESTS PASSED - Article scraper is working!")
        print("\nNext steps:")
        print("1. Test the Telegram bot with real URLs")
        print("2. Try: https://www.coindesk.com/markets/")
        print("3. Try: https://cointelegraph.com/news")
    else:
        print("\n⚠️ Some tests failed. Check logs above.")
        print("\nTry using specific article URLs instead:")
        for url in SPECIFIC_ARTICLE_URLS:
            print(f"  - {url}")
    
    print("\n" + "="*70)

def main():
    print("\n🚀 ARTICLE SCRAPER TEST SUITE")
    print("Testing URL extraction and article scraping...\n")
    
    try:
        # Run all tests
        test_url_detection()
        results = test_article_scraping()
        test_error_handling()
        print_summary(results)
        
        return 0 if sum(1 for r in results if r['success']) >= 3 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
