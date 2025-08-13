import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from global_vars import delete_time, main_menu, admin_menu, file_menu, channel_menu, remove_file_menu, settings_menu, no_caption_menu
from CMDHandle import delete_message_later, check_channel_membership, send_file_to_user
from DBConnr import (
    add_file_info, check_file, get_file, save_user, view_file, get_file_view, get_users, get_channels, set_channel,
    delete_channel, get_admins, delete_file_with_id, delete_file_with_fileid, check_password, get_user_stats,
    subscribe_newsletter, unsubscribe_newsletter, set_newsletter_unsubscribe, is_subscribed_newsletter, 
    get_scheduled_files, schedule_file, update_settings, update_message, get_settings, get_all_files
)

logger = logging.getLogger(__name__)

def get_user_data(context, key, default=None):
    return context.user_data.get(key, default)

def set_user_data(context, key, value):
    context.user_data[key] = value

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    args = context.args
    save_user(user_id)
    if args:
      try:
        param = int(args[0])
        file_info = get_file(param)
        if not file_info:
          await query.edit_message_text("⚠️ فایل پیدا نشد!")
          return
        
        channels = get_channels()
        join_channel = await check_channel_membership(context, user_id, channels)
        if not join_channel:
          if file_info[5] and not get_user_data(context, f"unlocked_{param}"):
            await update.message.reply_text("🔒 لطفاً رمز فایل را وارد کنید:", reply_markup=ForceReply(selective=True))
            set_user_data(context, "awaiting_password", param)
            return
          else:
            await send_file_to_user(context, chat_id, user_id, param)
        else:
          join_channel.append([InlineKeyboardButton("✅ عضو شدم", callback_data=f"send_file={param}")])
          reply_markup = InlineKeyboardMarkup(join_channel)
          await update.message.reply_text(
            "📢 برای استفاده از ربات، لطفاً در کانال‌های زیر عضو شوید:",reply_markup=reply_markup,)
      except Exception as e:
        logger.error(f"Error start def error : {e}")
        await update.message.reply_text("خطا در ارسال.")
    else:
      settings = get_settings()
      welcome_msg = settings[1]
      keyboard = admin_menu if user_id in get_admins() else main_menu
      await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    try:
        await query.answer()
        data = query.data.split('=')
        command = data[0]
        value = data[1] if len(data) > 1 else None
        logger.info(f"Button pressed by user {user_id}: {command}={value}")

        if command == "send_file":
            file_info = get_file(int(value))
            if not file_info:
                await query.edit_message_text("⚠️ فایل پیدا نشد!")
                return
      
            channels = get_channels()
            join_channel = await check_channel_membership(context, user_id, channels)
            if join_channel:
                join_channel.append([InlineKeyboardButton("✅ عضو شدم", callback_data=f"send_file={value}")])
                reply_markup = InlineKeyboardMarkup(join_channel)
                await query.edit_message_text("📢 برای دریافت فایل، در کانال‌های زیر عضو شوید:", reply_markup=reply_markup)
            else:
                await query.delete_message()
                if file_info[5] and not get_user_data(context, f"unlocked_{value}"):
                  await query.message.reply_text("🔒 لطفاً رمز فایل را وارد کنید:", reply_markup=ForceReply(selective=True))
                  set_user_data(context, "awaiting_password", value)
                  return
                else:
                  await send_file_to_user(context, query.message.chat_id, user_id, value)

        elif command == "no_caption":
            set_user_data(context, "temp_caption", None)
            set_user_data(context, "awaiting_caption", False)
            set_user_data(context, "awaiting_password", True)
            await query.message.reply_text("🔒 رمز فایل را وارد کنید (یا 'بدون رمز'):", reply_markup=ForceReply(selective=True))
            return

        if user_id in get_admins():
            if command == "view_user":
                stats = get_user_stats(int(value))
                if not stats['user_id']:
                    await query.edit_message_text("⚠️ کاربر پیدا نشد!")
                    return
                recent_files = "\n".join([f"- فایل {f[0]} در {f[1]}" for f in stats['recent_files']]) if stats['recent_files'] else "هیچ فایلی دیده نشده"
                profile_text = (
                    f"👤 پروفایل کاربر:\n"
                    f"🆔 آیدی: {stats['user_id']}\n"
                    f"📅 تاریخ عضویت: {stats['date_added']}\n"
                    f"👑 ادمین: {'بله' if stats['is_admin'] else 'خیر'}\n"
                    f"📊 فایل‌های دیده‌شده: {stats['views']}\n"
                    f"🔔 خبرنامه: {'فعال' if stats['newsletter_subscribed'] else 'غیرفعال'}\n"
                    f"🚫 اجازه لغو خبرنامه: {'بله' if stats['newsletter_allow_unsubscribe'] else 'خیر'}\n"
                    f"📂 فایل‌های اخیر:\n{recent_files}"
                )
                keyboard = [[InlineKeyboardButton(f"{'✅' if stats['newsletter_allow_unsubscribe'] else '❌'} اجازه لغو خبرنامه", callback_data=f"toggle_user_unsubscribe={value}")]]
                await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif command == "toggle_user_unsubscribe":
                stats = get_user_stats(int(value))
                new_value = not stats['newsletter_allow_unsubscribe']
                set_newsletter_unsubscribe(int(value), new_value)
                recent_files = "\n".join([f"- فایل {f[0]} در {f[1]}" for f in stats['recent_files']]) if stats['recent_files'] else "هیچ فایلی دیده نشده"
                profile_text = (
                    f"👤 پروفایل کاربر:\n"
                    f"🆔 آیدی: {stats['user_id']}\n"
                    f"📅 تاریخ عضویت: {stats['date_added']}\n"
                    f"👑 ادمین: {'بله' if stats['is_admin'] else 'خیر'}\n"
                    f"📊 فایل‌های دیده‌شده: {stats['views']}\n"
                    f"🔔 خبرنامه: {'فعال' if stats['newsletter_subscribed'] else 'غیرفعال'}\n"
                    f"🚫 اجازه لغو خبرنامه: {'بله' if new_value else 'خیر'}\n"
                    f"📂 فایل‌های اخیر:\n{recent_files}"
                )
                keyboard = [[InlineKeyboardButton(f"{'✅' if new_value else '❌'} اجازه لغو خبرنامه", callback_data=f"toggle_user_unsubscribe={value}")]]
                await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif command == "filter_type":
                files = get_all_files(value)
                if not files:
                    await query.edit_message_text("📂 هیچ فایلی با این نوع پیدا نشد!")
                    return
                keyboard = [[InlineKeyboardButton(f"📄 {file[3] or file[0]}", callback_data=f"send_file={file[0]}")] for file in files]
                await query.edit_message_text("📁 فایل‌های فیلترشده:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in button handler for user {user_id}: {e}")
        await query.edit_message_text("⚠️ خطایی رخ داد! دوباره تلاش کنید.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    message = update.message
    try:
        logger.info(f"File received from user {user_id}")
        if user_id not in get_admins():
            await message.reply_text("🚫 فقط ادمین‌ها می‌توانند فایل آپلود کنند!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
            return
        save_user(user_id)

        if get_user_data(context, "awaiting_file"):
            file = None
            file_type = None
            if message.document:
                file = message.document
                file_type = "document"
            elif message.photo:
                file = message.photo[-1]
                file_type = "photo"
            elif message.video:
                file = message.video
                file_type = "video"
            else:
                await message.reply_text("⚠️ این نوع فایل پشتیبانی نمی‌شود!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            file_id = file.file_id
            if message.media_group_id:
                media_group_id = message.media_group_id
                if "media_group" not in context.user_data:
                    context.user_data["media_group"] = {"media_group_id": media_group_id, "files": []}
                context.user_data["media_group"]["files"].append({"file_id": file_id, "type": file_type})
                if len(context.user_data["media_group"]["files"]) <= 10:
                    context.user_data.update({"awaiting_caption": True, "media_group": context.user_data["media_group"]})
                    if len(context.user_data["media_group"]["files"]) == 1:
                        await message.reply_text("📝 کپشن مدیا گروپ را بنویسید:", reply_markup=no_caption_menu)
                return
            else:
                context.user_data.update({"awaiting_file": False, "file_data_added": {"file_id": file_id, "type": file_type}, "awaiting_caption": True})
                await message.reply_text("📝 کپشن فایل را بنویسید:", reply_markup=no_caption_menu)
        elif get_user_data(context, "awaiting_for_fileid"):
            file = None
            if message.document:
                file = message.document
            elif message.photo:
                file = message.photo[-1]
            elif message.video:
                file = message.video
            if file:
                set_user_data(context, "rem_file_id", file.file_id)
                delete = delete_file_with_fileid(file.file_id)
                await message.reply_text("✅ فایل با موفقیت حذف شد!" if delete else "⚠️ خطا در حذف فایل!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                set_user_data(context, "awaiting_for_fileid", False)
            else:
                await message.reply_text("⚠️ لطفاً یک فایل معتبر ارسال کنید!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
    except Exception as e:
        logger.error(f"Error in handle_file for user {user_id}: {e}")
        await message.reply_text("⚠️ خطا در پردازش فایل!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    received_text = update.message.text
    try:
        logger.info(f"Text received from user {user_id}: {received_text}")
        save_user(user_id)

        if get_user_data(context, "awaiting_password") and not get_user_data(context, "file_data_added") and not get_user_data(context, "media_group"):
            file_id = get_user_data(context, "awaiting_password")
            if check_password(int(file_id), received_text):
                set_user_data(context, f"unlocked_{file_id}", True)
                set_user_data(context, "awaiting_password", None)
                await update.message.reply_text("✅ رمز درست بود! فایل در راهه...", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
                await send_file_to_user(context, update.message.chat_id, user_id, int(file_id))
            else:
                await update.message.reply_text("❌ رمز اشتباهه! دوباره تلاش کن:", reply_markup=ForceReply(selective=True))
            return

        if user_id in get_admins():
            if get_user_data(context, "send_message_to_all"):
                user_ids = get_users()
                sent_count = 0
                message = update.message
                for user in user_ids:
                    try:
                        if message.text:
                            await context.bot.send_message(chat_id=user[0], text=message.text_html, parse_mode='HTML')
                        elif message.photo:
                            await context.bot.send_photo(chat_id=user[0], photo=message.photo[-1].file_id, caption=message.caption_html, parse_mode='HTML')
                        elif message.video:
                            await context.bot.send_video(chat_id=user[0], video=message.video.file_id, caption=message.caption_html, parse_mode='HTML')
                        elif message.document:
                            await context.bot.send_document(chat_id=user[0], document=message.document.file_id, caption=message.caption_html, parse_mode='HTML')
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Error sending message to user {user[0]}: {e}")
                await update.message.reply_text(f"✅ پیام به {sent_count}/{len(user_ids)} کاربر ارسال شد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                set_user_data(context, "send_message_to_all", False)
                return

            if get_user_data(context, "awaiting_caption"):
                set_user_data(context, "temp_caption", received_text)
                set_user_data(context, "awaiting_caption", False)
                set_user_data(context, "awaiting_password", True)
                await update.message.reply_text("🔒 رمز فایل را وارد کنید (یا 'بدون رمز'):", reply_markup=ForceReply(selective=True))
                return

            if get_user_data(context, "awaiting_password") and get_user_data(context, "file_data_added"):
                file_id = get_user_data(context, "file_data_added")["file_id"]
                file_type = get_user_data(context, "file_data_added")["type"]
                caption = get_user_data(context, "temp_caption")
                password = None if received_text == "بدون رمز" else received_text
                info = add_file_info(file_id, caption, file_type, password=password)
                bot_id = str(context.bot.username).replace('@', '')
 
                context.user_data.clear()
                await update.message.reply_text(
                    f"✅ فایل با موفقیت آپلود شد!\n"
                    f"📄 اطلاعات فایل:\n"
                    f"🆔 ID فایل: <code>{info[0]}</code>\n"
                    f"🔗 لینک: https://t.me/{bot_id}?start={info[0]}",
                    reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True), parse_mode='HTML'
                )
                return

            if get_user_data(context, "awaiting_password") and get_user_data(context, "media_group"):
                media_group_id = get_user_data(context, "media_group")["media_group_id"]
                file_ids = get_user_data(context, "media_group")["files"]
                caption = get_user_data(context, "temp_caption")
                password = None if received_text == "بدون رمز" else received_text
                ids = []
                for file in file_ids:
                    file_id = file["file_id"]
                    file_type = file["type"]
                    info = add_file_info(file_id, caption, file_type, media_group_id=media_group_id, password=password)
                    ids.append(info[0])
                group_info = add_file_info(str(ids), caption, "group", media_group_id, password)
                bot_id = str(context.bot.username).replace('@', '')
                
                context.user_data.clear()
                await update.message.reply_text(
                    f"✅ مدیا گروپ با موفقیت آپلود شد!\n"
                    f"📄 اطلاعات فایل:\n"
                    f"🆔 ID گروه: <code>{group_info[0]}</code>\n"
                    f"🔗 لینک: https://t.me/{bot_id}?start={group_info[0]}",
                    reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True), parse_mode='HTML'
                )
                return

            if get_user_data(context, "awaiting_for_id"):
                if received_text.isdigit():
                    delete = delete_file_with_id(int(received_text))
                    await update.message.reply_text("✅ فایل حذف شد!" if delete else "⚠️ فایل پیدا نشد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ لطفاً ID معتبر وارد کنید!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                set_user_data(context, "awaiting_for_id", False)
                return

            if get_user_data(context, "awaiting_schedule"):
                file_id = get_user_data(context, "awaiting_schedule")
                try:
                    schedule_file(file_id, received_text)
                    set_user_data(context, "awaiting_schedule", None)
                    await update.message.reply_text("📅 فایل زمان‌بندی شد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                except ValueError:
                    await update.message.reply_text("⚠️ فرمت تاریخ نامعتبر است! از فرمت 1404-05-17 14:30 استفاده کنید.", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "awaiting_delete_time"):
                if received_text.isdigit():
                    update_settings(delete_time=int(received_text))
                    set_user_data(context, "awaiting_delete_time", False)
                    await update.message.reply_text(f"⏳ زمان حذف پیام‌ها به {received_text} ثانیه تغییر کرد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ لطفاً عدد معتبر وارد کنید!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "awaiting_welcome_message"):
                update_settings(welcome_message=received_text)
                update_message("welcome", received_text)
                set_user_data(context, "awaiting_welcome_message", False)
                await update.message.reply_text("📝 پیام خوش‌آمدگویی تغییر کرد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "awaiting_newsletter_unsubscribe"):
                if received_text.lower() in ["بله", "خیر"]:
                    new_value = 1 if received_text.lower() == "بله" else 0
                    update_settings(allow_newsletter_unsubscribe=new_value)
                    set_user_data(context, "awaiting_newsletter_unsubscribe", False)
                    await update.message.reply_text(f"🔔 اجازه لغو اشتراک خبرنامه {'فعال' if new_value else 'غیرفعال'} شد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                else:
                    await update.message.reply_text("⚠️ لطفاً 'بله' یا 'خیر' وارد کنید!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "awaiting_user_id"):
                if received_text.isdigit():
                    stats = get_user_stats(int(received_text))
                    if not stats['user_id']:
                        await update.message.reply_text("⚠️ کاربر پیدا نشد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                    else:
                        recent_files = "\n".join([f"- فایل {f[0]} در {f[1]}" for f in stats['recent_files']]) if stats['recent_files'] else "هیچ فایلی دیده نشده"
                        profile_text = (
                            f"👤 پروفایل کاربر:\n"
                            f"🆔 آیدی: {stats['user_id']}\n"
                            f"📅 تاریخ عضویت: {stats['date_added']}\n"
                            f"👑 ادمین: {'بله' if stats['is_admin'] else 'خیر'}\n"
                            f"📊 فایل‌های دیده‌شده: {stats['views']}\n"
                            f"🔔 خبرنامه: {'فعال' if stats['newsletter_subscribed'] else 'غیرفعال'}\n"
                            f"🚫 اجازه لغو خبرنامه: {'بله' if stats['newsletter_allow_unsubscribe'] else 'خیر'}\n"
                            f"📂 فایل‌های اخیر:\n{recent_files}"
                        )
                        keyboard = [[InlineKeyboardButton(f"{'✅' if stats['newsletter_allow_unsubscribe'] else '❌'} اجازه لغو خبرنامه", callback_data=f"toggle_user_unsubscribe={stats['user_id']}")]]
                        await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard))
                        await update.message.reply_text("📋 منوی اصلی:", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                    set_user_data(context, "awaiting_user_id", False)
                    return
                else:
                    await update.message.reply_text("⚠️ لطفاً آیدی معتبر وارد کنید!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "AFSCL"):
                set_user_data(context, "channel_link", received_text)
                set_user_data(context, "AFSCL", False)
                set_user_data(context, "AFSCN", True)
                await update.message.reply_text("📝 نام نمایشی کانال را وارد کنید:", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if get_user_data(context, "AFSCN"):
                set_user_data(context, "AFSCN", False)
                channel_link = get_user_data(context, "channel_link")
                set_channel(received_text, channel_link)
                await update.message.reply_text("✅ کانال اضافه شد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                return

            if received_text == "مدیریت فایل 📁":
                await update.message.reply_text("📁 یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(file_menu, resize_keyboard=True))
            elif received_text == "مدیریت کانال‌ها 📢":
                await update.message.reply_text("📢 یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(channel_menu, resize_keyboard=True))
            elif received_text == "ارسال پیام همگانی 📤":
                set_user_data(context, "send_message_to_all", True)
                await update.message.reply_text("📤 پیام مورد نظر را ارسال کنید:", reply_markup=ForceReply(selective=True))
            elif received_text == "تنظیمات ⚙️":
                await update.message.reply_text("⚙️ یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(settings_menu, resize_keyboard=True))
            elif received_text == "مدیریت کاربران 👥":
                await update.message.reply_text("👥 آیدی کاربر را برای مشاهده پروفایل وارد کنید:", reply_markup=ForceReply(selective=True))
                set_user_data(context, "awaiting_user_id", True)
            elif received_text == "پروفایل 👤":
                stats = get_user_stats(user_id)
                profile_text = (
                    f"👤 پروفایل شما:\n"
                    f"🆔 آیدی: {stats['user_id']}\n"
                    f"📅 تاریخ عضویت: {stats['date_added']}\n"
                    f"📊 فایل‌های دیده‌شده: {stats['views']}\n"
                    f"🔔 خبرنامه: {'فعال' if stats['newsletter_subscribed'] else 'غیرفعال'}"
                )
                await update.message.reply_text(profile_text, reply_markup=ReplyKeyboardMarkup(admin_menu if user_id in get_admins() else main_menu, resize_keyboard=True))
            elif received_text == "خبرنامه 🔔":
                if is_subscribed_newsletter(user_id):
                    if unsubscribe_newsletter(user_id):
                        await update.message.reply_text("🔔 شما از خبرنامه لغو اشتراک کردید! 😢", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
                    else:
                        await update.message.reply_text("🚫 لغو اشتراک خبرنامه غیرفعال است!", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
                else:
                    subscribe_newsletter(user_id)
                    await update.message.reply_text("🎉 به خبرنامه ما خوش اومدی! 🔔", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
            elif received_text == "آپلود فایل 📤":
                context.user_data.clear()
                set_user_data(context, "awaiting_file", True)
                await update.message.reply_text("📄 فایل را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
            elif received_text == "حذف فایل 🗑️":
                await update.message.reply_text("🗑️ یکی از روش‌های زیر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(remove_file_menu, resize_keyboard=True))
            elif received_text == "زمان‌بندی فایل 📅":
                set_user_data(context, "awaiting_schedule", 0)
                await update.message.reply_text("📅 ID فایل و تاریخ انتشار را وارد کنید (مثل: 123 1404-05-17 14:30):", reply_markup=ReplyKeyboardRemove())
            elif received_text == "با ID 🆔":
                await update.message.reply_text("🆔 ایدی فایلی که می‌خواهید حذف کنید را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
                set_user_data(context, "awaiting_for_id", True)
            elif received_text == "با فایل 📂":
                await update.message.reply_text("📂 فایلی که می‌خواهید حذف کنید را ارسال کنید:", reply_markup=ReplyKeyboardRemove())
                set_user_data(context, "awaiting_for_fileid", True)
            elif received_text == "افزودن کانال ➕":
                await update.message.reply_text("🔗 لینک کانال را ارسال کنید (باید عمومی باشد):", reply_markup=ReplyKeyboardRemove())
                set_user_data(context, "AFSCL", True)
            elif received_text == "حذف کانال ➖":
                channels = get_channels()
                if not channels:
                    await update.message.reply_text("هیچ کانالی وجود ندارد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                    return
                keyboard = [[InlineKeyboardButton(f"{channel[0]}", callback_data=f"rem_channel={channel[1]}")] for channel in channels]
                await update.message.reply_text("📢 کانالی را که می‌خواهید حذف کنید انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif received_text == "زمان حذف پیام‌ها ⏳":
                set_user_data(context, "awaiting_delete_time", True)
                await update.message.reply_text("⏳ زمان حذف پیام‌ها را به ثانیه وارد کنید (مثل 30):", reply_markup=ReplyKeyboardRemove())
            elif received_text == "پیام خوش‌آمدگویی 📝":
                set_user_data(context, "awaiting_welcome_message", True)
                await update.message.reply_text("📝 پیام خوش‌آمدگویی جدید را وارد کنید:", reply_markup=ReplyKeyboardRemove())
            elif received_text == "تنظیمات خبرنامه 🔔":
                set_user_data(context, "awaiting_newsletter_unsubscribe", True)
                settings = get_settings()
                await update.message.reply_text(f"🔔 اجازه لغو اشتراک خبرنامه فعلی: {'فعال' if settings[3] else 'غیرفعال'}\nلطفاً 'بله' یا 'خیر' وارد کنید:", reply_markup=ReplyKeyboardRemove())
            elif received_text == "فیلتر فایل‌ها 📂":
                keyboard = [
                    ["📄 اسناد", "🖼️ تصاویر", "🎥 ویدیوها"],
                    ["🔙 بازگشت"]
                ]
                await update.message.reply_text("📂 نوع فایل را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            elif received_text in ["📄 اسناد", "🖼️ تصاویر", "🎥 ویدیوها"]:
                file_type = {"📄 اسناد": "document", "🖼️ تصاویر": "photo", "🎥 ویدیوها": "video"}[received_text]
                files = get_all_files(file_type)
                if not files:
                    await update.message.reply_text("📂 هیچ فایلی با این نوع پیدا نشد!", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
                    return
                keyboard = [[InlineKeyboardButton(f"📄 {file[3] or file[0]}", callback_data=f"send_file={file[0]}")] for file in files]
                await update.message.reply_text("📁 فایل‌های فیلترشده:", reply_markup=InlineKeyboardMarkup(keyboard))
                await update.message.reply_text("📋 منوی اصلی:", reply_markup=ReplyKeyboardMarkup(admin_menu, resize_keyboard=True))
            elif received_text == "🔙 بازگشت":
                await update.message.reply_text("📋 منوی اصلی:", reply_markup=ReplyKeyboardMarkup(admin_menu if user_id in get_admins() else main_menu, resize_keyboard=True))
            else:
                await update.message.reply_text("⚠️ دستور نامعتبر! از منوی زیر استفاده کنید:", reply_markup=ReplyKeyboardMarkup(admin_menu if user_id in get_admins() else main_menu, resize_keyboard=True))
        else:
            if received_text == "پروفایل 👤":
                stats = get_user_stats(user_id)
                profile_text = (
                    f"👤 پروفایل شما:\n"
                    f"🆔 آیدی: {stats['user_id']}\n"
                    f"📅 تاریخ عضویت: {stats['date_added']}\n"
                    f"📊 فایل‌های دیده‌شده: {stats['views']}\n"
                    f"🔔 خبرنامه: {'فعال' if stats['newsletter_subscribed'] else 'غیرفعال'}"
                )
                await update.message.reply_text(profile_text, reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
            elif received_text == "خبرنامه 🔔":
                if is_subscribed_newsletter(user_id):
                    if unsubscribe_newsletter(user_id):
                        await update.message.reply_text("🔔 شما از خبرنامه لغو اشتراک کردید! 😢", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
                    else:
                        await update.message.reply_text("🚫 لغو اشتراک خبرنامه غیرفعال است!", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
                else:
                    subscribe_newsletter(user_id)
                    await update.message.reply_text("🎉 به خبرنامه ما خوش اومدی! 🔔", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
            else:
                await update.message.reply_text("⚠️ دستور نامعتبر! از منوی زیر استفاده کنید:", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))
    except Exception as e:
        logger.error(f"Error in handle_text for user {user_id}: {e}")
        await update.message.reply_text("⚠️ خطایی رخ داد! دوباره تلاش کنید.", reply_markup=ReplyKeyboardMarkup(admin_menu if user_id in get_admins() else main_menu, resize_keyboard=True))