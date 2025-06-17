# robot-adk-agent

A real-time multimodal RAG agent powered by Gemini Live API, supporting audio/video/text chat with vector DB-backed responses
Agent generated with [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `0.5.0`

## Project Structure

This project is organized as follows:

```
robot-adk-agent/
├── app/                 # Core application code
│   ├── agent.py         # Main agent logic
│   ├── server.py        # FastAPI Backend server
│   └── utils/           # Utility functions and helpers
├── deployment/          # Infrastructure and deployment scripts
├── notebooks/           # Jupyter notebooks for prototyping and evaluation
├── tests/               # Unit, integration, and load tests
├── Makefile             # Makefile for common commands
└── pyproject.toml       # Project dependencies and configuration
```

## Requirements

Before you begin, ensure you have:

- **uv**: Python package manager - [Install](https://docs.astral.sh/uv/getting-started/installation/)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform**: For infrastructure deployment - [Install](https://developer.hashicorp.com/terraform/downloads)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)

## Authentication for Vertex AI

Before running the backend with Vertex AI, authenticate your local environment with Google Cloud:

```bash
gcloud auth application-default login
```

This command obtains user credentials and sets up Application Default Credentials (ADC), which are required for Vertex AI client libraries to access Google Cloud resources.

## Quick Start (Local Testing)

Install required packages and launch the local development environment:

```bash
make install && make playground
```

## Commands

| Command              | Description                                                    |
| -------------------- | -------------------------------------------------------------- |
| `make install`       | Install all required dependencies using uv                     |
| `make playground`    | Launch local development environment with backend and frontend |
| `make backend`       | Deploy agent to Cloud Run                                      |
| `make local-backend` | Deploy agent to Cloud Run                                      |
| `make ui`            | Launch Agent Playground front-end only                         |
| `make test`          | Run unit and integration tests                                 |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                |
| `make setup-dev-env` | Set up development environment resources using Terraform       |
| `uv run jupyter lab` | Launch Jupyter notebook                                        |

For full command options and usage, refer to the [Makefile](Makefile).

## Usage

This template follows a "bring your own agent" approach - you focus on your business logic in `app/agent.py`, and the template handles the surrounding components (UI, infrastructure, deployment, monitoring).

Here’s the recommended workflow for local development:

1.  **Install Dependencies (if needed):**

    ```bash
    make install
    ```

2.  **Start the Backend Server:**
    Open a terminal and run:

    ```bash
    # Authenticate with Google Cloud for Vertex AI access
    gcloud auth application-default login
    gcloud config set project <project-id>
    make backend
    ```

    The backend is ready when you see `INFO:     Application startup complete.` Wait for this message before starting the frontend.

    <details>
    <summary><b>Optional: Use AI Studio / API Key instead of Vertex AI</b></summary>

    By default, the backend uses Vertex AI and Application Default Credentials. If you prefer to use Google AI Studio and an API key:

    ```bash
    export VERTEXAI=false
    export GOOGLE_API_KEY="your-google-api-key" # Replace with your actual key
    make backend
    ```

    Ensure `GOOGLE_API_KEY` is set correctly in your environment.
    </details>
    <br>

3.  **Start the Frontend UI:**
    Open _another_ terminal and run:

    ```bash
    make ui
    ```

    This launches the Streamlit application, which connects to the backend server (by default at `http://localhost:8000`).

4.  **Interact and Iterate:**
    - Open the Streamlit UI in your browser (usually `http://localhost:8501` or `http://localhost:3001`).
    - Click the play button in the UI to connect to the backend.
    - Interact with the agent! Try prompts like: _"Using the tool you have, define Governance in the context MLOPs"_
    - Modify the agent logic in `app/agent.py`. The backend server (FastAPI with `uvicorn --reload`) should automatically restart when you save changes. Refresh the frontend if needed to see behavioral changes.

<details>
<summary><b>Cloud Shell Usage</b></summary>

To run the agent using Google Cloud Shell:

1.  **Start the Frontend:**
    In a Cloud Shell tab, run:

    ```bash
    make ui
    ```

    Accept prompts to use a different port if 3000 is busy. Click the `localhost:PORT` link for the web preview.

2.  **Start the Backend:**
    Open a _new_ Cloud Shell tab. Set your project: `gcloud config set project [PROJECT_ID]`. Then run:

    ```bash
    make backend
    ```

3.  **Configure Backend Web Preview:**
    Use the Cloud Shell Web Preview feature to expose port 8000. Change the default port from 8080 to 8000. See [Cloud Shell Web Preview documentation](https://cloud.google.com/shell/docs/using-web-preview#preview_the_application).

4.  **Connect Frontend to Backend:**
    - Copy the URL generated by the backend web preview (e.g., `https://8000-cs-....cloudshell.dev/`).
    - Paste this URL into the "Server URL" field in the frontend UI settings (in the first tab).
    - Click the "Play button" to connect.

- **Note:** The feedback feature in the frontend might not work reliably in Cloud Shell due to cross-origin issues between the preview URLs.
</details>

</details>

## Deployment

> **Note:** For a streamlined one-command deployment of the entire CI/CD pipeline and infrastructure using Terraform, you can use the [`agent-starter-pack setup-cicd` CLI command](https://googlecloudplatform.github.io/agent-starter-pack/cli/setup_cicd.html). Currently only supporting Github.

### Dev Environment

You can test deployment towards a Dev Environment using the following command:

```bash
gcloud config set project <your-dev-project-id>
make backend
```

**Accessing the Deployed Backend Locally:**

To connect your local frontend (`make ui`) to the backend deployed on Cloud Run, use the `gcloud` proxy:

1.  **Start the proxy:**

    ```bash
    # Replace with your actual service name, project, and region
    gcloud run services proxy gemini-agent-service --port 8000 --project $PROJECT_ID --region $REGION
    ```

    Keep this terminal running.

2.  **Connect Frontend:** Your deployed backend is now accessible locally at `http://localhost:8000`. Point your Streamlit UI to this address.

The repository includes a Terraform configuration for the setup of the Dev Google Cloud project.
See [deployment/README.md](deployment/README.md) for instructions.

### Production Deployment

The repository includes a Terraform configuration for the setup of a production Google Cloud project. Refer to [deployment/README.md](deployment/README.md) for detailed instructions on how to deploy the infrastructure and application.
