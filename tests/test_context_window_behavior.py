# tests/test_context_window_behavior.py
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    from tools.context_utils import ContextMonitor, count_tokens, get_model_settings
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent / "tools"))
    from context_utils import ContextMonitor, count_tokens, get_model_settings


# Defer agent_call import to avoid pulling in openai/anyio at collection time
def _get_make_llm_call():
    try:
        from tools.agent_call import _make_llm_call_with_context

        return _make_llm_call_with_context
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.agent_call import _make_llm_call_with_context

        return _make_llm_call_with_context


def _require_agent_call():
    """Skip if agent_call cannot be imported (e.g. openai/anyio env issues)."""
    try:
        _get_make_llm_call()
    except ImportError as e:
        pytest.skip(f"agent_call not importable: {e}")


def test_model_settings_loading(sample_router_yaml):
    """Test that model settings are loaded correctly from router.yaml"""
    router_path = Path(sample_router_yaml)
    architect_settings = get_model_settings("architect", router_path=router_path)
    assert "temperature" in architect_settings
    assert architect_settings["temperature"] == 0.15
    assert architect_settings["max_tokens"] == 4096
    assert architect_settings["context_window"] == 16384

    # Test non-existent model raises error
    with pytest.raises(ValueError, match="Model nonexistent not found"):
        get_model_settings("nonexistent", router_path=router_path)


def test_token_counting():
    """Test the token counting function"""
    short_text = "Hello world"
    long_text = (
        "This is a longer text that should have more tokens than the previous one"
    )

    assert count_tokens(short_text) < count_tokens(long_text)
    # Verify it counts words (simple whitespace-based approach)
    assert count_tokens("one two three") == 3


def test_context_monitoring():
    """Test the context monitoring functionality"""
    monitor = ContextMonitor()

    # Test with different prompt lengths (80% of 16384 = 13107)
    for length in [1000, 8000, 13100]:  # Just below threshold
        success = monitor.track_usage("architect", length, 16384)
        assert success, f"Should succeed at {length} tokens"

    # Test at and above threshold (80% of 16384 = 13107)
    for length in [13200, 15000]:
        success = monitor.track_usage("architect", length, 16384)
        assert not success, f"Should fail at {length} tokens"

    # Verify statistics were recorded correctly
    stats = monitor.get_model_stats("architect")
    assert stats["attempts"] == 5  # 3 successful + 2 failed
    assert stats["overflow_rate"] > 0


def test_context_monitoring_persistence():
    """Test that context monitoring statistics persist between runs"""
    monitor1 = ContextMonitor()
    monitor1.track_usage("architect", 1000, 16384)
    monitor1.save_stats("tests/test_stats.json")

    monitor2 = ContextMonitor()
    monitor2.load_stats("tests/test_stats.json")
    stats = monitor2.get_model_stats("architect")

    assert stats["attempts"] == 1
    Path("tests/test_stats.json").unlink()  # Clean up


def test_backward_compatibility():
    """Test that existing agent_call functionality still works"""
    _require_agent_call()
    _make_llm_call_with_context = _get_make_llm_call()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"writes": []}'))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_model_params = {
        "temperature": 0.15,
        "max_tokens": 4096,
        "context_window": 16384,
        "top_p": 0.7,
        "presence_penalty": 0,
    }
    mock_monitor = MagicMock()
    mock_monitor.track_usage.return_value = True

    with (
        patch("tools.context_utils.get_model_settings", return_value=mock_model_params),
        patch("tools.context_utils.ContextMonitor", return_value=mock_monitor),
    ):
        response = _make_llm_call_with_context(
            client=mock_client,
            model_name="architect",
            system="Be concise and correct.",
            user_prompt="Test prompt",
        )

    assert response is not None
    mock_client.chat.completions.create.assert_called_once()


def test_structured_output_parameter():
    """Test that structured output parameter works as expected"""
    _require_agent_call()
    _make_llm_call_with_context = _get_make_llm_call()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"writes": []}'))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_model_params = {
        "temperature": 0.15,
        "max_tokens": 4096,
        "context_window": 16384,
        "top_p": 0.7,
        "presence_penalty": 0,
    }
    mock_monitor = MagicMock()
    mock_monitor.track_usage.return_value = True

    with (
        patch("tools.context_utils.get_model_settings", return_value=mock_model_params),
        patch("tools.context_utils.ContextMonitor", return_value=mock_monitor),
    ):
        # Test with structured output
        _make_llm_call_with_context(
            client=mock_client,
            model_name="architect",
            system="Be concise and correct.",
            user_prompt="Test prompt",
            use_structured_output=True,
        )

        # Verify the call was made with response_format
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert "response_format" in call_args

        # Reset for second call
        mock_client.chat.completions.create.reset_mock()

        # Test without structured output (backward compatibility)
        _make_llm_call_with_context(
            client=mock_client,
            model_name="architect",
            system="Be concise and correct.",
            user_prompt="Test prompt",
            use_structured_output=False,
        )

        # Verify the call was made without response_format
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert "response_format" not in call_args
