from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from global_vars import admin_menu
from DBConnr import get_all_files

async def filter_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ["📄 اسناد", "🖼️ تصاویر", "🎥 ویدیوها"],
        ["🔙 بازگشت"]
    ]
    await update.message.reply_text("📂 نوع فایل را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))