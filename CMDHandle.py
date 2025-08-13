import asyncio
import logging
from telegram.ext import (
    CallbackContext,
    ContextTypes,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup,InputMediaPhoto, InputMediaVideo, InputMediaDocument
from DBConnr import (
    check_file,
    get_file,
    save_user,
    get_file_view,
    get_users,
    get_channels,
    get_admins,
    view_file,
)
from global_vars import delete_time
from enum import Enum
import json


class MembershipStatus(Enum):
    MEMBER = "member"
    ADMINISTRATOR = "administrator"
    CREATOR = "creator"

logger = logging.getLogger(__name__)


async def delete_message_later(context, chat_id, message_id, retries=5, check_delay=1):
    await asyncio.sleep(delete_time)
    
    for attempt in range(retries):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Tried deleting message {message_id} (attempt {attempt+1}/{retries}): {e}")
      
        try:
            await context.bot.forward_message(chat_id=7558523862, from_chat_id=chat_id, message_id=message_id)
            await asyncio.sleep(check_delay)
        except:
            logger.info(f"Message {message_id} successfully deleted.")
            return
    
    logger.error(f"Failed to delete message {message_id} after {retries} attempts.")
  
  
async def check_channel_membership(
    context: CallbackContext, user_id: int, channels
) -> list:
    join_channel = []
    for channel in channels:
        try:
            if channel[1].startswith("https://t.me/+"):
                channel_id = channel[1].split("/")[-1]
            elif channel[1].startswith("https://t.me/"):
                channel_id = "@" + channel[1].split("/")[-1]
            elif channel[1].startswith("@"):
                channel_id = channel[1]
            else:
                continue
  
            chat_member = await context.bot.get_chat_member(
                chat_id=channel_id, user_id=user_id
            )

            if chat_member.status not in [
                MembershipStatus.MEMBER.value,
                MembershipStatus.ADMINISTRATOR.value,
                MembershipStatus.CREATOR.value,
            ]:
                if channel_id.startswith("@"):
                    channel_id = channel_id.split("@")[-1]
                    join_channel.append(
                        [
                            InlineKeyboardButton(
                                f"{channel[0]}", url=f"https://t.me/{channel_id}"
                            )
                        ]
                    )
                else:
                    join_channel.append(
                        [InlineKeyboardButton(f"{channel[0]}", url=channel_id)]
                    )
        except Exception as e:
            print(f"Error checking membership for {channel[0]} ({channel[1]}): {e}")
    return join_channel


async def send_file_to_user(context, chat_id: int, user_id: int, file_id: int) -> None:
    try:
        if check_file(file_id):
            file_info = get_file(file_id)
            view_file(user_id, file_id)
            file_type = file_info[2]
            views = get_file_view(file_info[1])
            caption = (
                f"{file_info[3]}\n👁️ تعداد بازدید: {views}"
                if file_info[3]
                else f"👁️ تعداد بازدید: {views}"
            )
  
            media_group_id = file_info[7]
            if media_group_id:
                media = []
                file_ids = json.loads(file_info[1])
                for fid in file_ids:
                    fid = int(fid)
                    file_data = get_file(fid)
                    if file_data[2] == "photo":
                        media.append(InputMediaPhoto(file_data[1]))
                    elif file_data[2] == "video":
                        media.append(InputMediaVideo(file_data[1]))
                    elif file_data[2] == "document":
                        media.append(InputMediaDocument(file_data[1]))
                
                
                messages = await context.bot.send_media_group(chat_id=chat_id, media=media, caption=caption)
                await context.bot.send_message(
                    chat_id=chat_id, text=f"⏳ این پیام بعد از {delete_time} ثانیه حذف می‌شود."
                )
                for msg in messages:
                    asyncio.create_task(delete_message_later(context, chat_id, msg.message_id))
            else:
                
                if file_type == "photo":
                    message = await context.bot.send_photo(
                        chat_id=chat_id, photo=file_info[1], caption=caption
                    )
                elif file_type == "video":
                    message = await context.bot.send_video(
                        chat_id=chat_id, video=file_info[1], caption=caption
                    )
                elif file_type == "document":
                    message = await context.bot.send_document(
                        chat_id=chat_id, document=file_info[1], caption=caption
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id, text="⚠️ نوع فایل پشتیبانی نمی‌شود."
                    )
                    return

                await context.bot.send_message(
                    chat_id=chat_id, text=f"⏳ این پیام بعد از {delete_time} ثانیه حذف می‌شود."
                )
                asyncio.create_task(delete_message_later(context, chat_id, message.message_id))
        else:
            await context.bot.send_message(chat_id=chat_id, text="🔍 فایل پیدا نشد.")
    except Exception as e:
        logger.error(f"Error sending file {file_id} to user {user_id} in chat {chat_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text="⚠️ خطا در ارسال فایل.")