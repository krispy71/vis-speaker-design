import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from claude_runner import run_claude, ClaudeError

def test_run_claude_returns_stdout():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Hello from Claude\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_claude("say hello")
    assert result == "Hello from Claude"
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args[0][0][0] == "claude"
    assert call_args[0][0][1] == "-p"

def test_run_claude_raises_on_nonzero_exit():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "authentication error"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeError, match="authentication error"):
            run_claude("say hello")

def test_run_claude_raises_on_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 120)):
        with pytest.raises(ClaudeError, match="timed out"):
            run_claude("say hello")
