import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config.settings import BOT_TOKEN
from src.handlers import start, button_handler, handle_message, handle_file, unknown

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def setup_handlers(app: Application):
    """Register all command handlers"""
    # Commands
    app.add_handler(CommandHandler("start", start))
    
    # Callback queries (buttons)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # File uploads (documents, photos, videos, audio)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_file))
    
    # Unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown))


def run_bot():
    """Initialize and run the bot"""
    logger.info("Starting GitHub Copilot CLI Telegram Bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(app)
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    run_bot()
