#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands
import threading
import time
import json
import os

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class DiscordCollector:
    """
    Collects cryptocurrency-related messages from Discord servers.
    
    This collector operates as a Discord bot that monitors specified channels
    for crypto discussions and mentions of specific tokens.
    """
    
    def __init__(self, config):
        """
        Initialize Discord collector with configuration.
        
        Args:
            config: Configuration object with Discord bot token and settings
        """
        self.config = config
        self.bot = None
        self.collected_messages = []
        self.monitoring_symbols = set()
        self.is_running = False
        self.collection_lock = threading.Lock()
        
        # Target crypto Discord servers optimized for new token detection
        # IMPORTANT: Bot must be invited to these servers with Message Content Intent enabled
        self.target_servers = {
            # Major Public Crypto Discord Servers (invite bot to these)
            # Format: 'Server Name': {'channels': [...], 'priority': high/medium/low, 'invite_link': '...'}
            
            # Tier 1: High new token activity (invite bot here first)
            'DegenScore': {
                'channels': ['new-listings', 'general', 'alpha-calls', 'degen-chat'],
                'priority': 'high',
                'focus': 'New DeFi tokens, early gems, high-risk plays'
            },
            'Crypto Gem Hunters': {
                'channels': ['gem-calls', 'new-launches', 'presales', 'general'],
                'priority': 'high', 
                'focus': 'Early-stage token discovery'
            },
            
            # Tier 2: Established communities with new token discussion
            'DeFiPulse': {
                'channels': ['general', 'new-projects', 'farming', 'announcements'],
                'priority': 'medium',
                'focus': 'DeFi protocol launches and updates'
            },
            'Crypto Twitter': {
                'channels': ['general', 'alpha', 'calls', 'new-coins'],
                'priority': 'medium',
                'focus': 'Crypto influencer discussions'
            },
            
            # Tier 3: Exchange and ecosystem-specific
            'Uniswap': {
                'channels': ['general', 'new-pairs', 'trading'],
                'priority': 'medium',
                'focus': 'New Uniswap token listings'
            },
            'Solana Trader': {
                'channels': ['general', 'new-tokens', 'degen-plays'],
                'priority': 'medium',
                'focus': 'Solana ecosystem new tokens'
            }
        }
        
        # Fallback: Generic channel names to search in any server the bot joins
        self.generic_target_channels = [
            'general', 'trading', 'new-listings', 'alpha', 'calls', 
            'announcements', 'gem-calls', 'new-tokens', 'presales',
            'degen-chat', 'moonshots', 'altcoins'
        ]
        
        # Initialize bot with intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required to read message content
        
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self._setup_bot_events()
        
    def _setup_bot_events(self):
        """Setup Discord bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            logger.info(f'Discord bot logged in as {self.bot.user}')
            logger.info(f'Bot is in {len(self.bot.guilds)} servers')
            for guild in self.bot.guilds:
                logger.info(f'  - {guild.name} (id: {guild.id})')
        
        @self.bot.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == self.bot.user:
                return
            
            # Only process messages from text channels
            if not isinstance(message.channel, discord.TextChannel):
                return
            
            # Check if this is a channel we want to monitor
            if not self._should_monitor_channel(message.channel):
                return
            
            # Process the message for crypto content
            await self._process_message(message)
            
            # Process commands (if any)
            await self.bot.process_commands(message)
        
        @self.bot.command(name='crypto_status')
        async def crypto_status(ctx):
            """Command to check bot status (for debugging)."""
            if ctx.author.guild_permissions.manage_messages:  # Only for mods
                status = f"Monitoring {len(self.monitoring_symbols)} symbols, collected {len(self.collected_messages)} messages"
                await ctx.send(status)
    
    def _should_monitor_channel(self, channel: discord.TextChannel) -> bool:
        """
        Check if we should monitor messages from this channel.
        
        Args:
            channel: Discord channel object
            
        Returns:
            True if channel should be monitored
        """
        channel_name_lower = channel.name.lower()
        server_name = channel.guild.name
        
        # Priority 1: Check if server is in our target list
        for target_server, config in self.target_servers.items():
            if target_server.lower() in server_name.lower():
                if channel_name_lower in [c.lower() for c in config['channels']]:
                    logger.info(f"Monitoring {server_name}#{channel.name} (target server)")
                    return True
        
        # Priority 2: Check generic channel names in any crypto-related server
        if channel_name_lower in [c.lower() for c in self.generic_target_channels]:
            # Look for crypto-related keywords in server name
            crypto_server_keywords = [
                'crypto', 'bitcoin', 'btc', 'ethereum', 'eth', 'defi',
                'altcoin', 'trading', 'blockchain', 'token', 'coin',
                'dex', 'nft', 'web3', 'solana', 'binance', 'coinbase',
                'moon', 'gem', 'degen', 'yield', 'farm', 'swap'
        ]
        
        # Check channel name
        if any(keyword in channel_name_lower for keyword in crypto_keywords):
            return True
        
        # Check server name
        if any(keyword in server_name_lower for keyword in crypto_keywords):
            # But only from general discussion channels
            general_channels = ['general', 'chat', 'discussion', 'trading', 'announcements']
            if any(gen_chan in channel_name_lower for gen_chan in general_channels):
                return True
        
        return False
    
    async def _process_message(self, message: discord.Message):
        """
        Process a Discord message for crypto content.
        
        Args:
            message: Discord message object
        """
        try:
            # Skip very short messages
            if len(message.content) < 10:
                return
            
            # Skip messages that are just links
            if message.content.startswith('http') and len(message.content.split()) == 1:
                return
            
            # Check if message contains any monitored symbols
            contains_monitored = False
            mentioned_symbols = []
            
            for symbol in self.monitoring_symbols:
                if self._contains_symbol(message.content, symbol):
                    contains_monitored = True
                    mentioned_symbols.append(symbol)
            
            # Also collect general crypto discussions
            is_crypto_relevant = contains_monitored or self._is_crypto_relevant(message.content)
            
            if is_crypto_relevant:
                message_data = {
                    'text': message.content,
                    'author': str(message.author),
                    'timestamp': message.created_at.isoformat(),
                    'source': f'discord_{message.guild.name}_{message.channel.name}',
                    'channel': message.channel.name,
                    'server': message.guild.name,
                    'id': str(message.id),
                    'mentioned_symbols': mentioned_symbols,
                    'author_id': str(message.author.id)
                }
                
                with self.collection_lock:
                    self.collected_messages.append(message_data)
                    
                    # Keep only recent messages (last 24 hours)
                    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                    self.collected_messages = [
                        msg for msg in self.collected_messages
                        if datetime.fromisoformat(msg['timestamp']) > cutoff_time
                    ]
                
                logger.debug(f"Collected Discord message from {message.guild.name}#{message.channel.name}")
                
        except Exception as e:
            logger.error(f"Error processing Discord message: {e}")
    
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
    
    def _is_crypto_relevant(self, text: str) -> bool:
        """
        Check if message is relevant to cryptocurrency discussions.
        
        Args:
            text: Message text to check
            
        Returns:
            True if message appears crypto-relevant
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Crypto keywords that indicate relevance
        crypto_indicators = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain',
            'defi', 'dex', 'trading', 'hodl', 'moon', 'pump', 'dump',
            'altcoin', 'shitcoin', 'rugpull', 'diamond hands', 'paper hands',
            'whale', 'dip', 'ath', 'market cap', 'bull run', 'bear market',
            'staking', 'yield', 'liquidity', 'token', 'coin', 'wallet',
            'exchange', 'binance', 'coinbase', 'uniswap', 'pancakeswap'
        ]
        
        # Check if message contains crypto indicators
        word_count = 0
        for indicator in crypto_indicators:
            if indicator in text_lower:
                word_count += 1
        
        # Consider relevant if multiple crypto terms or one strong indicator
        strong_indicators = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi']
        has_strong = any(indicator in text_lower for indicator in strong_indicators)
        
        return word_count >= 2 or has_strong
    
    def start_monitoring(self, symbol: str = None):
        """
        Start monitoring Discord for crypto discussions.
        
        Args:
            symbol: Optional specific symbol to monitor
        """
        if symbol:
            self.monitoring_symbols.add(symbol.upper())
            logger.info(f"Added {symbol} to Discord monitoring")
        
        if not self.is_running and hasattr(self.config, 'DISCORD_BOT_TOKEN'):
            self.is_running = True
            
            # Run bot in separate thread to avoid blocking
            def run_bot():
                try:
                    asyncio.run(self.bot.start(self.config.DISCORD_BOT_TOKEN))
                except Exception as e:
                    logger.error(f"Discord bot error: {e}")
                    self.is_running = False
            
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            logger.info("Discord collector started")
        else:
            logger.warning("Discord bot token not configured or already running")
    
    def stop_monitoring(self):
        """Stop Discord monitoring."""
        if self.is_running:
            asyncio.create_task(self.bot.close())
            self.is_running = False
            logger.info("Discord collector stopped")
    
    def collect_for_symbol(self, symbol: str, hours_back: int = 6) -> List[Dict]:
        """
        Get collected messages for a specific symbol.
        
        Args:
            symbol: Cryptocurrency symbol
            hours_back: Hours back to search (filters existing collected messages)
            
        Returns:
            List of relevant Discord messages
        """
        self.start_monitoring(symbol)
        
        with self.collection_lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            relevant_messages = []
            for message in self.collected_messages:
                message_time = datetime.fromisoformat(message['timestamp'])
                
                if message_time < cutoff_time:
                    continue
                
                # Check if message mentions the symbol or is generally relevant
                if (symbol.upper() in message.get('mentioned_symbols', []) or 
                    self._contains_symbol(message['text'], symbol)):
                    relevant_messages.append(message)
            
            logger.info(f"Found {len(relevant_messages)} Discord messages for {symbol}")
            return relevant_messages
    
    def get_recent_messages(self, hours_back: int = 2) -> List[Dict]:
        """
        Get recent crypto-relevant messages.
        
        Args:
            hours_back: Hours back to retrieve
            
        Returns:
            List of recent messages
        """
        with self.collection_lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            recent_messages = []
            for message in self.collected_messages:
                message_time = datetime.fromisoformat(message['timestamp'])
                
                if message_time >= cutoff_time:
                    recent_messages.append(message)
            
            return recent_messages
    
    def get_server_info(self) -> Dict:
        """
        Get information about Discord servers the bot is in.
        
        Returns:
            Dictionary with server information
        """
        if not self.bot or not self.bot.is_ready():
            return {'error': 'Bot not ready'}
        
        server_info = {}
        for guild in self.bot.guilds:
            crypto_channels = []
            for channel in guild.text_channels:
                if self._should_monitor_channel(channel):
                    crypto_channels.append(channel.name)
            
            server_info[guild.name] = {
                'id': guild.id,
                'member_count': guild.member_count,
                'crypto_channels': crypto_channels,
                'total_channels': len(guild.text_channels)
            }
        
        return server_info
    
    def save_messages_to_file(self, filepath: str):
        """
        Save collected messages to a file.
        
        Args:
            filepath: Path to save messages
        """
        try:
            with self.collection_lock:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.collected_messages, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.collected_messages)} Discord messages to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving Discord messages: {e}")
    
    def load_messages_from_file(self, filepath: str):
        """
        Load messages from a file.
        
        Args:
            filepath: Path to load messages from
        """
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    loaded_messages = json.load(f)
                
                with self.collection_lock:
                    # Merge with existing messages, avoiding duplicates
                    existing_ids = {msg['id'] for msg in self.collected_messages}
                    new_messages = [msg for msg in loaded_messages if msg['id'] not in existing_ids]
                    self.collected_messages.extend(new_messages)
                
                logger.info(f"Loaded {len(new_messages)} new Discord messages from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading Discord messages: {e}")