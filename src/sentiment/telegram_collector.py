#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import logging
import asyncio
import threading
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat, User

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class TelegramCollector:
    """
    Collects cryptocurrency-related messages from Telegram channels and groups.
    
    Uses Telethon library to connect to Telegram API and monitor crypto channels
    for specific token mentions and general crypto sentiment.
    """
    
    def __init__(self, config):
        """
        Initialize Telegram collector with configuration.
        
        Args:
            config: Configuration object with Telegram API credentials
        """
        self.config = config
        
        # Major crypto Telegram channels (public channels/groups)
        self.crypto_channels = [
            '@CryptoPanic',           # News aggregator
            '@CryptoNewsOfficialTG',  # News channel
            '@CoinMarketCapNews',     # CoinMarketCap official
            '@binance',               # Binance official
            '@coinbase',              # Coinbase official
            '@CryptoSignalsAdvice',   # Trading signals
            '@CryptoCurrencyPinned',  # General crypto chat
            '@BitcoinMagazine',       # Bitcoin Magazine
            '@ethereum',              # Ethereum community
            '@altcoins',              # Altcoin discussion
        ]
        
        # Initialize client
        self.client = None
        self.session_name = 'crypto_sentiment_session'
        self.is_connected = False
        self.rate_limit_delay = 1.0  # Delay between API calls
        self.last_request_time = 0
        
        # Message collection
        self.collected_messages = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.event_loop = None
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Telethon Telegram client."""
        try:
            self.client = TelegramClient(
                self.session_name,
                self.config.TELEGRAM_API_ID,
                self.config.TELEGRAM_API_HASH
            )
            
            logger.info("Telegram client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            self.client = None
    
    async def _connect_client(self):
        """Connect and authenticate Telegram client."""
        if not self.client:
            return False
        
        try:
            await self.client.start(phone=self.config.TELEGRAM_PHONE_NUMBER)
            
            # Check if we need 2FA
            if not await self.client.is_user_authorized():
                logger.error("Telegram client not authorized")
                return False
            
            self.is_connected = True
            me = await self.client.get_me()
            logger.info(f"Connected to Telegram as: {me.first_name}")
            return True
            
        except SessionPasswordNeededError:
            logger.error("Two-factor authentication required for Telegram")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
    
    def _rate_limit_check(self):
        """Enforce rate limiting to avoid Telegram flood limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _get_entity_safe(self, channel_name: str):
        """
        Safely get Telegram entity (channel/group) with error handling.
        
        Args:
            channel_name: Channel username or ID
            
        Returns:
            Entity object or None if failed
        """
        try:
            self._rate_limit_check()
            entity = await self.client.get_entity(channel_name)
            return entity
        except FloodWaitError as e:
            logger.warning(f"Flood wait for {e.seconds} seconds when accessing {channel_name}")
            await asyncio.sleep(e.seconds)
            return None
        except Exception as e:
            logger.warning(f"Could not access channel {channel_name}: {e}")
            return None
    
    async def _collect_messages_from_channel(self, channel_name: str, symbol: str, hours_back: int) -> List[Dict]:
        """
        Collect messages from a specific Telegram channel.
        
        Args:
            channel_name: Telegram channel name
            symbol: Cryptocurrency symbol to search for
            hours_back: Hours back to search
            
        Returns:
            List of message data
        """
        messages = []
        
        entity = await self._get_entity_safe(channel_name)
        if not entity:
            return messages
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            self._rate_limit_check()
            
            # Get recent messages from the channel
            async for message in self.client.iter_messages(
                entity, 
                limit=100,  # Limit messages per channel
                offset_date=cutoff_time
            ):
                # Skip messages without text
                if not message.text:
                    continue
                
                # Check if message contains the symbol
                if not self._contains_symbol(message.text, symbol):
                    continue
                
                # Extract message data
                message_data = {
                    'text': message.text,
                    'author': self._get_sender_name(message),
                    'timestamp': message.date.isoformat(),
                    'source': f'telegram_{channel_name.replace("@", "")}',
                    'url': f'https://t.me/{channel_name.replace("@", "")}/{message.id}',
                    'message_id': message.id,
                    'channel': channel_name,
                    'views': getattr(message, 'views', 0) or 0,
                    'forwards': getattr(message, 'forwards', 0) or 0
                }
                
                messages.append(message_data)
                
        except FloodWaitError as e:
            logger.warning(f"Hit flood limit on {channel_name}, waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.warning(f"Error collecting from {channel_name}: {e}")
        
        return messages
    
    def _get_sender_name(self, message) -> str:
        """
        Extract sender name from message.
        
        Args:
            message: Telegram message object
            
        Returns:
            Sender name or 'unknown'
        """
        try:
            if message.sender:
                if hasattr(message.sender, 'first_name'):
                    name = message.sender.first_name
                    if hasattr(message.sender, 'last_name') and message.sender.last_name:
                        name += f" {message.sender.last_name}"
                    return name
                elif hasattr(message.sender, 'title'):
                    return message.sender.title
                elif hasattr(message.sender, 'username'):
                    return f"@{message.sender.username}"
            return 'unknown'
        except:
            return 'unknown'
    
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
            f"#{symbol_lower}",
            f"{symbol_lower}/usdt",
            f"{symbol_lower}/btc",
            f"{symbol_lower}usdt",
        ]
        
        return any(pattern in text_lower for pattern in symbol_patterns)
    
    async def _async_collect_for_symbol(self, symbol: str, hours_back: int = 6) -> List[Dict]:
        """
        Async method to collect Telegram messages for a symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            hours_back: Hours back to search
            
        Returns:
            List of collected messages
        """
        if not await self._connect_client():
            return []
        
        all_messages = []
        
        logger.info(f"Collecting Telegram messages for {symbol} from last {hours_back} hours")
        
        # Collect from each channel
        for channel_name in self.crypto_channels[:5]:  # Limit to first 5 channels to avoid rate limits
            try:
                messages = await self._collect_messages_from_channel(channel_name, symbol, hours_back)
                all_messages.extend(messages)
                logger.info(f"Collected {len(messages)} messages from {channel_name}")
                
                # Rate limiting between channels
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error collecting from {channel_name}: {e}")
                continue
        
        # Remove duplicates by message content hash
        seen_texts = set()
        unique_messages = []
        for msg in all_messages:
            text_hash = hash(msg['text'])
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_messages.append(msg)
        
        await self.client.disconnect()
        logger.info(f"Collected {len(unique_messages)} unique Telegram messages for {symbol}")
        
        return unique_messages
    
    def collect_for_symbol(self, symbol: str, hours_back: int = 6) -> List[Dict]:
        """
        Collect Telegram messages mentioning a specific cryptocurrency symbol.
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH', 'NEWCOIN')
            hours_back: How many hours back to search (default 6)
            
        Returns:
            List of structured message data dictionaries
        """
        if not self.client:
            logger.error("Telegram client not initialized")
            return []
        
        try:
            # Run async collection in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                messages = loop.run_until_complete(
                    self._async_collect_for_symbol(symbol, hours_back)
                )
                return messages
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in Telegram collection: {e}")
            return []
    
    async def _async_collect_general_sentiment(self, hours_back: int = 2) -> List[Dict]:
        """
        Async method to collect general crypto sentiment from Telegram.
        
        Args:
            hours_back: Hours back to search
            
        Returns:
            List of general crypto messages
        """
        if not await self._connect_client():
            return []
        
        all_messages = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Focus on news and general channels for sentiment
        priority_channels = [
            '@CryptoPanic',
            '@CryptoNewsOfficialTG',
            '@BitcoinMagazine',
            '@binance'
        ]
        
        for channel_name in priority_channels:
            try:
                entity = await self._get_entity_safe(channel_name)
                if not entity:
                    continue
                
                self._rate_limit_check()
                
                async for message in self.client.iter_messages(
                    entity,
                    limit=50,
                    offset_date=cutoff_time
                ):
                    if not message.text or len(message.text) < 50:
                        continue
                    
                    message_data = {
                        'text': message.text,
                        'author': self._get_sender_name(message),
                        'timestamp': message.date.isoformat(),
                        'source': f'telegram_{channel_name.replace("@", "")}_general',
                        'url': f'https://t.me/{channel_name.replace("@", "")}/{message.id}',
                        'message_id': message.id,
                        'channel': channel_name,
                        'views': getattr(message, 'views', 0) or 0,
                        'forwards': getattr(message, 'forwards', 0) or 0
                    }
                    
                    all_messages.append(message_data)
                
                await asyncio.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error collecting general sentiment from {channel_name}: {e}")
                continue
        
        await self.client.disconnect()
        return all_messages
    
    def collect_general_crypto_sentiment(self, hours_back: int = 2) -> List[Dict]:
        """
        Collect general cryptocurrency sentiment from major Telegram channels.
        
        Args:
            hours_back: How many hours back to search
            
        Returns:
            List of recent crypto-related messages
        """
        if not self.client:
            logger.error("Telegram client not initialized")
            return []
        
        try:
            # Run async collection in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                messages = loop.run_until_complete(
                    self._async_collect_general_sentiment(hours_back)
                )
                return messages
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error in general Telegram collection: {e}")
            return []
    
    def start_monitoring(self, symbol: str):
        """
        Start real-time monitoring for a symbol.
        
        Args:
            symbol: Symbol to monitor
        """
        # Real-time monitoring would require keeping connection open
        # For now, just log that monitoring was requested
        logger.info(f"Telegram monitoring requested for {symbol} (not implemented in current version)")
    
    def stop_monitoring(self, symbol: str):
        """
        Stop monitoring a symbol.
        
        Args:
            symbol: Symbol to stop monitoring
        """
        logger.info(f"Stopped Telegram monitoring for {symbol}")
    
    def get_channel_info(self) -> Dict[str, Dict]:
        """
        Get information about monitored Telegram channels.
        
        Returns:
            Dictionary with channel statistics
        """
        # This would require connecting and querying each channel
        # Return basic info for now
        channel_info = {}
        
        for channel in self.crypto_channels[:3]:  # Limit to avoid rate limits
            channel_info[channel] = {
                'type': 'Telegram Channel',
                'status': 'configured',
                'url': f'https://t.me/{channel.replace("@", "")}'
            }
        
        return channel_info
    
    def __del__(self):
        """Cleanup when collector is destroyed."""
        if self.client and self.is_connected:
            try:
                # Disconnect if still connected
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.client.disconnect())
                loop.close()
            except:
                pass