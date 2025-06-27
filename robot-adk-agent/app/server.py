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
import copy
import json
import logging
from asyncio import Queue
from collections.abc import Callable
from typing import Any

import backoff
import fastmcp
from app.agent import MODEL_ID, genai_client, get_live_connect_config
from app.config import config
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import logging as google_cloud_logging
from google.genai import types
from google.genai.types import LiveServerToolCall
from websockets.exceptions import ConnectionClosedError

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
logging.basicConfig(level=logging.INFO)


class GeminiSession:
    """Manages bidirectional communication between a client and the Gemini model."""

    def __init__(
        self,
        session: Any,
        websocket: WebSocket,
        mcp_client: fastmcp.Client,
    ) -> None:
        """Initialize the Gemini session.

        Args:
            session: The Gemini session
            websocket: The client websocket connection
            mcp_client: The MCP client instance for this session
        """
        self.session = session
        self.websocket = websocket
        self.mcp_client = mcp_client
        self.run_id = "n/a"
        self.user_id = "n/a"
        self._tool_tasks: list[asyncio.Task] = []
        self._tool_call_queue: Queue = Queue()
        self._tool_processor_task: asyncio.Task | None = None
        self._is_running = True

    async def cleanup(self) -> None:
        """Clean up resources and tasks."""
        self._is_running = False

        # Cancel the tool processor task
        if self._tool_processor_task and not self._tool_processor_task.done():
            self._tool_processor_task.cancel()
            try:
                await self._tool_processor_task
            except asyncio.CancelledError:
                pass

        # Cancel any remaining tool tasks
        for task in self._tool_tasks:
            if not task.done():
                task.cancel()

        if self._tool_tasks:
            await asyncio.gather(*self._tool_tasks, return_exceptions=True)

        self._tool_tasks.clear()

    async def receive_from_client(self) -> None:
        """Listen for and process messages from the client.

        Continuously receives messages and forwards audio data to Gemini.
        Handles connection errors gracefully.
        """
        try:
            while self._is_running:
                try:
                    data = await self.websocket.receive_json()

                    if isinstance(data, dict) and (
                        "realtimeInput" in data or "clientContent" in data
                    ):
                        await self.session._ws.send(json.dumps(data))
                    elif "setup" in data:
                        self.run_id = data["setup"]["run_id"]
                        self.user_id = data["setup"]["user_id"]
                        logger.log_struct(
                            {**data["setup"], "type": "setup"}, severity="INFO"
                        )
                    else:
                        logging.warning(
                            f"Received unexpected input from client: {data}"
                        )
                except ConnectionClosedError as e:
                    logging.warning(f"Client {self.user_id} closed connection: {e}")
                    break
                except Exception as e:
                    logging.error(f"Error receiving from client {self.user_id}: {e!s}")
                    break
        finally:
            await self.cleanup()

    async def _handle_tool_call(
        self, session: Any, tool_call: LiveServerToolCall
    ) -> None:
        """Process tool calls from Gemini and send back responses."""
        if tool_call.function_calls is None:
            logging.debug("No function calls in tool_call")
            return

        for fc in tool_call.function_calls:
            try:
                logging.debug(
                    f"[{self.user_id}] Calling tool function: {fc.name} with args: {fc.args}"
                )

                response = await self.mcp_client.call_tool(fc.name, fc.args)

                tool_response = types.LiveClientToolResponse(
                    function_responses=[
                        types.FunctionResponse(
                            name=fc.name,
                            id=fc.id,
                            response={"response": response[0].text},
                        )
                    ]
                )
                logging.debug(f"[{self.user_id}] Tool response: {tool_response}")
                await session.send(input=tool_response)
            except Exception as e:
                logging.error(
                    f"[{self.user_id}] Error handling tool call {fc.name}: {e!s}"
                )
                # Send error response back to Gemini
                error_response = types.LiveClientToolResponse(
                    function_responses=[
                        types.FunctionResponse(
                            name=fc.name,
                            id=fc.id,
                            response={"error": f"Tool execution failed: {e!s}"},
                        )
                    ]
                )
                await session.send(input=error_response)

    async def _process_tool_calls(self) -> None:
        """Continuously process tool calls from the queue."""
        try:
            while self._is_running:
                try:
                    # Use timeout to avoid blocking indefinitely
                    tool_call = await asyncio.wait_for(
                        self._tool_call_queue.get(), timeout=1.0
                    )
                    task = asyncio.create_task(
                        self._handle_tool_call(self.session, tool_call)
                    )
                    self._tool_tasks.append(task)
                    self._tool_call_queue.task_done()

                    # Clean up completed tasks
                    self._tool_tasks = [t for t in self._tool_tasks if not t.done()]

                except asyncio.TimeoutError:
                    # Timeout is expected, continue loop
                    continue
                except Exception as e:
                    logging.error(
                        f"[{self.user_id}] Error processing tool calls: {e!s}"
                    )
        except asyncio.CancelledError:
            logging.debug(f"[{self.user_id}] Tool call processor cancelled")
            raise

    async def receive_from_gemini(self) -> None:
        """Listen for and process messages from Gemini without blocking."""
        # Start the tool call processing task
        self._tool_processor_task = asyncio.create_task(self._process_tool_calls())

        try:
            while self._is_running and (
                result := await self.session._ws.recv(decode=False)
            ):
                await self.websocket.send_bytes(result)
                raw_message = json.loads(result)
                if "toolCall" in raw_message:
                    message = types.LiveServerMessage.model_validate(raw_message)
                    tool_call = LiveServerToolCall.model_validate(message.tool_call)
                    # Add the tool call to the queue for processing
                    await self._tool_call_queue.put(tool_call)
        except Exception as e:
            logging.error(f"[{self.user_id}] Error receiving from Gemini: {e!s}")
        finally:
            await self.cleanup()


def get_connect_and_run_callable(
    websocket: WebSocket, initial_user_id: str = "anonymous"
) -> Callable:
    """Create a callable that handles Gemini connection with retry logic.

    Args:
        websocket: The client websocket connection
        initial_user_id: Initial user ID extracted from connection

    Returns:
        Callable: An async function that establishes and manages the Gemini connection
    """

    async def on_backoff(details: backoff._typing.Details) -> None:
        await websocket.send_json(
            {
                "status": f"Model connection error, retrying in {details['wait']} seconds..."
            }
        )

    @backoff.on_exception(
        backoff.expo, ConnectionClosedError, max_tries=10, on_backoff=on_backoff
    )
    async def connect_and_run() -> None:
        # Create a dedicated MCP client for this connection

        # Clone the config to avoid cross-session mutation
        user_config = copy.deepcopy(config)
        user_config["mcpServers"]["robot"]["env"]["SESSION_KEY"] = initial_user_id
        logging.info(f"Creating MCP client for user: {initial_user_id}")
        mcp_client = fastmcp.Client(user_config)
        gemini_session = None

        try:
            async with mcp_client:
                tools = await mcp_client.list_tools()
                live_connect_config = get_live_connect_config(
                    tools=tools,
                )
                async with genai_client.aio.live.connect(
                    model=MODEL_ID, config=live_connect_config
                ) as session:
                    await websocket.send_json(
                        {"status": "Backend is ready for conversation"}
                    )
                    gemini_session = GeminiSession(
                        session=session,
                        websocket=websocket,
                        mcp_client=mcp_client,
                    )
                    # Set initial user_id
                    gemini_session.user_id = initial_user_id
                    logging.info("Starting bidirectional communication for new user")
                    await asyncio.gather(
                        gemini_session.receive_from_client(),
                        gemini_session.receive_from_gemini(),
                        return_exceptions=True,
                    )
        except Exception as e:
            logging.error(f"Error in connect_and_run: {e!s}")
            if gemini_session:
                await gemini_session.cleanup()
            raise

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new websocket connections."""
    await websocket.accept()

    # Extract user_id from query parameters if provided
    user_id = websocket.query_params.get("user_id", "anonymous")
    logging.info(f"WebSocket connection established for user: {user_id}")

    connect_and_run = get_connect_and_run_callable(websocket, user_id)
    await connect_and_run()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
