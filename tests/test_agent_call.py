"""Test cases for agent_call functionality"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from unittest.mock import MagicMock, patch

import pytest

# Use relative import that works with UV's structure
try:
    from tools.agent_call import _make_llm_call_with_context, main
except ImportError as e:
    print(f"Import error: {e}")
    sys.path.append(str(Path(__file__).parent.parent))
    from agent_call import _make_llm_call_with_context, main


@pytest.fixture
def mock_openai_client():
    """Fixture that provides a mocked OpenAI client"""
    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        yield mock_client


def test_main_function_returns_correct_exit_code(mock_openai_client):
    """Test that main() returns the correct exit code for successful execution"""
    # Mock the client response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"writes": []}'))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    with patch("agent_call._read", return_value="Test prompt"):
        exit_code = main()

    assert exit_code == 0
    mock_openai_client.chat.completions.create.assert_called_once()


def test_main_with_json_writes_flag(mock_openai_client):
    """Test that main() uses the correct system message when --json-writes is passed"""
    # Mock the client response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"writes": []}'))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    with patch("agent_call._read", return_value="Test prompt"):
        # Mock sys.argv to simulate --json-writes flag
        with patch.dict("sys.argv", ["agent_call.py", "--json-writes"]):
            exit_code = main()

    assert exit_code == 0
    mock_openai_client.chat.completions.create.assert_called_once()
    call_args = mock_openai_client.chat.completions.create.call_args[1]
    # Verify the system message contains JSON rules
    assert "Return ONLY valid JSON" in call_args["messages"][0]["content"]


def test_llm_call_with_context_parameters(mock_openai_client):
    """Test that _make_llm_call_with_context uses correct parameters"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"writes": []}'))]
    mock_openai_client.chat.completions.create.return_value = mock_response

    # Mock context monitoring to avoid file operations
    with patch("tools.context_utils.ContextMonitor.track_usage", return_value=True):
        response = _make_llm_call_with_context(
            client=mock_openai_client,
            model_name="architect",
            system="Test system message",
            user_prompt="Test user prompt",
        )

    assert response is not None
    mock_openai_client.chat.completions.create.assert_called_once()

    # Verify the call was made with correct parameters
    call_args = mock_openai_client.chat.completions.create.call_args[1]
    assert call_args["model"] == "architect"
    assert "temperature" in call_args
    assert "max_tokens" in call_args
    assert "top_p" in call_args
    assert "presence_penalty" in call_args
