#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta, timezone
import praw
from prawcore.exceptions import TooManyRequests, RequestException

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class RedditCollector:
    """
    Collects cryptocurrency-related posts from Reddit using PRAW.
    
    Focuses on major crypto subreddits and searches for specific token mentions.
    Handles rate limiting and provides structured data for sentiment analysis.
    """
    
    def __init__(self, config):
        """
        Initialize Reddit collector with configuration.
        
        Args:
            config: Configuration object with Reddit API credentials
        """
        self.config = config
        
        # Primary crypto subreddits (updated 2025 - ordered by quality and activity)
        # Tier 1: Core Communities (highest quality, most active)
        self.crypto_subreddits = [
            'CryptoCurrency',      # 9.9M members, highest quality discussions
            'Bitcoin',             # 7.8M members, BTC ecosystem focus
            'ethereum',            # 3.7M members, ETH ecosystem focus  
            'CryptoMarkets',       # 1.7M members, trading and market analysis
            'CryptoTechnology',    # 1.3M members, technical discussions
            
            # Tier 2: Ecosystem-Specific (2025 additions)
            'solana',              # 449K members, fast-growing SOL ecosystem
            'cardano',             # 700K members, ADA governance and development
            'defi',                # DeFi protocols and yield farming trends
            'web3',                # Web3 infrastructure and emerging trends
            'altcoin',             # 226K members, general altcoin discussions
            
            # Tier 3: Specialized & Exchange-Specific
            'binance',             # 800K members, CEX-specific discussions
            'coinbase',            # 500K members, CEX-specific discussions
            'BitcoinBeginners',    # 690K members, retail sentiment indicator
            # Note: Removed r/avalanche (403 access), SatoshiStreetBets (declining quality) and CryptoMoonShots (requires heavy filtering)
        ]
        
        # Initialize Reddit client
        self.reddit = None
        self.rate_limit_reset = time.time()
        self.requests_made = 0
        self.max_requests_per_minute = 60  # Conservative rate limiting
        
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize PRAW Reddit client with authentication."""
        try:
            self.reddit = praw.Reddit(
                client_id=self.config.REDDIT_CLIENT_ID,
                client_secret=self.config.REDDIT_CLIENT_SECRET,
                user_agent=f"crypto_sentiment_bot/1.0 by {self.config.REDDIT_USERNAME}",
                username=self.config.REDDIT_USERNAME,
                password=self.config.REDDIT_PASSWORD
            )
            
            # Test connection
            logger.info(f"Reddit client initialized, authenticated as: {self.reddit.user.me()}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None
    
    def _check_rate_limit(self):
        """
        Check and enforce rate limiting.
        Reddit API allows 100 requests per minute, we use 60 to be safe.
        """
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.rate_limit_reset >= 60:
            self.requests_made = 0
            self.rate_limit_reset = current_time
        
        # Wait if we're at the limit
        if self.requests_made >= self.max_requests_per_minute:
            sleep_time = 60 - (current_time - self.rate_limit_reset)
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.requests_made = 0
                self.rate_limit_reset = time.time()
        
        self.requests_made += 1
    
    def collect_for_symbol(self, symbol: str, hours_back: int = 6) -> List[Dict]:
        """
        Collect Reddit posts mentioning a specific cryptocurrency symbol.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH', 'NEWCOIN')
            hours_back: How many hours back to search (default 6)
            
        Returns:
            List of structured post data dictionaries
        """
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []
        
        posts = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Search queries for the symbol
        search_queries = [
            symbol,
            f"${symbol}",
            f"{symbol.upper()}",
            f"{symbol.lower()}",
        ]
        
        logger.info(f"Collecting Reddit posts for {symbol} from last {hours_back} hours")
        
        for subreddit_name in self.crypto_subreddits:
            try:
                self._check_rate_limit()
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for symbol mentions in recent posts
                for query in search_queries[:2]:  # Limit queries to avoid rate limits
                    try:
                        self._check_rate_limit()
                        
                        # Search recent posts
                        search_results = subreddit.search(
                            query, 
                            sort='new', 
                            time_filter='day',  # Last 24 hours
                            limit=50  # Max 50 posts per query
                        )
                        
                        for post in search_results:
                            post_time = datetime.fromtimestamp(post.created_utc, timezone.utc)
                            
                            # Only include recent posts
                            if post_time < cutoff_time:
                                continue
                            
                            # Check if symbol is actually mentioned
                            if not self._contains_symbol(post.title + " " + post.selftext, symbol):
                                continue
                            
                            post_data = {
                                'text': f"{post.title} {post.selftext}".strip(),
                                'author': str(post.author) if post.author else 'deleted',
                                'timestamp': post_time.isoformat(),
                                'source': f'reddit_r_{subreddit_name}',
                                'url': f"https://reddit.com{post.permalink}",
                                'score': post.score,
                                'num_comments': post.num_comments,
                                'id': post.id,
                                'subreddit': subreddit_name
                            }
                            
                            posts.append(post_data)
                            
                    except TooManyRequests:
                        logger.warning(f"Rate limited on r/{subreddit_name}, waiting 60 seconds")
                        time.sleep(60)
                    except Exception as e:
                        logger.warning(f"Error searching r/{subreddit_name} for '{query}': {e}")
                        continue
                
                # Also check recent hot posts for mentions
                try:
                    self._check_rate_limit()
                    hot_posts = subreddit.hot(limit=25)
                    
                    for post in hot_posts:
                        post_time = datetime.fromtimestamp(post.created_utc, timezone.utc)
                        
                        if post_time < cutoff_time:
                            continue
                        
                        if not self._contains_symbol(post.title + " " + post.selftext, symbol):
                            continue
                        
                        # Check if we already have this post
                        if any(p['id'] == post.id for p in posts):
                            continue
                        
                        post_data = {
                            'text': f"{post.title} {post.selftext}".strip(),
                            'author': str(post.author) if post.author else 'deleted',
                            'timestamp': post_time.isoformat(),
                            'source': f'reddit_r_{subreddit_name}_hot',
                            'url': f"https://reddit.com{post.permalink}",
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'id': post.id,
                            'subreddit': subreddit_name
                        }
                        
                        posts.append(post_data)
                        
                except Exception as e:
                    logger.warning(f"Error getting hot posts from r/{subreddit_name}: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing subreddit r/{subreddit_name}: {e}")
                continue
        
        # Remove duplicates by ID
        seen_ids = set()
        unique_posts = []
        for post in posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)
        
        logger.info(f"Collected {len(unique_posts)} unique Reddit posts for {symbol}")
        return unique_posts
    
    def collect_general_crypto_sentiment(self, hours_back: int = 2) -> List[Dict]:
        """
        Collect general cryptocurrency sentiment from major subreddits.
        
        Args:
            hours_back: How many hours back to search
            
        Returns:
            List of recent crypto-related posts
        """
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []
        
        posts = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Focus on highest quality subreddits for general sentiment (2025 update)
        priority_subreddits = [
            'CryptoCurrency',      # 9.9M - Best overall quality and moderation
            'CryptoTechnology',    # 1.3M - Technical discussions, less speculation
            'CryptoMarkets',       # 1.7M - Trading-focused market analysis
            'Bitcoin',             # 7.8M - BTC ecosystem sentiment
            'ethereum',            # 3.7M - ETH ecosystem sentiment
            'defi',                # DeFi protocol trends and sentiment
        ]
        
        logger.info(f"Collecting general crypto sentiment from last {hours_back} hours")
        
        for subreddit_name in priority_subreddits:
            try:
                self._check_rate_limit()
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get recent posts
                recent_posts = subreddit.new(limit=50)
                
                for post in recent_posts:
                    post_time = datetime.fromtimestamp(post.created_utc, timezone.utc)
                    
                    if post_time < cutoff_time:
                        continue
                    
                    # Filter for substantial posts (not just links)
                    text = f"{post.title} {post.selftext}".strip()
                    if len(text) < 50:  # Skip very short posts
                        continue
                    
                    post_data = {
                        'text': text,
                        'author': str(post.author) if post.author else 'deleted',
                        'timestamp': post_time.isoformat(),
                        'source': f'reddit_r_{subreddit_name}_general',
                        'url': f"https://reddit.com{post.permalink}",
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'id': post.id,
                        'subreddit': subreddit_name
                    }
                    
                    posts.append(post_data)
                
            except Exception as e:
                logger.error(f"Error collecting general sentiment from r/{subreddit_name}: {e}")
                continue
        
        # Remove duplicates
        seen_ids = set()
        unique_posts = []
        for post in posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)
        
        logger.info(f"Collected {len(unique_posts)} general crypto posts")
        return unique_posts
    
    def _contains_symbol(self, text: str, symbol: str) -> bool:
        """
        Check if text contains the cryptocurrency symbol.
        
        Args:
            text: Text to search in
            symbol: Symbol to search for
            
        Returns:
            True if symbol is found
        """
        if not text:
            return False
        
        text_lower = text.lower()
        symbol_lower = symbol.lower()
        
        # Check various formats
        symbol_patterns = [
            symbol_lower,
            f"${symbol_lower}",
            f" {symbol_lower} ",
            f" {symbol_lower}.",
            f" {symbol_lower},",
            f"({symbol_lower})",
            f"{symbol_lower}-eur",
            f"{symbol_lower}/eur",
        ]
        
        return any(pattern in text_lower for pattern in symbol_patterns)
    
    def get_subreddit_info(self) -> Dict[str, Dict]:
        """
        Get information about monitored subreddits.
        
        Returns:
            Dictionary with subreddit statistics
        """
        if not self.reddit:
            return {}
        
        subreddit_info = {}
        
        for subreddit_name in self.crypto_subreddits[:5]:  # Check first 5 to avoid rate limits
            try:
                self._check_rate_limit()
                subreddit = self.reddit.subreddit(subreddit_name)
                
                subreddit_info[subreddit_name] = {
                    'subscribers': subreddit.subscribers,
                    'active_users': subreddit.active_user_count,
                    'description': subreddit.public_description[:100] + "..." if len(subreddit.public_description) > 100 else subreddit.public_description,
                    'created': datetime.fromtimestamp(subreddit.created_utc, timezone.utc).isoformat()
                }
                
            except Exception as e:
                logger.warning(f"Could not get info for r/{subreddit_name}: {e}")
                subreddit_info[subreddit_name] = {'error': str(e)}
        
        return subreddit_info