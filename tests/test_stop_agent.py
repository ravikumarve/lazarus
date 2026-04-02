"""
tests/test_stop_agent.py — Unit tests for agent stop functionality.
"""

from unittest.mock import patch, MagicMock
import pytest

import agent.heartbeat
from agent.heartbeat import stop_agent


class TestStopAgent:
    def test_stop_agent_with_running_scheduler(self):
        """Test that stop_agent waits for scheduler to shut down."""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True

        # Set the global _scheduler
        agent.heartbeat._scheduler = mock_scheduler

        with patch("agent.heartbeat._remove_pid_file") as mock_remove_pid:
            stop_agent()

            # Verify shutdown was called with wait=True
            mock_scheduler.shutdown.assert_called_once_with(wait=True)
            mock_remove_pid.assert_called_once()
            assert agent.heartbeat._scheduler is None  # Global should be set to None

    def test_stop_agent_with_stopped_scheduler(self):
        """Test that stop_agent does nothing if scheduler is not running."""
        mock_scheduler = MagicMock()
        mock_scheduler.running = False

        # Set the global _scheduler
        agent.heartbeat._scheduler = mock_scheduler

        with patch("agent.heartbeat._remove_pid_file") as mock_remove_pid:
            stop_agent()

            # Should not call shutdown if not running
            mock_scheduler.shutdown.assert_not_called()
            mock_remove_pid.assert_called_once()
            assert agent.heartbeat._scheduler is None  # Global should be set to None

    def test_stop_agent_with_no_scheduler(self):
        """Test that stop_agent handles case where _scheduler is None."""
        # Set the global _scheduler to None
        agent.heartbeat._scheduler = None

        with patch("agent.heartbeat._remove_pid_file") as mock_remove_pid:
            stop_agent()

            # Should just remove PID file and return
            mock_remove_pid.assert_called_once()
