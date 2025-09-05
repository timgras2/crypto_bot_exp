#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from typing import Dict, List, Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)


class VaderSentimentAnalyzer:
    """
    VADER-based sentiment analyzer optimized for crypto social media posts.
    
    VADER (Valence Aware Dictionary and sEntiment Reasoner) is specifically
    designed for social media text and handles emojis, slang, and intensity well.
    """
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        
        # Add crypto-specific terms to VADER's lexicon
        self._enhance_crypto_lexicon()
        
        logger.info("VaderSentimentAnalyzer initialized with crypto enhancements")
    
    def _enhance_crypto_lexicon(self):
        """
        Add crypto-specific terms to VADER's sentiment lexicon.
        
        VADER allows us to add custom terms with sentiment scores.
        Scores range from -4 (most negative) to +4 (most positive).
        """
        crypto_lexicon_updates = {
            # Positive crypto terms
            'hodl': 2.0,
            'hodling': 2.0,
            'diamond hands': 3.0,
            'diamondhands': 3.0,
            'bullish': 2.5,
            'moon': 2.0,
            'mooning': 3.0,
            'lambo': 2.0,
            'ath': 1.5,  # All Time High
            'btfd': 2.0,  # Buy The F***ing Dip
            'wagmi': 2.5,  # We're All Gonna Make It
            'lfg': 2.0,  # Let's F***ing Go
            'gm': 1.0,   # Good Morning (crypto greeting)
            'based': 2.0,
            'alpha': 2.0,
            'gem': 2.5,
            'hidden gem': 3.0,
            'undervalued': 1.5,
            'solid project': 2.5,
            'fundamentals': 1.5,
            'utility': 2.0,
            
            # Negative crypto terms
            'rugpull': -4.0,
            'rug pull': -4.0,
            'rugged': -3.5,
            'scam': -3.0,
            'shitcoin': -2.5,
            'paper hands': -2.5,
            'paperhands': -2.5,
            'bearish': -2.0,
            'dump': -2.5,
            'dumping': -2.5,
            'rekt': -3.0,
            'fud': -2.0,
            'ngmi': -2.5,  # Not Gonna Make It
            'ponzi': -3.5,
            'exit scam': -4.0,
            'dead cat bounce': -2.0,
            'capitulation': -2.5,
            'bag holder': -2.0,
            'bagholder': -2.0,
            'down bad': -2.0,
            'cope': -1.5,
            'copium': -1.5,
            
            # Neutral but informative
            'dyor': 0.0,  # Do Your Own Research
            'nfa': 0.0,   # Not Financial Advice
            'imo': 0.0,   # In My Opinion
            'imho': 0.0,  # In My Humble Opinion
        }
        
        # Update VADER's lexicon
        self.analyzer.lexicon.update(crypto_lexicon_updates)
        logger.info(f"Added {len(crypto_lexicon_updates)} crypto-specific terms to VADER lexicon")
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dict with sentiment scores:
            - compound: Overall sentiment (-1 to +1)
            - positive: Positive intensity (0 to 1)
            - negative: Negative intensity (0 to 1)
            - neutral: Neutral intensity (0 to 1)
        """
        if not text or not text.strip():
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0
            }
        
        try:
            scores = self.analyzer.polarity_scores(text)
            return {
                'compound': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment for text: {e}")
            return {
                'compound': 0.0,
                'positive': 0.0,
                'negative': 0.0,
                'neutral': 1.0
            }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, float]]:
        """
        Analyze sentiment for multiple texts efficiently.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment score dictionaries
        """
        results = []
        for text in texts:
            result = self.analyze_text(text)
            results.append(result)
        
        return results
    
    def get_sentiment_label(self, compound_score: float) -> str:
        """
        Convert compound score to human-readable label.
        
        Args:
            compound_score: VADER compound score (-1 to +1)
            
        Returns:
            Sentiment label: 'positive', 'negative', 'neutral'
        """
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'
    
    def get_sentiment_strength(self, compound_score: float) -> str:
        """
        Get sentiment strength description.
        
        Args:
            compound_score: VADER compound score (-1 to +1)
            
        Returns:
            Strength label: 'very_strong', 'strong', 'moderate', 'weak'
        """
        abs_score = abs(compound_score)
        
        if abs_score >= 0.8:
            return 'very_strong'
        elif abs_score >= 0.6:
            return 'strong'
        elif abs_score >= 0.3:
            return 'moderate'
        else:
            return 'weak'


class CryptoSentimentProcessor:
    """
    High-level processor for crypto sentiment analysis with additional features.
    """
    
    def __init__(self):
        self.analyzer = VaderSentimentAnalyzer()
        logger.info("CryptoSentimentProcessor initialized")
    
    def process_social_post(self, post_data: Dict) -> Optional[Dict]:
        """
        Process a single social media post with comprehensive analysis.
        
        Args:
            post_data: Dict containing 'text', 'author', 'timestamp', etc.
            
        Returns:
            Dict with processed sentiment data or None if post should be filtered
        """
        text = post_data.get('text', '')
        if not text:
            return None
        
        # Basic spam/bot filtering
        if self._is_likely_spam(text):
            logger.debug(f"Filtered spam post: {text[:50]}...")
            return None
        
        # Analyze sentiment
        sentiment = self.analyzer.analyze_text(text)
        
        # Calculate confidence (how sure we are about the sentiment)
        confidence = self._calculate_confidence(sentiment, text)
        
        return {
            'text': text,
            'sentiment_compound': sentiment['compound'],
            'sentiment_positive': sentiment['positive'],
            'sentiment_negative': sentiment['negative'],
            'sentiment_neutral': sentiment['neutral'],
            'sentiment_label': self.analyzer.get_sentiment_label(sentiment['compound']),
            'sentiment_strength': self.analyzer.get_sentiment_strength(sentiment['compound']),
            'confidence': confidence,
            'timestamp': post_data.get('timestamp'),
            'author': post_data.get('author'),
            'source': post_data.get('source', 'unknown')
        }
    
    def _is_likely_spam(self, text: str) -> bool:
        """
        Basic spam detection for obvious pump attempts.
        
        Args:
            text: The text to check
            
        Returns:
            True if text appears to be spam
        """
        text_lower = text.lower()
        
        spam_indicators = {
            'excessive_caps': sum(1 for c in text if c.isupper()) / max(len(text), 1) > 0.6,
            'excessive_emojis': len([c for c in text if ord(c) > 127]) > 15,
            'rocket_spam': text.count('🚀') > 3,
            'moon_spam': text_lower.count('moon') > 2,
            'buy_spam': text_lower.count('buy') > 2,
            'pump_keywords': any(word in text_lower for word in ['pump pump', 'buy buy', 'moon moon', 'now now']),
            'excessive_exclamation': text.count('!') > 8,
            'all_caps_words': len([word for word in text.split() if word.isupper() and len(word) > 3]) > 3,
            'repeated_words': len(text.split()) != len(set(text.lower().split())),
            'guaranteed_keywords': any(word in text_lower for word in ['guaranteed', '100x', 'lambo guaranteed']),
            
            # Enhanced detection for new token pump schemes (added for CryptoMoonShots)
            'new_gem_spam': text_lower.count('gem') > 2,
            'presale_spam': any(word in text_lower for word in ['presale', 'pre-sale', 'ico launching', 'new launch']),
            'urgency_spam': any(word in text_lower for word in ['now or never', 'last chance', 'dont miss', 'hurry up']),
            'price_prediction_spam': any(word in text_lower for word in ['1000x', '10000x', 'next shib', 'next doge']),
            'social_proof_spam': text_lower.count('everyone is buying') > 0 or text_lower.count('everyone buying') > 0,
            'financial_advice_red_flag': any(word in text_lower for word in ['financial advice', 'trust me bro', 'easy money'])
        }
        
        # Consider spam if 3 or more indicators
        spam_score = sum(spam_indicators.values())
        return spam_score >= 3
    
    def _calculate_confidence(self, sentiment: Dict[str, float], text: str) -> float:
        """
        Calculate confidence in the sentiment analysis.
        
        Args:
            sentiment: VADER sentiment scores
            text: Original text
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from VADER's compound score strength
        base_confidence = abs(sentiment['compound'])
        
        # Adjust based on text characteristics
        text_length = len(text.split())
        
        # Longer texts generally give more reliable sentiment
        length_factor = min(text_length / 20, 1.0)  # Cap at 20 words
        
        # Higher confidence if sentiment is not mixed
        mixed_penalty = 0
        if sentiment['positive'] > 0.1 and sentiment['negative'] > 0.1:
            mixed_penalty = 0.2  # Reduce confidence for mixed sentiment
        
        confidence = (base_confidence + length_factor) / 2 - mixed_penalty
        return max(0.0, min(1.0, confidence))  # Clamp between 0 and 1