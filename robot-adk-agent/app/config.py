import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = {
    "mcpServers": {
        "robot": {
            "command": "uv",
            "args": [
                "--directory",
                os.path.join(BASE_DIR, "robot-mcp-server", "humanoid"),
                "run",
                "python",
                "server.py",
            ],
            "env": {
                "ROBOT_API_URL": "https://6mz6soy3j3.execute-api.us-east-1.amazonaws.com/prod/run_action/",
                "ROBOT_IMAGE_API_URL": "https:///6mz6soy3j3.execute-api.us-east-1.amazonaws.com/prod/run_action/",
            },
        },
    }
}
