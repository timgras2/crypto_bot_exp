"""
Sentiment analysis module for crypto trading bot.

This module provides sentiment analysis capabilities for social media posts
about cryptocurrencies, specifically designed to enhance new listing trading decisions.
"""

from .sentiment_analyzer import VaderSentimentAnalyzer

__all__ = ['VaderSentimentAnalyzer']