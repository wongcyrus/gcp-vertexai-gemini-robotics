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
                "ROBOT_API_URL": "http://127.0.0.1:5000/run_action/",
                "ROBOT_IMAGE_API_URL": "http://127.0.0.1:5000:5000/run_action/",
                "SESSION_KEY": "your_email_address",
            },
        },
    }
}
