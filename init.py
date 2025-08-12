import sqlite3
from getpass import getpass
from datetime import datetime
from DBConnr import init_db

def init():
    init_db()
    bot_token = getpass("لطفا کد توکن ربات رو وارد کن: ")
    admin_ids = input("آیدی ادمین‌ها رو با کاما جدا کن (مثل 123,456): ")
    delete_time = int(input("زمان حذف پیام‌ها رو به ثانیه وارد کن (مثل 30): "))
    welcome_msg = input("پیام خوش‌آمدگویی رو بنویس: ")
    allow_unsubscribe = input("آیا کاربران اجازه لغو اشتراک خبرنامه داشته باشند؟ (بله/خیر): ").lower() == "بله"

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (delete_time, welcome_message, allow_user_filters, allow_newsletter_unsubscribe) VALUES (?, ?, ?, ?)', 
                   (delete_time, welcome_msg, 0, 1 if allow_unsubscribe else 0))
    cursor.execute('INSERT OR REPLACE INTO messages (key, text) VALUES (?, ?)', ("welcome", welcome_msg))
    for admin_id in admin_ids.split(','):
        cursor.execute('INSERT OR IGNORE INTO users (user_id, admin, date_added) VALUES (?, 1, ?)', 
                       (int(admin_id.strip()), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    with open(".env", "w") as f:
        f.write(f"BOT_TOKEN={bot_token}")
    print("🎉 تنظیمات اولیه با موفقیت انجام شد!")

if __name__ == "__main__":
    init()