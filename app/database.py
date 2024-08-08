import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executescript('''
        DROP TABLE IF EXISTS urls;
        DROP TABLE IF EXISTS users;

        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            original_url TEXT NOT NULL,
            short_url TEXT UNIQUE NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0,
            expiry TEXT NOT NULL,
            ip_address TEXT,
            location TEXT
        );

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        ''')
        conn.commit()
