import os
import time
from typing import Any, Dict, Optional

import requests

# Optional imports for Real APIs
try:
    import tweepy
except ImportError:
    tweepy = None

try:
    import praw
except ImportError:
    praw = None

try:
    from newsapi import NewsApiClient
except ImportError:
    NewsApiClient = None

try:
    import feedparser
except ImportError:
    feedparser = None


def get_fear_greed_index() -> str:
    """
    Fetch the Crypto Fear & Greed Index from alternative.me.
    """
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            item = data["data"][0]
            value = item["value"]
            classification = item["value_classification"]
            return f"Fear & Greed Index: {value} ({classification})"
        return "Error: Could not retrieve Fear & Greed Index."
    except Exception as e:
        return f"Error fetching Fear & Greed Index: {str(e)}"


def get_market_news() -> str:
    """
    Fetch aggregated crypto market news using CryptoPanic API if available.
    """
    api_key = os.getenv("CRYPTOPANIC_API_KEY")
    if not api_key:
        return "Market News Unavailable: CRYPTOPANIC_API_KEY not configured. Set this environment variable to enable real-time crypto news."

    try:
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={api_key}&kind=news&filter=hot"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "results" in data:
            headlines = [f"{i + 1}. {p['title']}" for i, p in enumerate(data["results"][:5])]
            return "CryptoPanic News:\n" + "\n".join(headlines)
        return "Error: No news found via CryptoPanic."
    except Exception as e:
        return f"Error fetching CryptoPanic news: {str(e)}"


def fetch_rss_news(symbol: str = "") -> str:
    """
    Fetch free market news from RSS feeds (CoinDesk, Cointelegraph).
    This provides 'Free' news without requiring API keys.
    """
    if not feedparser:
        return "Error: feedparser library not installed. Cannot fetch RSS news."

    feeds = [("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"), ("Cointelegraph", "https://cointelegraph.com/rss")]

    all_headlines = []

    for name, url in feeds:
        try:
            feed = feedparser.parse(url)
            # Take top 3 from each
            count = 0
            for entry in feed.entries:
                if count >= 3:
                    break
                # If symbol is provided, check if it's in the title/summary (case-insensitive)
                if symbol and symbol.lower() not in entry.title.lower() and symbol.lower() not in entry.summary.lower():
                    continue

                all_headlines.append(f"{entry.title} ({name})")
                count += 1
        except Exception as e:
            all_headlines.append(f"Error fetching {name} feed: {str(e)}")

    if not all_headlines:
        if symbol:
            return f"No RSS news found matching '{symbol}' in recent feeds."
        return "No RSS news found."

    return "Market News (Free RSS):\n" + "\n".join([f"{i + 1}. {h}" for i, h in enumerate(all_headlines[:6])])


class SentimentCache:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        if symbol in self.cache:
            entry = self.cache[symbol]
            if time.time() - entry["time"] < self.ttl:
                return entry
        return None

    def set(self, symbol: str, score: float, description: str):
        self.cache[symbol] = {"time": time.time(), "score": score, "description": description}


_sentiment_cache = SentimentCache()


def get_cached_sentiment_score(symbol: str) -> float:
    """Return cached sentiment score or 0.0 if missing."""
    entry = _sentiment_cache.get(symbol)
    if entry:
        return entry["score"]
    return 0.0


def analyze_social_sentiment(symbol: str) -> str:
    """
    Analyze social sentiment using Tweepy (X) or PRAW (Reddit) if configured.
    """
    # Check cache first (optional, but good for speed)
    # But usually this tool is called explicitly to Refresh.
    # Let's refresh every time this tool is CALLED, but get_cached_sentiment_score uses what's there.

    score = 0.0

    # 1. Twitter / X Analysis
    twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
    twitter_result = "Twitter: API Key missing."

    if twitter_bearer and tweepy:
        try:
            client = tweepy.Client(bearer_token=twitter_bearer)
            # Simple search for recent tweets (read-only)
            query = f"{symbol} -is:retweet lang:en"
            tweets = client.search_recent_tweets(query=query, max_results=10)
            if tweets.data:
                texts = [t.text for t in tweets.data]
                preview = " | ".join([t[:50] + "..." for t in texts[:2]])
                twitter_result = f"Twitter (Real): Found {len(texts)} recent tweets. Preview: {preview}"
                # Mock score calculation from real data
                score += 0.2  # Arbitrary boost for finding volume
            else:
                twitter_result = "Twitter (Real): No recent tweets found."
        except Exception as e:
            twitter_result = f"Twitter Error: {str(e)}"

    # 2. Reddit Analysis
    reddit_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_result = "Reddit: API Keys missing."

    if reddit_id and reddit_secret and praw:
        try:
            reddit = praw.Reddit(client_id=reddit_id, client_secret=reddit_secret, user_agent="agent_zero_crypto_bot/1.0")
            # Search r/cryptocurrency
            subreddit = reddit.subreddit("cryptocurrency")
            posts = subreddit.search(symbol, limit=5, time_filter="day")
            titles = [p.title for p in posts]
            if titles:
                preview = " | ".join(titles[:2])
                reddit_result = f"Reddit (Real): Found {len(titles)} posts in r/CC. Preview: {preview}"
                score += 0.2
            else:
                reddit_result = "Reddit (Real): No recent posts found."
        except Exception as e:
            reddit_result = f"Reddit Error: {str(e)}"

    # Combine results
    final_output = f"{twitter_result}\n{reddit_result}"

    if "API Key missing" in twitter_result and "API Key missing" in reddit_result:
        # No sentiment APIs configured - return neutral score with clear guidance
        score = 0.0  # Neutral score when no data available
        final_output = (
            f"Social Sentiment Unavailable for {symbol}: No sentiment APIs configured.\n"
            "To enable real-time sentiment analysis:\n"
            "1. X (Twitter): Get a Bearer Token from https://developer.x.com/ and set TWITTER_BEARER_TOKEN\n"
            "2. Reddit: Create an app at https://www.reddit.com/prefs/apps and set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET\n"
            "NOTE: Sentiment score defaults to neutral (0.0) when no data sources are configured."
        )

    # Update Cache
    _sentiment_cache.set(symbol, score, final_output)

    return final_output


def fetch_financial_news(symbol: str) -> str:
    """
    Fetch financial news using NewsAPI.
    """
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key or not NewsApiClient:
        return (
            f"Financial News Unavailable for {symbol}: NewsAPI not configured.\n"
            "To enable real financial news feeds, get an API key from https://newsapi.org/ and set NEWSAPI_KEY in your .env file."
        )

    try:
        newsapi = NewsApiClient(api_key=api_key)
        # Search for symbol + crypto or finance
        articles = newsapi.get_everything(q=f"{symbol} crypto", language="en", sort_by="relevancy", page_size=3)

        if articles["status"] == "ok" and articles["articles"]:
            headlines = [f"{i + 1}. {a['title']} ({a['source']['name']})" for i, a in enumerate(articles["articles"])]
            return "Financial Headlines (NewsAPI):\n" + "\n".join(headlines)
        return "NewsAPI: No articles found."
    except Exception as e:
        return f"NewsAPI Error: {str(e)}"
