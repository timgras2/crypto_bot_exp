#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
import threading
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from .reddit_collector import RedditCollector
from .discord_collector import DiscordCollector
from .telegram_collector import TelegramCollector
from .sentiment_analyzer import CryptoSentimentProcessor
from .sentiment_cache import SentimentCache

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class MultiSourceDataCollector:
    """
    Unified data collector that aggregates sentiment from multiple social media sources.
    
    Coordinates Reddit, Discord, and potentially other sources to provide
    comprehensive sentiment analysis for cryptocurrency symbols.
    """
    
    def __init__(self, config):
        """
        Initialize multi-source data collector.
        
        Args:
            config: Configuration object with API credentials and settings
        """
        self.config = config
        self.cache = SentimentCache()
        self.sentiment_processor = CryptoSentimentProcessor()
        
        # Initialize collectors based on available configuration
        self.collectors = {}
        
        # Reddit collector (recommended - free and reliable)
        if self._has_reddit_config():
            try:
                self.collectors['reddit'] = RedditCollector(config)
                logger.info("Reddit collector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Reddit collector: {e}")
        
        # Discord collector (optional - requires bot setup)
        if self._has_discord_config():
            try:
                self.collectors['discord'] = DiscordCollector(config)
                logger.info("Discord collector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Discord collector: {e}")
        
        # Telegram collector (optional - requires API credentials)
        if self._has_telegram_config():
            try:
                self.collectors['telegram'] = TelegramCollector(config)
                logger.info("Telegram collector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram collector: {e}")
        
        if not self.collectors:
            logger.error("No social media collectors could be initialized!")
        else:
            logger.info(f"Initialized collectors: {list(self.collectors.keys())}")
        
        # Threading for concurrent collection
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="sentiment_collector")
        self.active_monitoring = {}  # symbol -> monitoring info
        self.monitoring_lock = threading.Lock()
    
    def _has_reddit_config(self) -> bool:
        """Check if Reddit configuration is available."""
        required_attrs = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USERNAME', 'REDDIT_PASSWORD']
        return all(hasattr(self.config, attr) and getattr(self.config, attr) for attr in required_attrs)
    
    def _has_discord_config(self) -> bool:
        """Check if Discord configuration is available."""
        return hasattr(self.config, 'DISCORD_BOT_TOKEN') and self.config.DISCORD_BOT_TOKEN
    
    def _has_telegram_config(self) -> bool:
        """Check if Telegram configuration is available."""
        required_attrs = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_PHONE_NUMBER']
        return all(hasattr(self.config, attr) and getattr(self.config, attr) for attr in required_attrs)
    
    def collect_for_symbol(self, symbol: str, hours_back: int = 6) -> Dict:
        """
        Collect and analyze sentiment for a specific cryptocurrency symbol.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            hours_back: Hours back to search for mentions
            
        Returns:
            Aggregated sentiment analysis result
        """
        logger.info(f"Collecting sentiment data for {symbol} ({hours_back}h back)")
        
        # Check cache first
        cached_sentiment = self.cache.get_sentiment(symbol)
        if cached_sentiment:
            logger.info(f"Using cached sentiment for {symbol}")
            return cached_sentiment
        
        # Collect raw posts from all sources concurrently
        all_posts = []
        collection_results = {}
        
        # Submit collection tasks
        futures = {}
        for source_name, collector in self.collectors.items():
            future = self.executor.submit(
                self._collect_from_source,
                source_name, collector, symbol, hours_back
            )
            futures[future] = source_name
        
        # Gather results
        for future in as_completed(futures):
            source_name = futures[future]
            try:
                posts = future.result(timeout=30)  # 30 second timeout per source
                all_posts.extend(posts)
                collection_results[source_name] = len(posts)
                logger.info(f"Collected {len(posts)} posts from {source_name} for {symbol}")
            except Exception as e:
                logger.error(f"Error collecting from {source_name}: {e}")
                collection_results[source_name] = 0
        
        if not all_posts:
            logger.warning(f"No posts found for {symbol}")
            return self._create_empty_sentiment_result(symbol, collection_results)
        
        # Store raw posts in cache
        self.cache.store_raw_posts(symbol, all_posts)
        
        # Process sentiment
        sentiment_result = self._process_sentiment(symbol, all_posts, collection_results)
        
        # Store processed sentiment in cache
        self.cache.store_sentiment(symbol, sentiment_result)
        
        return sentiment_result
    
    def _collect_from_source(self, source_name: str, collector, symbol: str, hours_back: int) -> List[Dict]:
        """
        Collect posts from a specific source.
        
        Args:
            source_name: Name of the source
            collector: Collector instance
            symbol: Symbol to search for
            hours_back: Hours back to search
            
        Returns:
            List of collected posts
        """
        try:
            if hasattr(collector, 'collect_for_symbol'):
                return collector.collect_for_symbol(symbol, hours_back)
            else:
                logger.warning(f"Collector {source_name} doesn't support collect_for_symbol")
                return []
        except Exception as e:
            logger.error(f"Error in {source_name} collector: {e}")
            return []
    
    def _process_sentiment(self, symbol: str, posts: List[Dict], collection_results: Dict) -> Dict:
        """
        Process raw posts into sentiment analysis.
        
        Args:
            symbol: Cryptocurrency symbol
            posts: List of raw posts
            collection_results: Collection statistics by source
            
        Returns:
            Processed sentiment result
        """
        logger.info(f"Processing sentiment for {len(posts)} posts about {symbol}")
        
        # Process each post through sentiment analysis
        processed_posts = []
        total_posts = len(posts)
        filtered_spam = 0
        
        for post in posts:
            processed = self.sentiment_processor.process_social_post(post)
            if processed:
                processed_posts.append(processed)
            else:
                filtered_spam += 1
        
        if not processed_posts:
            logger.warning(f"All {total_posts} posts for {symbol} were filtered as spam")
            return self._create_empty_sentiment_result(symbol, collection_results)
        
        logger.info(f"Processed {len(processed_posts)} posts for {symbol} (filtered {filtered_spam} spam)")
        
        # Calculate aggregated sentiment
        sentiment_scores = [post['sentiment_compound'] for post in processed_posts]
        confidence_scores = [post['confidence'] for post in processed_posts]
        
        # Weighted average (confidence-weighted sentiment)
        if confidence_scores and sum(confidence_scores) > 0:
            weighted_sentiment = sum(s * c for s, c in zip(sentiment_scores, confidence_scores)) / sum(confidence_scores)
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            weighted_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            avg_confidence = 0.3  # Low confidence if no confidence scores
        
        # Sentiment distribution
        positive_posts = sum(1 for s in sentiment_scores if s > 0.05)
        negative_posts = sum(1 for s in sentiment_scores if s < -0.05)
        neutral_posts = len(sentiment_scores) - positive_posts - negative_posts
        
        # Detect potential pump patterns
        pump_indicators = self._detect_pump_patterns(processed_posts)
        
        # Source breakdown
        source_breakdown = {}
        for post in processed_posts:
            source = post['source'].split('_')[0]  # Extract main source (reddit/discord)
            if source not in source_breakdown:
                source_breakdown[source] = {'count': 0, 'avg_sentiment': 0}
            source_breakdown[source]['count'] += 1
        
        # Calculate average sentiment per source
        for source in source_breakdown:
            source_posts = [p for p in processed_posts if p['source'].startswith(source)]
            if source_posts:
                source_sentiment = sum(p['sentiment_compound'] for p in source_posts) / len(source_posts)
                source_breakdown[source]['avg_sentiment'] = source_sentiment
        
        result = {
            'symbol': symbol.upper(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'aggregated_sentiment': weighted_sentiment,
            'confidence': avg_confidence,
            'total_posts': total_posts,
            'processed_posts': len(processed_posts),
            'filtered_spam': filtered_spam,
            'sentiment_distribution': {
                'positive': positive_posts,
                'negative': negative_posts,
                'neutral': neutral_posts
            },
            'sentiment_strength': self._get_sentiment_strength(weighted_sentiment),
            'pump_detected': pump_indicators['likely_pump'],
            'pump_score': pump_indicators['pump_score'],
            'mention_count': total_posts,
            'source_breakdown': source_breakdown,
            'collection_results': collection_results,
            'data_freshness_hours': 1  # Data is fresh since just collected
        }
        
        return result
    
    def _detect_pump_patterns(self, posts: List[Dict]) -> Dict:
        """
        Detect potential pump and dump patterns in posts.
        
        Args:
            posts: List of processed posts
            
        Returns:
            Dictionary with pump detection results
        """
        if not posts:
            return {'likely_pump': False, 'pump_score': 0.0, 'indicators': []}
        
        indicators = []
        pump_score = 0.0
        
        # Indicator 1: High volume of posts in short time
        timestamps = [datetime.fromisoformat(post['timestamp']) for post in posts]
        if len(timestamps) > 1:
            time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600  # hours
            posts_per_hour = len(posts) / max(time_span, 0.1)
            
            if posts_per_hour > 10:  # More than 10 posts per hour
                indicators.append('high_volume')
                pump_score += 0.3
        
        # Indicator 2: Extremely positive sentiment with low confidence
        very_positive_low_conf = sum(1 for p in posts 
                                   if p['sentiment_compound'] > 0.7 and p['confidence'] < 0.4)
        if very_positive_low_conf > len(posts) * 0.3:
            indicators.append('suspicious_positivity')
            pump_score += 0.4
        
        # Indicator 3: Repetitive language patterns
        texts = [post['text'].lower() for post in posts]
        common_phrases = ['to the moon', 'buy now', 'pump', 'moon', 'rocket']
        phrase_counts = {phrase: sum(1 for text in texts if phrase in text) for phrase in common_phrases}
        high_phrase_usage = sum(1 for count in phrase_counts.values() if count > len(posts) * 0.4)
        
        if high_phrase_usage >= 2:
            indicators.append('repetitive_phrases')
            pump_score += 0.3
        
        # Final determination
        likely_pump = pump_score > 0.5 and len(indicators) >= 2
        
        return {
            'likely_pump': likely_pump,
            'pump_score': pump_score,
            'indicators': indicators,
            'phrase_counts': phrase_counts
        }
    
    def _get_sentiment_strength(self, sentiment_score: float) -> str:
        """Get sentiment strength label."""
        abs_score = abs(sentiment_score)
        if abs_score >= 0.8:
            return 'very_strong'
        elif abs_score >= 0.6:
            return 'strong'
        elif abs_score >= 0.3:
            return 'moderate'
        else:
            return 'weak'
    
    def _create_empty_sentiment_result(self, symbol: str, collection_results: Dict) -> Dict:
        """Create empty sentiment result when no data is available."""
        return {
            'symbol': symbol.upper(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'aggregated_sentiment': 0.0,
            'confidence': 0.0,
            'total_posts': 0,
            'processed_posts': 0,
            'filtered_spam': 0,
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'sentiment_strength': 'weak',
            'pump_detected': False,
            'pump_score': 0.0,
            'mention_count': 0,
            'source_breakdown': {},
            'collection_results': collection_results,
            'data_freshness_hours': 0
        }
    
    def start_monitoring(self, symbol: str):
        """
        Start continuous monitoring for a symbol.
        
        Args:
            symbol: Symbol to monitor
        """
        with self.monitoring_lock:
            if symbol not in self.active_monitoring:
                # Start Discord monitoring if available
                if 'discord' in self.collectors:
                    self.collectors['discord'].start_monitoring(symbol)
                
                self.active_monitoring[symbol] = {
                    'started_at': datetime.now(timezone.utc),
                    'last_collection': None
                }
                
                logger.info(f"Started monitoring {symbol}")
    
    def stop_monitoring(self, symbol: str):
        """
        Stop monitoring a symbol.
        
        Args:
            symbol: Symbol to stop monitoring
        """
        with self.monitoring_lock:
            if symbol in self.active_monitoring:
                del self.active_monitoring[symbol]
                logger.info(f"Stopped monitoring {symbol}")
    
    def get_monitoring_status(self) -> Dict:
        """
        Get status of active monitoring.
        
        Returns:
            Dictionary with monitoring status
        """
        with self.monitoring_lock:
            status = {
                'active_symbols': list(self.active_monitoring.keys()),
                'total_active': len(self.active_monitoring),
                'collectors_available': list(self.collectors.keys()),
                'cache_stats': self.cache.get_cache_stats()
            }
            
            # Add individual symbol status
            for symbol, info in self.active_monitoring.items():
                status[f'{symbol}_status'] = {
                    'monitoring_duration': str(datetime.now(timezone.utc) - info['started_at']),
                    'last_collection': info.get('last_collection')
                }
        
        return status
    
    def cleanup_old_data(self):
        """Clean up old cached data."""
        self.cache.cleanup_old_data()
    
    def get_collector_info(self) -> Dict:
        """
        Get information about available collectors.
        
        Returns:
            Dictionary with collector information
        """
        info = {
            'collectors': {},
            'total_collectors': len(self.collectors)
        }
        
        for name, collector in self.collectors.items():
            try:
                if name == 'reddit' and hasattr(collector, 'get_subreddit_info'):
                    info['collectors'][name] = {
                        'type': 'Reddit',
                        'status': 'active',
                        'subreddits': collector.get_subreddit_info()
                    }
                elif name == 'discord' and hasattr(collector, 'get_server_info'):
                    info['collectors'][name] = {
                        'type': 'Discord',
                        'status': 'active',
                        'servers': collector.get_server_info()
                    }
                elif name == 'telegram' and hasattr(collector, 'get_channel_info'):
                    info['collectors'][name] = {
                        'type': 'Telegram',
                        'status': 'active',
                        'channels': collector.get_channel_info()
                    }
                else:
                    info['collectors'][name] = {
                        'type': name.title(),
                        'status': 'active'
                    }
            except Exception as e:
                info['collectors'][name] = {
                    'type': name.title(),
                    'status': f'error: {str(e)}'
                }
        
        return info