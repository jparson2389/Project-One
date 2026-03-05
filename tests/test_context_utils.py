"""Test cases for context_utils.py"""

import sys
from pathlib import Path
from unittest.mock import patch

try:
    from tools.context_utils import ContextMonitor, count_tokens
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tools.context_utils import ContextMonitor, count_tokens


def test_count_tokens():
    """Test the token counting function with various inputs"""
    # Simple text
    assert count_tokens("Hello world") == 2

    # Empty string
    assert count_tokens("") == 0

    # Multiple spaces and newlines
    assert count_tokens("This   \n\n is  a test") == 4

    # Special characters
    assert count_tokens("!@#$%^&*()") == 1


def test_context_monitor_initialization():
    """Test that ContextMonitor initializes with correct default values"""
    monitor = ContextMonitor()
    assert monitor.context_stats["total_attempts"] == 0
    assert monitor.context_stats["successful_attempts"] == 0
    assert monitor.context_stats["context_overflows"] == 0


def test_context_monitor_tracking():
    """Test the track_usage method with different scenarios"""
    monitor = ContextMonitor()

    # Test successful usage (below threshold)
    success = monitor.track_usage("architect", 1000, 16384)
    assert success
    stats = monitor.get_model_stats("architect")
    assert stats["attempts"] == 1
    assert stats["overflow_rate"] == 0

    # Test overflow (above threshold)
    success = monitor.track_usage("architect", 15000, 16384)  # 92% usage
    assert not success
    stats = monitor.get_model_stats("architect")
    assert stats["attempts"] == 2
    assert stats["overflow_rate"] > 0


def test_context_monitor_statistics():
    """Test that statistics are calculated correctly"""
    monitor = ContextMonitor()

    # Add some usage data
    for i in range(1, 6):
        if i < 4:  # First 3 succeed
            monitor.track_usage("architect", 500 * i, 16384)
        else:  # Last 2 fail (overflow)
            monitor.track_usage("architect", 15000, 16384)

    stats = monitor.get_model_stats("architect")
    assert stats["attempts"] == 5
    assert stats["overflow_rate"] > 0.5  # More than half failed


def test_context_monitor_persistence():
    """Test that statistics persist between runs"""
    stats_file = Path("tests/test_monitor_stats.json")

    # First run - create stats
    monitor1 = ContextMonitor()
    monitor1.track_usage("architect", 1000, 16384)
    monitor1.save_stats(str(stats_file))

    # Second run - load and verify
    monitor2 = ContextMonitor()
    monitor2.load_stats(str(stats_file))
    stats = monitor2.get_model_stats("architect")

    assert stats["attempts"] == 1

    # Clean up
    stats_file.unlink()


def test_context_monitor_warning_messages():
    """Test that warning messages are logged when thresholds are exceeded."""
    monitor = ContextMonitor()
    monitor.config["warning_threshold"] = 50  # Lower threshold for testing

    with patch("tools.context_utils.logger") as mock_logger:
        success = monitor.track_usage("architect", 9000, 16384)  # 55% usage
        assert success  # Still succeeds (above warning but below fallback)

        # Verify warning was logged (54.9% = 9000/16384)
        mock_logger.warning.assert_called_with(
            "[context] high context usage: 54.9% for architect"
        )

    # Test fallback threshold
    with patch("tools.context_utils.logger") as mock_logger:
        success = monitor.track_usage("architect", 13500, 16384)  # 82% usage
        assert not success  # Fails at fallback threshold

        # Verify warning was logged before failing
        mock_logger.warning.assert_called()
        last_msg = mock_logger.warning.call_args[0][0]
        assert "[context] high context usage" in last_msg
