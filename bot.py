"""
Topclass Telegram Bot
A Telegram bot that forwards user messages to the Topclass Adjuster API
and returns the AI response back to the user.
"""

import os
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Read configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TOPCLASS_API_URL = os.getenv("TOPCLASS_API_URL")
TOPCLASS_API_KEY = os.getenv("TOPCLASS_API_KEY")

# Validate required environment variables
if not all([TELEGRAM_BOT_TOKEN, TOPCLASS_API_URL, TOPCLASS_API_KEY]):
    logger.error("Missing required environment variables. Check your .env file.")
    raise ValueError("Missing required environment variables. Check your .env file.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command with a welcome message."""
    welcome_message = (
        "👋 Welcome to the Topclass Adjuster Bot!\n\n"
        "I can help you interact with the Topclass AI. "
        "Simply send me any message and I'll forward it to the AI and return the response.\n\n"
        "Use /help to see available commands."
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_message = (
        "📖 *Available Commands:*\n\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n\n"
        "💡 *How to use:*\n"
        "Just send me any message and I'll forward it to the Topclass AI for you!"
    )
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages.
    Forwards the message to the Topclass Adjuster API and returns the response.
    Shows typing action while waiting for the API response.
    """
    user_message = update.message.text
    logger.info(f"Received message from user {update.effective_user.id}: {user_message}")

    # Show typing action while processing
    await update.message.chat.send_action(action="typing")

    try:
        # Make async HTTP request to Topclass API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TOPCLASS_API_URL}/api/chat",
                headers={
                    "x-api-key": TOPCLASS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"message": user_message},
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse the response JSON
            data = response.json()

            # Extract the reply text from the response
            # Try common response field names
            reply_text = (
                data.get("reply")
                or data.get("response")
                or data.get("message")
                or data.get("text")
                or data.get("answer")
                or str(data)  # Fallback to string representation
            )

            logger.info(f"API response for user {update.effective_user.id}: {reply_text[:100]}...")
            await update.message.reply_text(reply_text)

    except httpx.TimeoutException:
        logger.error("Request to Topclass API timed out")
        await update.message.reply_text(
            "⏱️ Sorry, the request timed out. Please try again later."
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
        await update.message.reply_text(
            f"❌ API error occurred (Status: {e.response.status_code}). Please try again later."
        )
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
        await update.message.reply_text(
            "❌ Could not connect to the AI service. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An unexpected error occurred. Please try again later."
        )


def main() -> None:
    """Start the bot."""
    logger.info("Starting Topclass Telegram Bot...")

    # Create the Application (use builder pattern for v20+)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register message handler for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot in polling mode (suitable for Railway deployment)
    logger.info("Bot is now running in polling mode...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
