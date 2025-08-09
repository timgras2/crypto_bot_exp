#!/usr/bin/env python3
"""
Circuit Breaker - System stability protection for asset protection operations
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit breaker triggered, all requests fail
    HALF_OPEN = "half_open" # Testing if system has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5        # Number of consecutive failures to trigger
    recovery_timeout: int = 300       # Seconds to wait before trying recovery
    success_threshold: int = 3        # Consecutive successes needed to close circuit
    monitoring_window: int = 60       # Window in seconds to count failures


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascade failures in asset protection.
    
    Protects against:
    - Repeated API failures
    - Exchange connectivity issues
    - Invalid market conditions
    - Budget or configuration errors
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.state_change_time = datetime.now()
        
        # Failure tracking within monitoring window
        self.recent_failures: list[datetime] = []
        
        logger.info(f"Circuit breaker '{self.name}' initialized: "
                   f"failure_threshold={self.config.failure_threshold}, "
                   f"recovery_timeout={self.config.recovery_timeout}s")
    
    def call(self, operation_name: str, func, *args, **kwargs):
        """
        Execute a function through the circuit breaker.
        
        Args:
            operation_name: Name of the operation for logging
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Function result if successful
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails and circuit allows it
        """
        if not self._can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is OPEN for operation '{operation_name}'. "
                f"Last failure: {self.last_failure_time}, "
                f"Recovery in: {self._time_until_recovery():.0f}s"
            )
        
        try:
            # Execute the operation
            result = func(*args, **kwargs)
            
            # Record success
            self._on_success()
            logger.debug(f"Circuit breaker '{self.name}' - '{operation_name}' succeeded")
            
            return result
            
        except Exception as e:
            # Record failure
            self._on_failure(operation_name, str(e))
            logger.warning(f"Circuit breaker '{self.name}' - '{operation_name}' failed: {e}")
            
            # Re-raise the original exception
            raise
    
    def _can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_reset():
                self._attempt_reset()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _attempt_reset(self) -> None:
        """Attempt to reset the circuit breaker to half-open state."""
        logger.info(f"Circuit breaker '{self.name}' attempting reset to HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_change_time = datetime.now()
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        self.success_count += 1
        self.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in normal operation
            self.failure_count = 0
            self._cleanup_old_failures()
    
    def _on_failure(self, operation_name: str, error_msg: str) -> None:
        """Handle failed operation."""
        current_time = datetime.now()
        self.failure_count += 1
        self.last_failure_time = current_time
        self.recent_failures.append(current_time)
        
        # Clean up old failures outside monitoring window
        self._cleanup_old_failures()
        
        # Check if we should open the circuit
        if self.state == CircuitState.CLOSED:
            # Count recent failures within monitoring window
            recent_failure_count = len(self.recent_failures)
            
            if recent_failure_count >= self.config.failure_threshold:
                self._open_circuit(operation_name, error_msg)
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state opens the circuit
            self._open_circuit(operation_name, error_msg)
    
    def _cleanup_old_failures(self) -> None:
        """Remove failures older than the monitoring window."""
        cutoff_time = datetime.now() - timedelta(seconds=self.config.monitoring_window)
        self.recent_failures = [
            failure_time for failure_time in self.recent_failures
            if failure_time > cutoff_time
        ]
    
    def _open_circuit(self, operation_name: str, error_msg: str) -> None:
        """Open the circuit breaker."""
        logger.error(f"Circuit breaker '{self.name}' OPENING due to repeated failures. "
                    f"Last failure in '{operation_name}': {error_msg}")
        
        self.state = CircuitState.OPEN
        self.state_change_time = datetime.now()
        self.success_count = 0
        
        print(f"🚨 CIRCUIT BREAKER: {self.name} protection activated - blocking operations for {self.config.recovery_timeout}s")
    
    def _close_circuit(self) -> None:
        """Close the circuit breaker (return to normal operation)."""
        logger.info(f"Circuit breaker '{self.name}' CLOSING - returning to normal operation")
        
        self.state = CircuitState.CLOSED
        self.state_change_time = datetime.now()
        self.failure_count = 0
        self.success_count = 0
        self.recent_failures.clear()
        
        print(f"✅ CIRCUIT BREAKER: {self.name} restored - normal operations resumed")
    
    def _time_until_recovery(self) -> float:
        """Calculate seconds until recovery attempt."""
        if not self.last_failure_time:
            return 0.0
        
        time_since_failure = datetime.now() - self.last_failure_time
        return max(0.0, self.config.recovery_timeout - time_since_failure.total_seconds())
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the circuit breaker."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'recent_failures': len(self.recent_failures),
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'time_until_recovery': self._time_until_recovery() if self.state == CircuitState.OPEN else 0.0,
            'state_duration': (datetime.now() - self.state_change_time).total_seconds()
        }
    
    def force_open(self, reason: str) -> None:
        """Manually open the circuit breaker."""
        logger.warning(f"Circuit breaker '{self.name}' manually opened: {reason}")
        self._open_circuit("manual", reason)
    
    def force_close(self, reason: str) -> None:
        """Manually close the circuit breaker."""
        logger.info(f"Circuit breaker '{self.name}' manually closed: {reason}")
        self._close_circuit()
        
        print(f"⚡ MANUAL OVERRIDE: {self.name} circuit breaker reset by operator")


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker prevents operation execution."""
    pass


# Pre-configured circuit breakers for common operations
def create_api_circuit_breaker() -> CircuitBreaker:
    """Create circuit breaker for API operations."""
    config = CircuitBreakerConfig(
        failure_threshold=5,    # 5 consecutive API failures
        recovery_timeout=300,   # 5 minute recovery wait
        success_threshold=3,    # 3 successes to close
        monitoring_window=60    # Count failures in 1-minute window
    )
    return CircuitBreaker("API_Operations", config)


def create_trading_circuit_breaker() -> CircuitBreaker:
    """Create circuit breaker for trading operations."""
    config = CircuitBreakerConfig(
        failure_threshold=3,    # 3 consecutive trading failures
        recovery_timeout=600,   # 10 minute recovery wait (trading is more critical)
        success_threshold=2,    # 2 successes to close
        monitoring_window=120   # Count failures in 2-minute window
    )
    return CircuitBreaker("Trading_Operations", config)


def create_balance_circuit_breaker() -> CircuitBreaker:
    """Create circuit breaker for balance/account operations."""
    config = CircuitBreakerConfig(
        failure_threshold=4,    # 4 consecutive balance failures
        recovery_timeout=180,   # 3 minute recovery wait
        success_threshold=2,    # 2 successes to close
        monitoring_window=90    # Count failures in 90-second window
    )
    return CircuitBreaker("Balance_Operations", config)