install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source ~/.bashrc; }
	uv sync --dev --extra jupyter --frozen && npm --prefix frontend install

test:
	uv run pytest tests/unit && uv run pytest tests/integration

playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                         |"
	@echo "==============================================================================="
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload &
	PORT=8501 npm --prefix frontend start

backend:
	PROJECT_ID=$$(gcloud config get-value project) && \
	gcloud run deploy robot-adk-agent \
		--source . \
		--memory "4Gi" \
		--project $$PROJECT_ID \
		--region "us-central1" \
		--no-allow-unauthenticated \
		--labels "created-by=adk" \
		--set-env-vars \
		"COMMIT_SHA=$(shell git rev-parse HEAD)"

local-backend:
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

ui:
	PORT=8501 npm --prefix frontend start

setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .

remove-backend:
	PROJECT_ID=$$(gcloud config get-value project) && \
	gcloud run services delete robot-adk-agent --region us-central1 --project $$PROJECT_ID --quiet
