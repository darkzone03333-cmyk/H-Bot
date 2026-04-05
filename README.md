# Topclass Telegram Bot

A Telegram bot that forwards user messages to the Topclass Adjuster API and returns the AI response back to the user.

## Features

- 🤖 Forwards all user messages to the Topclass AI API
- ⌨️ Shows "typing..." action while waiting for API response
- 🛡️ Graceful error handling (API down, timeout, etc.)
- 📝 `/start` and `/help` commands
- 🚀 Ready for Railway deployment (polling mode)

## Prerequisites

- Python 3.8+
- A Telegram Bot Token (get it from [@BotFather](https://t.me/BotFather))
- Access to the Topclass Adjuster API (URL and API key)

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd topclass-telegram-bot
   ```

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your values:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   TOPCLASS_API_URL=https://your-railway-app.up.railway.app
   TOPCLASS_API_KEY=your_api_key_here
   ```

5. **Run the bot**
   ```bash
   python bot.py
   ```

## Deployment on Railway

1. Push your code to a GitHub repository
2. Create a new project on [Railway](https://railway.app/)
3. Connect your GitHub repository
4. Add the following environment variables in Railway:
   - `TELEGRAM_BOT_TOKEN`
   - `TOPCLASS_API_URL`
   - `TOPCLASS_API_KEY`
5. Deploy! The `Procfile` will automatically start the bot in polling mode.

## Project Structure

```
topclass-telegram-bot/
├── bot.py              # Main bot file
├── requirements.txt    # Dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Ignore .env and __pycache__
├── Procfile            # For Railway deployment
└── README.md           # This file
```

## API Integration

The bot communicates with the Topclass Adjuster API:
- **Endpoint:** `POST /api/chat`
- **Headers:** `x-api-key` for authentication
- **Request Body:** `{"message": "<user_message>"}`
- **Response:** Expects a JSON response with a text field (supports `reply`, `response`, `message`, `text`, or `answer`)

## License

MIT
