import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handler import start, button, handle_file, handle_text
from dotenv import load_dotenv
import os
from log_filter import setup_logging
import logging

async def error_handler(update, context):
    logger = logging.getLogger(__name__)
    logger.error(f"Update {update} caused error {context.error}")

def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN not found in .env file")
        return

    setup_logging(token)
    logger = logging.getLogger(__name__)
    logger.info("Bot started")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == "__main__":
    main()