# Containerized Slackbot

A containerized Slackbot built using the Bolt framework for Python.

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
     - Add Bot Token Scopes: `chat:write`, `commands`, `app_mentions:read`, `channels:history`, `im:history`
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

- The app is set up to restart automatically if it crashes
- Code changes in your local directory will be reflected in the container (volumes are mounted)
- View logs directly from the Docker container

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
