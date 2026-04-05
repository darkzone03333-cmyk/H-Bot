"""
MyBot - Telegram chatbot with AI provider switching via environment variables.
Supports OpenRouter, OpenAI, NVIDIA, Groq, Together, and custom providers.
"""

import logging
import os
from typing import Optional

import openai
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------
PROVIDER_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "custom": None,  # resolved from AI_BASE_URL
}


def resolve_base_url(provider: str) -> str:
    """Resolve the base URL for the given AI provider."""
    if provider not in PROVIDER_URLS:
        raise ValueError(
            f"Unknown AI_PROVIDER: '{provider}'. "
            f"Must be one of: {', '.join(PROVIDER_URLS.keys())}"
        )
    if provider == "custom":
        custom_url = os.getenv("AI_BASE_URL")
        if not custom_url:
            raise ValueError(
                "AI_PROVIDER is 'custom' but AI_BASE_URL is not set. "
                "Please set AI_BASE_URL in environment variables."
            )
        return custom_url
    return PROVIDER_URLS[provider]


# ---------------------------------------------------------------------------
# Configuration (read at startup)
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "")
AI_API_KEY: str = os.getenv("AI_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free")
SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", "")

# Validate required env vars at module load time
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")
if not AI_PROVIDER:
    raise RuntimeError("AI_PROVIDER environment variable is not set.")
if not AI_API_KEY:
    raise RuntimeError("AI_API_KEY environment variable is not set.")

RESOLVED_BASE_URL: str = resolve_base_url(AI_PROVIDER)

# ---------------------------------------------------------------------------
# OpenAI client (works with any OpenAI-compatible provider)
# ---------------------------------------------------------------------------
client = openai.AsyncOpenAI(api_key=AI_API_KEY, base_url=RESOLVED_BASE_URL)

# ---------------------------------------------------------------------------
# Per-user conversation history (in-memory)
# ---------------------------------------------------------------------------
# Maps user_id -> list of message dicts
conversation_history: dict[int, list[dict[str, str]]] = {}

# Maximum messages to keep per user (prevents unbounded memory growth)
MAX_HISTORY_LENGTH: int = 50


def get_user_history(user_id: int) -> list[dict[str, str]]:
    """Return the conversation history for a given user, initializing if needed."""
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    return conversation_history[user_id]


def add_to_history(user_id: int, role: str, content: str) -> None:
    """Add a message to the user's conversation history."""
    history = get_user_history(user_id)
    history.append({"role": role, "content": content})
    # Trim history to prevent memory issues
    if len(history) > MAX_HISTORY_LENGTH:
        conversation_history[user_id] = history[-MAX_HISTORY_LENGTH:]


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command — send a welcome message."""
    welcome_msg = (
        "👋 Welcome! I'm MyBot.\n\n"
        "You can ask me anything and I'll do my best to help. "
        "I remember our conversation, so feel free to ask follow-up questions!"
    )
    await update.message.reply_text(welcome_msg)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_msg = (
        "🤖 *MyBot Help*\n\n"
        "Just send me any message and I'll respond!\n"
        "I maintain conversation history, so you can have a natural back-and-forth.\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/clear - Clear conversation history"
    )
    await update.message.reply_text(help_msg, parse_mode="Markdown")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /clear command — reset conversation history for the user."""
    user_id = update.effective_user.id
    if user_id in conversation_history:
        del conversation_history[user_id]
    await update.message.reply_text("🧹 Conversation history cleared!")


# ---------------------------------------------------------------------------
# Message handler (AI interaction)
# ---------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages — call the AI API and respond."""
    user_id = update.effective_user.id
    user_message = update.message.text

    # Add user message to history
    add_to_history(user_id, "user", user_message)

    # Build the messages list for the API call
    messages: list[dict[str, str]] = []

    # Add system prompt if configured
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # Add conversation history
    messages.extend(get_user_history(user_id))

    # Typing indicator
    await update.message.chat.send_action("typing")

    try:
        # Call the AI provider
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        # Extract the assistant's reply
        assistant_reply: str = response.choices[0].message.content or ""

        # Add assistant reply to history
        add_to_history(user_id, "assistant", assistant_reply)

        # Send the reply to the user
        await update.message.reply_text(assistant_reply)

    except openai.APIConnectionError as e:
        logger.error("API connection error: %s", e)
        await update.message.reply_text(
            "❌ Sorry, I couldn't connect to the AI service. Please try again later."
        )
    except openai.RateLimitError as e:
        logger.error("Rate limit exceeded: %s", e)
        await update.message.reply_text(
            "⏳ Rate limit exceeded. Please wait a moment and try again."
        )
    except openai.APIStatusError as e:
        logger.error("API status error: %s", e)
        await update.message.reply_text(
            "❌ The AI service returned an error. Please try again later."
        )
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        await update.message.reply_text(
            "❌ An unexpected error occurred. Please try again later."
        )


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Exception while handling an update: %s", context.error, exc_info=context.error)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Start the bot."""
    logger.info("Starting MyBot with provider: %s (%s)", AI_PROVIDER, RESOLVED_BASE_URL)
    logger.info("Model: %s", MODEL_NAME)

    # Build the application
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is running... (long polling mode)")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
