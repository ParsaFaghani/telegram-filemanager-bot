import sqlite3
from datetime import datetime
import jdatetime

DB_PATH = "data.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE,
            file_type TEXT,
            description TEXT,
            views INTEGER DEFAULT 0,
            password TEXT,
            auto_remove INTEGER CHECK(auto_remove IN (0,1)) DEFAULT 1,
            media_group_id TEXT,
            scheduled_time TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            admin INTEGER CHECK(admin IN (0,1)) DEFAULT 0,
            date_added TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_views (
            user_id INTEGER,
            file_id TEXT,
            view_time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(file_id) REFERENCES files(file_id)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            delete_time INTEGER DEFAULT 30,
            welcome_message TEXT DEFAULT '👋 به ربات ما خوش اومدی!',
            allow_user_filters INTEGER CHECK(allow_user_filters IN (0,1)) DEFAULT 0,
            allow_newsletter_unsubscribe INTEGER CHECK(allow_newsletter_unsubscribe IN (0,1)) DEFAULT 1
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            key TEXT PRIMARY KEY,
            text TEXT
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS check_channels (
            name TEXT,
            id TEXT UNIQUE,
            joins INTEGER DEFAULT 0
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS newsletter (
            user_id INTEGER UNIQUE,
            subscribed_at TEXT,
            allow_unsubscribe INTEGER CHECK(allow_unsubscribe IN (0,1)) DEFAULT 1
        )
        ''')
        
        cursor.execute('SELECT COUNT(*) FROM settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO settings (delete_time, welcome_message, allow_user_filters, allow_newsletter_unsubscribe) VALUES (?, ?, ?, ?)', 
                           (30, "👋 به ربات ما خوش اومدی!", 0, 1))
            cursor.execute('INSERT OR REPLACE INTO messages (key, text) VALUES (?, ?)', ("welcome", "👋 به ربات ما خوش اومدی!"))
        conn.commit()

def get_settings():
    with get_connection() as conn:
        cursor = conn.cursor()
        settings = cursor.execute('SELECT * FROM settings').fetchone()
        if settings:
            return settings
        return (30, "👋 به ربات ما خوش اومدی!", 0, 1)

def update_settings(**kwargs):
    with get_connection() as conn:
        cursor = conn.cursor()
        for key, value in kwargs.items():
            cursor.execute(f'UPDATE settings SET {key} = ?', (value,))
        
        cursor.execute('SELECT COUNT(*) FROM settings')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO settings (delete_time, welcome_message, allow_user_filters, allow_newsletter_unsubscribe) VALUES (?, ?, ?, ?)', 
                           (kwargs.get('delete_time', 30), kwargs.get('welcome_message', "👋 به ربات ما خوش اومدی!"), kwargs.get('allow_user_filters', 0), kwargs.get('allow_newsletter_unsubscribe', 1)))
        conn.commit()

def get_messages():
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute('SELECT key, text FROM messages').fetchall()
        if not rows:
            return {"welcome": "👋 به ربات ما خوش اومدی!"}
        return {key: text for key, text in rows}

def update_message(key, text):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO messages (key, text) VALUES (?, ?)', (key, text))
        conn.commit()

def get_channels():
    with get_connection() as conn:
        cursor = conn.cursor()
        return cursor.execute('SELECT * FROM check_channels').fetchall()

def set_channel(name, channel_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO check_channels (name, id, joins) VALUES (?, ?, 0)', (name, channel_id))
        conn.commit()

def delete_channel(channel_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM check_channels WHERE id = ?', (channel_id,))
        conn.commit()

def add_file_info(file_id: str, description: str = None, file_type: str = "document", media_group_id: str = None, password: str = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO files (file_id, file_type, description, views, password, auto_remove, media_group_id)
        VALUES (?, ?, ?, 0, ?, 1, ?)
        ''', (file_id, file_type, description, password, media_group_id))
        conn.commit()
        return cursor.execute('SELECT * FROM files WHERE rowid = last_insert_rowid()').fetchone()

def check_password(file_id: int, password: str) -> bool:
    file = get_file(file_id)
    if file and file[5]:
        return file[5] == password
    return True

def check_file(file_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        files = cursor.execute('SELECT id FROM files WHERE id = ?', (file_id,)).fetchall()
        return len(files) > 0

def get_file(file_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        return cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()

def save_user(user_id: int, admin: int = 0):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO users (user_id, admin, date_added) VALUES (?, ?, ?)', (user_id, admin, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()

def get_file_view(file_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        return cursor.execute('SELECT COUNT(*) FROM user_views WHERE file_id = ?', (file_id,)).fetchone()[0]

def view_file(user_id: int, file_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        file = get_file(file_id)
        user_exists = cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)).fetchone()
        file_exists = cursor.execute('SELECT file_id FROM files WHERE id = ?', (file_id,)).fetchone()
        if user_exists and file_exists:
          view_exists = cursor.execute('SELECT * FROM user_views WHERE user_id = ? AND file_id = ?', (user_id, file_exists[0])).fetchone()
          if not view_exists:
            cursor.execute('''
            INSERT INTO user_views (user_id, file_id)
            VALUES (?, ?)
            ''', (user_exists[0], file_exists[0]))
            conn.commit()

def get_users():
    with get_connection() as conn:
        cursor = conn.cursor()
        return [row[0] for row in cursor.execute('SELECT user_id FROM users').fetchall()]

def get_admins():
    with get_connection() as conn:
        cursor = conn.cursor()
        return [row[0] for row in cursor.execute('SELECT user_id FROM users WHERE admin = 1').fetchall()]

def get_user_stats(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        views = cursor.execute('SELECT COUNT(*) FROM user_views WHERE user_id = ?', (user_id,)).fetchone()[0]
        recent_files = cursor.execute('SELECT file_id, view_time FROM user_views WHERE user_id = ? ORDER BY view_time DESC LIMIT 5', (user_id,)).fetchall()
        user_info = cursor.execute('SELECT user_id, date_added, admin FROM users WHERE user_id = ?', (user_id,)).fetchone()
        newsletter_status = cursor.execute('SELECT subscribed_at, allow_unsubscribe FROM newsletter WHERE user_id = ?', (user_id,)).fetchone()
        return {
            "views": views,
            "recent_files": recent_files,
            "user_id": user_info[0] if user_info else None,
            "date_added": user_info[1] if user_info else None,
            "is_admin": bool(user_info[2]) if user_info else False,
            "newsletter_subscribed": bool(newsletter_status),
            "newsletter_allow_unsubscribe": newsletter_status[1] if newsletter_status else True
        }

def subscribe_newsletter(user_id: int, allow_unsubscribe: int = 1):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO newsletter (user_id, subscribed_at, allow_unsubscribe) VALUES (?, ?, ?)', (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), allow_unsubscribe))
        conn.commit()

def unsubscribe_newsletter(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        allow_unsubscribe = cursor.execute('SELECT allow_unsubscribe FROM newsletter WHERE user_id = ?', (user_id,)).fetchone()
        if allow_unsubscribe and allow_unsubscribe[0]:
            cursor.execute('DELETE FROM newsletter WHERE user_id = ?', (user_id,))
            conn.commit()
            return True
        return False

def set_newsletter_unsubscribe(user_id: int, allow: bool):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE newsletter SET allow_unsubscribe = ? WHERE user_id = ?', (1 if allow else 0, user_id))
        conn.commit()

def is_subscribed_newsletter(user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        subscribed = cursor.execute('SELECT user_id FROM newsletter WHERE user_id = ?', (user_id,)).fetchone()
        return subscribed is not None

def schedule_file(file_id: int, schedule_time: str):
    try:
        jdatetime.datetime.strptime(schedule_time, '%Y-%m-%d %H:%M')
    except ValueError:
        raise ValueError("فرمت تاریخ نامعتبر است! لطفاً از فرمت 1404-05-17 14:30 استفاده کنید.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET scheduled_time = ? WHERE id = ?', (schedule_time, file_id))
        conn.commit()

def get_scheduled_files():
    with get_connection() as conn:
        cursor = conn.cursor()
        return cursor.execute('SELECT * FROM files WHERE scheduled_time IS NOT NULL').fetchall()

def get_suggested_files(file_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        file = get_file(file_id)
        if not file:
            return []
        return cursor.execute('SELECT * FROM files WHERE file_type = ? AND id != ? LIMIT 2', (file[2], file_id)).fetchall()

def get_all_files(file_type: str = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if file_type:
            return cursor.execute('SELECT * FROM files WHERE file_type = ?', (file_type,)).fetchall()
        return cursor.execute('SELECT * FROM files').fetchall()

def delete_file_with_id(id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE id = ?', (id,))
        conn.commit()
        return cursor.rowcount > 0

def delete_file_with_fileid(file_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE file_id = ?', (file_id,))
        conn.commit()
        return cursor.rowcount > 0

init_db()