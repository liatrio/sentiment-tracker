# Sentiment Tracker Bot

A Slack bot designed to collect and analyze team sentiment through interactive feedback sessions. It's built using the Bolt framework for Python and containerized with Docker.


## Prerequisites

- Docker and Docker Compose
- Slack API credentials (Bot Token and App Token)

## Setup

1. **Create a Slack App**:
   - Go to [https://api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" and choose "From scratch"
   - Name your app and select the workspace to install it to
   - In the "Add features and functionality" section:
     - Enable Socket Mode
     - Add Bot Token Scopes: `chat:write`, `commands`, `app_mentions:read`, `channels:history`, `im:history`, `users:read` (to resolve user IDs to names for anonymized reporting)
     - Create slash commands (e.g., `/ping`)
   - Install the app to your workspace and note the Bot Token
   - Generate an App-Level Token with `connections:write` scope

2. **Configure Environment Variables**:
   - Copy `.env.example` to `.env`:
     ```
     cp .env.example .env
     ```
   - Update `.env` with your Slack tokens

## Running Locally

Start the bot using Docker Compose:

```bash
docker-compose up --build
```

## Development

This project uses `Taskfile.yml` to manage common development tasks. After cloning the repository, initialize the development environment:

```bash
task init
```

This will set up a virtual environment and install all necessary dependencies.

- The application, when run via `docker-compose up`, is configured for live reloading. Code changes in your local `src/` directory will be reflected in the running container.
- View logs directly from the Docker container using `docker-compose logs -f`.

### Testing

- Run all unit tests using `task test`.
- Tests are located in the `tests/` directory.
- The project aims for high test coverage for all core logic.

### Code Quality

- This project uses pre-commit hooks to enforce code style and quality automatically before commits.
- Install the hooks after cloning:
  ```bash
  task pre-commit-install
  ```
- Run all linters (Flake8, Black check, isort check, MyPy):
  ```bash
  task lint
  ```
- Format code automatically with Black and isort:
  ```bash
  task format
  ```
- You can also manually trigger pre-commit hooks on all files:
  ```bash
  task pre-commit-run
  ```

## Project Structure

- `src/`: Contains the main application code.
  - `app.py`: The main Slack bot application logic, including event handlers and middleware.
  - `session_data.py`: Defines the `SessionData` class for storing individual feedback session details.
  - `session_store.py`: Implements `ThreadSafeSessionStore` for managing active feedback sessions in memory.
- `tests/`: Contains all unit tests, mirroring the structure of `src/`.
- `Dockerfile`: Defines the instructions for building the Docker image for the application.
- `docker-compose.yml`: Configures the services, networks, and volumes for local Docker-based development.
- `Taskfile.yml`: Defines tasks for common development operations like testing, linting, formatting, and environment setup (using [Task](https://taskfile.dev/)).
- `requirements.txt`: Lists the Python dependencies for the application.
- `requirements-dev.txt`: Lists additional Python dependencies for development and testing.
- `.pre-commit-config.yaml`: Configuration for pre-commit hooks (Black, Flake8, isort, etc.).
- `.env.example`: Example environment file. Copy to `.env` and fill in your credentials.

## Adding New Features

To add new features to your bot:
- Add message listeners with `@app.message()`
- Add slash command handlers with `@app.command()`
- Add event handlers with `@app.event()`

Example:
```python
@app.message("help")
def handle_help(message, say):
    say("Here's how you can use this bot: ...")
```

## Troubleshooting

- Check Docker logs: `docker-compose logs`
- Ensure your bot has been invited to the channel you're testing in
- Verify your tokens are correct in the `.env` file
