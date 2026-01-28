"""News fetcher for crypto RSS feeds and Reddit."""
import os
import feedparser
import praw
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from dotenv import load_dotenv

from database import get_db_session
from models import Article

load_dotenv()
logger = logging.getLogger(__name__)

# RSS Feed URLs
RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Bitcoin.com": "https://news.bitcoin.com/feed/",
    "Decrypt": "https://decrypt.co/feed",
    "CryptoSlate": "https://cryptoslate.com/feed/",
}

# Reddit Configuration
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "sentiment-bot/1.0")

SUBREDDITS = [
    "cryptocurrency",
    "bitcoin",
    "CryptoMarkets",
    "CryptoCurrency",
]

class NewsFetcher:
    """Fetch crypto news from RSS feeds and Reddit."""
    
    def __init__(self):
        """Initialize news fetcher."""
        self.reddit_client = None
        if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            try:
                self.reddit_client = praw.Reddit(
                    client_id=REDDIT_CLIENT_ID,
                    client_secret=REDDIT_CLIENT_SECRET,
                    user_agent=REDDIT_USER_AGENT,
                )
                logger.info("✅ Reddit client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Reddit client: {e}")
    
    def fetch_rss_articles(self, hours_back: int = 6) -> List[Dict]:
        """Fetch articles from RSS feeds.
        
        Args:
            hours_back: How many hours back to fetch articles (default 6)
            
        Returns:
            List of article dictionaries
        """
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for source, feed_url in RSS_FEEDS.items():
            try:
                logger.info(f"🔍 Fetching from {source}...")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries:
                    # Parse published date
                    published_at = None
                    if hasattr(entry, 'published_parsed'):
                        published_at = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed'):
                        published_at = datetime(*entry.updated_parsed[:6])
                    
                    # Skip old articles
                    if published_at and published_at < cutoff_time:
                        continue
                    
                    article = {
                        'url': entry.get('link', ''),
                        'title': entry.get('title', ''),
                        'source': source,
                        'content': entry.get('summary', ''),
                        'published_at': published_at or datetime.now(),
                    }
                    
                    if article['url'] and article['title']:
                        articles.append(article)
                        logger.info(f"  ✅ {article['title'][:60]}...")
                
                logger.info(f"✅ Fetched {len([a for a in articles if a['source'] == source])} articles from {source}")
                
            except Exception as e:
                logger.error(f"❌ Error fetching from {source}: {e}")
        
        logger.info(f"🎯 Total RSS articles: {len(articles)}")
        return articles
    
    def fetch_reddit_posts(self, hours_back: int = 6, limit: int = 25) -> List[Dict]:
        """Fetch top posts from crypto subreddits.
        
        Args:
            hours_back: How many hours back to fetch posts (default 6)
            limit: Number of posts per subreddit (default 25)
            
        Returns:
            List of post dictionaries
        """
        if not self.reddit_client:
            logger.warning("⚠️ Reddit client not initialized, skipping Reddit fetch")
            return []
        
        posts = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for subreddit_name in SUBREDDITS:
            try:
                logger.info(f"🔍 Fetching from r/{subreddit_name}...")
                subreddit = self.reddit_client.subreddit(subreddit_name)
                
                for submission in subreddit.hot(limit=limit):
                    created_at = datetime.fromtimestamp(submission.created_utc)
                    
                    # Skip old posts
                    if created_at < cutoff_time:
                        continue
                    
                    # Skip if not enough text
                    if len(submission.title) < 20:
                        continue
                    
                    post = {
                        'url': f"https://reddit.com{submission.permalink}",
                        'title': submission.title,
                        'source': f"Reddit-{subreddit_name}",
                        'content': submission.selftext[:500] if submission.selftext else '',
                        'published_at': created_at,
                    }
                    
                    posts.append(post)
                    logger.info(f"  ✅ {post['title'][:60]}...")
                
                logger.info(f"✅ Fetched {len([p for p in posts if subreddit_name in p['source']])} posts from r/{subreddit_name}")
                
            except Exception as e:
                logger.error(f"❌ Error fetching from r/{subreddit_name}: {e}")
        
        logger.info(f"🎯 Total Reddit posts: {len(posts)}")
        return posts
    
    def save_articles_to_db(self, articles: List[Dict]) -> int:
        """Save articles to database (avoiding duplicates).
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Number of new articles saved
        """
        saved_count = 0
        
        with get_db_session() as db:
            for article_data in articles:
                try:
                    # Check if article already exists
                    existing = db.query(Article).filter(
                        Article.url == article_data['url']
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create new article
                    article = Article(
                        url=article_data['url'],
                        title=article_data['title'],
                        source=article_data['source'],
                        content=article_data['content'],
                        published_at=article_data['published_at'],
                        fetched_at=datetime.now(),
                        is_analyzed=False,
                    )
                    
                    db.add(article)
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error saving article {article_data.get('url')}: {e}")
        
        logger.info(f"💾 Saved {saved_count} new articles to database")
        return saved_count
    
    def fetch_and_save_all(self, hours_back: int = 6) -> Dict[str, int]:
        """Fetch from all sources and save to database.
        
        Args:
            hours_back: How many hours back to fetch (default 6)
            
        Returns:
            Dictionary with stats
        """
        logger.info(f"🚀 Starting news fetch (last {hours_back} hours)...")
        
        # Fetch from RSS
        rss_articles = self.fetch_rss_articles(hours_back=hours_back)
        
        # Fetch from Reddit
        reddit_posts = self.fetch_reddit_posts(hours_back=hours_back)
        
        # Combine all
        all_articles = rss_articles + reddit_posts
        
        # Save to database
        saved_count = self.save_articles_to_db(all_articles)
        
        stats = {
            'rss_fetched': len(rss_articles),
            'reddit_fetched': len(reddit_posts),
            'total_fetched': len(all_articles),
            'saved_to_db': saved_count,
        }
        
        logger.info(f"✅ Fetch complete: {stats}")
        return stats

if __name__ == "__main__":
    # Test fetcher when run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    fetcher = NewsFetcher()
    stats = fetcher.fetch_and_save_all(hours_back=24)
    
    print(f"\n📋 FETCH STATS:")
    print(f"  RSS articles: {stats['rss_fetched']}")
    print(f"  Reddit posts: {stats['reddit_fetched']}")
    print(f"  Total fetched: {stats['total_fetched']}")
    print(f"  Saved to DB: {stats['saved_to_db']}")
