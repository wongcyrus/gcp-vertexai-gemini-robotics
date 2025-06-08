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
import json
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, Literal

import backoff
import fastmcp
from app.agent import MODEL_ID, genai_client, get_live_connect_config
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import logging as google_cloud_logging
from google.genai import types
from google.genai.types import LiveServerToolCall
from pydantic import BaseModel
from websockets.exceptions import ConnectionClosedError

config = {
    "mcpServers": {
        "robot": {
            "command": "uv",
            "args": [
                "--directory",
                "/workspaces/gcp-vertexai-gemini-robotics/robot-mcp-server/humanoid",
                "run",
                "python",
                "server.py",
            ],
            "env": {
                "USE_API_PROXRY": "true",
                "ROBOT_API_URL": "https://6mz6soy3j3.execute-api.us-east-1.amazonaws.com/prod/run_action/robot_9",
            },
        },
    }
}

# mcp_client is now managed as app.state.mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    app.state.mcp_client = fastmcp.Client(config)
    yield
    # Clean up the ML models and release the resources
    app.state.mcp_client.close()


app = FastAPI(lifespan=lifespan)
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
        mcp_client: Any,
    ) -> None:
        """Initialize the Gemini session.

        Args:
            session: The Gemini session
            websocket: The client websocket connection
            user_id: Unique identifier for this client
            tool_functions: Dictionary of available tool functions
        """
        self.session = session
        self.websocket = websocket
        self.mcp_client = mcp_client
        self.run_id = "n/a"
        self.user_id = "n/a"
        self._tool_tasks: list[asyncio.Task] = []

    async def receive_from_client(self) -> None:
        """Listen for and process messages from the client.

        Continuously receives messages and forwards audio data to Gemini.
        Handles connection errors gracefully.
        """
        while True:
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
                    logging.warning(f"Received unexpected input from client: {data}")
            except ConnectionClosedError as e:
                logging.warning(f"Client {self.user_id} closed connection: {e}")
                break
            except Exception as e:
                logging.error(f"Error receiving from client {self.user_id}: {e!s}")
                break

    async def _handle_tool_call(
        self, session: Any, tool_call: LiveServerToolCall
    ) -> None:
        """Process tool calls from Gemini and send back responses."""
        if tool_call.function_calls is None:
            logging.debug("No function calls in tool_call")
            return

        for fc in tool_call.function_calls:
            logging.debug(f"Calling tool function: {fc.name} with args: {fc.args}")

            response = await self.mcp_client.call_tool(fc.name, fc.args)

            tool_response = types.LiveClientToolResponse(
                function_responses=[
                    types.FunctionResponse(name=fc.name, id=fc.id, response=response)
                ]
            )
            logging.debug(f"Tool response: {tool_response}")
            await session.send(input=tool_response)

    async def receive_from_gemini(self) -> None:
        """Listen for and process messages from Gemini without blocking."""
        while result := await self.session._ws.recv(decode=False):
            await self.websocket.send_bytes(result)
            raw_message = json.loads(result)
            if "toolCall" in raw_message:
                message = types.LiveServerMessage.model_validate(raw_message)
                tool_call = LiveServerToolCall.model_validate(message.tool_call)
                # Create a separate task to handle the tool call without blocking
                task = asyncio.create_task(
                    self._handle_tool_call(self.session, tool_call)
                )
                self._tool_tasks.append(task)


def get_connect_and_run_callable(websocket: WebSocket) -> Callable:
    """Create a callable that handles Gemini connection with retry logic.

    Args:
        websocket: The client websocket connection

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
        mcp_client = app.state.mcp_client
        async with mcp_client:
            mcp_session = mcp_client.session
            live_connect_config = get_live_connect_config(
                tools=[mcp_session],
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
                logging.info("Starting bidirectional communication")
                await asyncio.gather(
                    gemini_session.receive_from_client(),
                    gemini_session.receive_from_gemini(),
                )

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new websocket connections."""
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(websocket)
    await connect_and_run()


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    run_id: str
    user_id: str | None
    log_type: Literal["feedback"] = "feedback"


@app.post("/feedback")
async def collect_feedback(feedback_dict: Feedback) -> None:
    """Collect and log feedback."""
    feedback_data = feedback_dict.model_dump()
    logger.log_struct(feedback_data, severity="INFO")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
