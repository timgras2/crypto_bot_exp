#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import threading

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class SentimentCache:
    """
    File-based caching system for sentiment analysis results.
    
    Provides persistent storage with automatic cleanup, deduplication,
    and efficient retrieval of sentiment data for cryptocurrency symbols.
    """
    
    def __init__(self, cache_dir: str = None, max_age_hours: int = 24):
        """
        Initialize sentiment cache.
        
        Args:
            cache_dir: Directory to store cache files (default: data/sentiment_cache)
            max_age_hours: Maximum age for cached data in hours (default: 24)
        """
        self.max_age_hours = max_age_hours
        
        # Set cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Default to data/sentiment_cache in project root
            project_root = Path(__file__).parent.parent.parent
            self.cache_dir = project_root / "data" / "sentiment_cache"
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(f"SentimentCache initialized at: {self.cache_dir}")
    
    def _get_cache_file(self, symbol: str) -> Path:
        """
        Get cache file path for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Path to cache file
        """
        # Sanitize symbol for filename
        safe_symbol = "".join(c for c in symbol if c.isalnum() or c in ('-', '_')).lower()
        return self.cache_dir / f"{safe_symbol}_sentiment.json"
    
    def _get_data_hash(self, data: Dict) -> str:
        """
        Generate hash for data deduplication.
        
        Args:
            data: Data dictionary
            
        Returns:
            MD5 hash string
        """
        # Create hash from key fields
        hash_string = f"{data.get('text', '')}{data.get('timestamp', '')}{data.get('source', '')}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def store_sentiment(self, symbol: str, sentiment_data: Dict):
        """
        Store sentiment analysis result for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            sentiment_data: Processed sentiment data
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(symbol)
                
                # Load existing data
                existing_data = self._load_cache_file(cache_file)
                
                # Add timestamp if not present
                if 'timestamp' not in sentiment_data:
                    sentiment_data['timestamp'] = datetime.utcnow().isoformat()
                
                # Add to cache
                if 'sentiment_results' not in existing_data:
                    existing_data['sentiment_results'] = []
                
                existing_data['sentiment_results'].append(sentiment_data)
                existing_data['last_updated'] = datetime.utcnow().isoformat()
                existing_data['symbol'] = symbol.upper()
                
                # Clean old data
                existing_data = self._clean_old_data(existing_data)
                
                # Save back to file
                self._save_cache_file(cache_file, existing_data)
                
                logger.debug(f"Stored sentiment data for {symbol}")
                
            except Exception as e:
                logger.error(f"Error storing sentiment for {symbol}: {e}")
    
    def store_raw_posts(self, symbol: str, posts: List[Dict]):
        """
        Store raw social media posts for a symbol with deduplication.
        
        Args:
            symbol: Cryptocurrency symbol
            posts: List of raw post data
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(symbol)
                existing_data = self._load_cache_file(cache_file)
                
                if 'raw_posts' not in existing_data:
                    existing_data['raw_posts'] = []
                
                # Create set of existing hashes for deduplication
                existing_hashes = set()
                for post in existing_data['raw_posts']:
                    if 'hash' in post:
                        existing_hashes.add(post['hash'])
                
                # Add new posts with deduplication
                new_posts_added = 0
                for post in posts:
                    post_hash = self._get_data_hash(post)
                    
                    if post_hash not in existing_hashes:
                        post['hash'] = post_hash
                        post['cached_at'] = datetime.utcnow().isoformat()
                        existing_data['raw_posts'].append(post)
                        existing_hashes.add(post_hash)
                        new_posts_added += 1
                
                if new_posts_added > 0:
                    existing_data['last_updated'] = datetime.utcnow().isoformat()
                    existing_data['symbol'] = symbol.upper()
                    
                    # Clean old data
                    existing_data = self._clean_old_data(existing_data)
                    
                    # Save back to file
                    self._save_cache_file(cache_file, existing_data)
                    
                    logger.info(f"Stored {new_posts_added} new posts for {symbol} (deduplicated)")
                
            except Exception as e:
                logger.error(f"Error storing raw posts for {symbol}: {e}")
    
    def get_sentiment(self, symbol: str) -> Optional[Dict]:
        """
        Get latest sentiment data for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            
        Returns:
            Latest sentiment data or None if not found/expired
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(symbol)
                
                if not cache_file.exists():
                    return None
                
                data = self._load_cache_file(cache_file)
                
                if 'sentiment_results' not in data or not data['sentiment_results']:
                    return None
                
                # Get most recent sentiment result
                latest_result = data['sentiment_results'][-1]
                
                # Check if data is still fresh
                if self._is_data_fresh(latest_result):
                    return latest_result
                else:
                    logger.debug(f"Sentiment data for {symbol} is stale")
                    return None
                
            except Exception as e:
                logger.error(f"Error getting sentiment for {symbol}: {e}")
                return None
    
    def get_raw_posts(self, symbol: str, max_age_hours: int = None) -> List[Dict]:
        """
        Get cached raw posts for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            max_age_hours: Maximum age in hours (default: use instance setting)
            
        Returns:
            List of raw posts
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(symbol)
                
                if not cache_file.exists():
                    return []
                
                data = self._load_cache_file(cache_file)
                
                if 'raw_posts' not in data:
                    return []
                
                # Filter by age if specified
                if max_age_hours:
                    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
                    fresh_posts = []
                    
                    for post in data['raw_posts']:
                        post_time = datetime.fromisoformat(post.get('timestamp', post.get('cached_at', '')))
                        if post_time >= cutoff_time:
                            fresh_posts.append(post)
                    
                    return fresh_posts
                else:
                    return data['raw_posts']
                
            except Exception as e:
                logger.error(f"Error getting raw posts for {symbol}: {e}")
                return []
    
    def get_cache_stats(self, symbol: str = None) -> Dict:
        """
        Get cache statistics.
        
        Args:
            symbol: Specific symbol to get stats for, or None for all
            
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'total_symbols': 0,
            'total_posts': 0,
            'total_sentiment_results': 0,
            'cache_size_mb': 0,
            'symbols': {}
        }
        
        try:
            if symbol:
                # Stats for specific symbol
                cache_file = self._get_cache_file(symbol)
                if cache_file.exists():
                    data = self._load_cache_file(cache_file)
                    symbol_stats = {
                        'posts': len(data.get('raw_posts', [])),
                        'sentiment_results': len(data.get('sentiment_results', [])),
                        'last_updated': data.get('last_updated'),
                        'file_size_kb': cache_file.stat().st_size / 1024
                    }
                    stats['symbols'][symbol] = symbol_stats
                    stats['total_symbols'] = 1
                    stats['total_posts'] = symbol_stats['posts']
                    stats['total_sentiment_results'] = symbol_stats['sentiment_results']
                    stats['cache_size_mb'] = symbol_stats['file_size_kb'] / 1024
            else:
                # Stats for all symbols
                for cache_file in self.cache_dir.glob("*_sentiment.json"):
                    try:
                        data = self._load_cache_file(cache_file)
                        symbol_name = cache_file.stem.replace('_sentiment', '').upper()
                        
                        symbol_stats = {
                            'posts': len(data.get('raw_posts', [])),
                            'sentiment_results': len(data.get('sentiment_results', [])),
                            'last_updated': data.get('last_updated'),
                            'file_size_kb': cache_file.stat().st_size / 1024
                        }
                        
                        stats['symbols'][symbol_name] = symbol_stats
                        stats['total_posts'] += symbol_stats['posts']
                        stats['total_sentiment_results'] += symbol_stats['sentiment_results']
                        stats['cache_size_mb'] += symbol_stats['file_size_kb'] / 1024
                        
                    except Exception as e:
                        logger.warning(f"Error reading cache file {cache_file}: {e}")
                
                stats['total_symbols'] = len(stats['symbols'])
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
        
        return stats
    
    def cleanup_old_data(self):
        """Remove expired data from all cache files."""
        with self._lock:
            try:
                cleaned_files = 0
                for cache_file in self.cache_dir.glob("*_sentiment.json"):
                    try:
                        data = self._load_cache_file(cache_file)
                        original_size = len(data.get('raw_posts', [])) + len(data.get('sentiment_results', []))
                        
                        cleaned_data = self._clean_old_data(data)
                        new_size = len(cleaned_data.get('raw_posts', [])) + len(cleaned_data.get('sentiment_results', []))
                        
                        if new_size < original_size:
                            self._save_cache_file(cache_file, cleaned_data)
                            cleaned_files += 1
                            logger.debug(f"Cleaned {cache_file}: {original_size} -> {new_size} items")
                    
                    except Exception as e:
                        logger.warning(f"Error cleaning {cache_file}: {e}")
                
                logger.info(f"Cleaned {cleaned_files} cache files")
                
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")
    
    def clear_symbol_cache(self, symbol: str):
        """
        Clear all cached data for a specific symbol.
        
        Args:
            symbol: Symbol to clear
        """
        with self._lock:
            try:
                cache_file = self._get_cache_file(symbol)
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info(f"Cleared cache for {symbol}")
            except Exception as e:
                logger.error(f"Error clearing cache for {symbol}: {e}")
    
    def _load_cache_file(self, cache_file: Path) -> Dict:
        """
        Load data from a cache file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            Loaded data or empty dict
        """
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading cache file {cache_file}: {e}")
        
        return {}
    
    def _save_cache_file(self, cache_file: Path, data: Dict):
        """
        Save data to a cache file.
        
        Args:
            cache_file: Path to cache file
            data: Data to save
        """
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")
    
    def _clean_old_data(self, data: Dict) -> Dict:
        """
        Remove expired data from cache data.
        
        Args:
            data: Cache data dictionary
            
        Returns:
            Cleaned data dictionary
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
        
        # Clean raw posts
        if 'raw_posts' in data:
            fresh_posts = []
            for post in data['raw_posts']:
                try:
                    post_time = datetime.fromisoformat(post.get('timestamp', post.get('cached_at', '')))
                    if post_time >= cutoff_time:
                        fresh_posts.append(post)
                except Exception:
                    # Keep posts with invalid timestamps for now
                    fresh_posts.append(post)
            
            data['raw_posts'] = fresh_posts
        
        # Clean sentiment results
        if 'sentiment_results' in data:
            fresh_results = []
            for result in data['sentiment_results']:
                try:
                    result_time = datetime.fromisoformat(result.get('timestamp', ''))
                    if result_time >= cutoff_time:
                        fresh_results.append(result)
                except Exception:
                    # Keep results with invalid timestamps for now
                    fresh_results.append(result)
            
            data['sentiment_results'] = fresh_results
        
        return data
    
    def _is_data_fresh(self, data: Dict) -> bool:
        """
        Check if data is still fresh (not expired).
        
        Args:
            data: Data with timestamp
            
        Returns:
            True if data is fresh
        """
        try:
            data_time = datetime.fromisoformat(data.get('timestamp', ''))
            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
            return data_time >= cutoff_time
        except Exception:
            return False