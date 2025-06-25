# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from app.server import GeminiSession, app
from fastapi.testclient import TestClient


class TestMultiUserFunctionality:
    """Test cases for multi-user functionality."""

    def test_gemini_session_initialization(self):
        """Test that GeminiSession initializes correctly."""
        session_mock = MagicMock()
        websocket_mock = MagicMock()
        mcp_client_mock = MagicMock()

        gemini_session = GeminiSession(
            session=session_mock,
            websocket=websocket_mock,
            mcp_client=mcp_client_mock,
        )

        assert gemini_session.session == session_mock
        assert gemini_session.websocket == websocket_mock
        assert gemini_session.mcp_client == mcp_client_mock
        assert gemini_session.run_id == "n/a"
        assert gemini_session.user_id == "n/a"
        assert gemini_session._is_running is True
        assert isinstance(gemini_session._tool_call_queue, asyncio.Queue)

    @pytest.mark.asyncio
    async def test_cleanup_cancels_tasks(self):
        """Test that cleanup properly cancels all tasks."""
        session_mock = MagicMock()
        websocket_mock = MagicMock()
        mcp_client_mock = MagicMock()

        gemini_session = GeminiSession(
            session=session_mock,
            websocket=websocket_mock,
            mcp_client=mcp_client_mock,
        )

        # Create real async tasks for testing
        async def dummy_task():
            await asyncio.sleep(10)

        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())

        gemini_session._tool_tasks = [task1, task2]

        # Create mock processor task
        processor_task = asyncio.create_task(dummy_task())
        gemini_session._tool_processor_task = processor_task

        await gemini_session.cleanup()

        # Verify cleanup behavior
        assert gemini_session._is_running is False
        assert task1.cancelled()
        assert task2.cancelled()
        assert processor_task.cancelled()

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolation(self):
        """Test that multiple sessions don't interfere with each other."""
        # Create two separate sessions
        session1_mock = MagicMock()
        websocket1_mock = MagicMock()
        mcp_client1_mock = MagicMock()

        session2_mock = MagicMock()
        websocket2_mock = MagicMock()
        mcp_client2_mock = MagicMock()

        gemini_session1 = GeminiSession(
            session=session1_mock,
            websocket=websocket1_mock,
            mcp_client=mcp_client1_mock,
        )

        gemini_session2 = GeminiSession(
            session=session2_mock,
            websocket=websocket2_mock,
            mcp_client=mcp_client2_mock,
        )

        # Set different user IDs
        gemini_session1.user_id = "user1"
        gemini_session2.user_id = "user2"

        # Verify they are independent
        assert gemini_session1.user_id != gemini_session2.user_id
        assert gemini_session1.mcp_client != gemini_session2.mcp_client
        assert gemini_session1._tool_call_queue != gemini_session2._tool_call_queue

    @pytest.mark.asyncio
    async def test_tool_call_queue_isolation(self):
        """Test that tool call queues are isolated between sessions."""
        session1_mock = MagicMock()
        websocket1_mock = MagicMock()
        mcp_client1_mock = MagicMock()

        session2_mock = MagicMock()
        websocket2_mock = MagicMock()
        mcp_client2_mock = MagicMock()

        gemini_session1 = GeminiSession(
            session=session1_mock,
            websocket=websocket1_mock,
            mcp_client=mcp_client1_mock,
        )

        gemini_session2 = GeminiSession(
            session=session2_mock,
            websocket=websocket2_mock,
            mcp_client=mcp_client2_mock,
        )

        # Add items to queues
        await gemini_session1._tool_call_queue.put("tool_call_1")
        await gemini_session2._tool_call_queue.put("tool_call_2")

        # Verify queue isolation
        assert gemini_session1._tool_call_queue.qsize() == 1
        assert gemini_session2._tool_call_queue.qsize() == 1

        item1 = await gemini_session1._tool_call_queue.get()
        item2 = await gemini_session2._tool_call_queue.get()

        assert item1 == "tool_call_1"
        assert item2 == "tool_call_2"

    def test_app_state_config_isolation(self):
        """Test that app state is properly configured for per-connection MCP clients."""
        with TestClient(app):
            # Verify that app.state.config is set up correctly
            assert hasattr(app.state, "config")
            assert app.state.config is not None

    @pytest.mark.asyncio
    async def test_error_handling_in_tool_calls(self):
        """Test error handling in tool call processing."""
        session_mock = MagicMock()
        session_mock.send = MagicMock(
            return_value=asyncio.create_task(asyncio.sleep(0))
        )

        websocket_mock = MagicMock()
        mcp_client_mock = MagicMock()

        # Mock tool call that raises an exception
        async def mock_call_tool(*args, **kwargs):
            raise Exception("Tool execution failed")

        mcp_client_mock.call_tool = mock_call_tool

        gemini_session = GeminiSession(
            session=session_mock,
            websocket=websocket_mock,
            mcp_client=mcp_client_mock,
        )

        # Mock tool call with proper string values
        function_call_mock = MagicMock()
        function_call_mock.name = "test_tool"
        function_call_mock.args = {}
        function_call_mock.id = "test_id"

        tool_call_mock = MagicMock()
        tool_call_mock.function_calls = [function_call_mock]

        with patch("app.server.types.LiveClientToolResponse") as mock_response:
            await gemini_session._handle_tool_call(session_mock, tool_call_mock)

            # Verify error response was created
            mock_response.assert_called()
