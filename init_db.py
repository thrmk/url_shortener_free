def init_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    
    cursor.executescript('''
    DROP TABLE IF EXISTS urls;
    DROP TABLE IF EXISTS users;

    CREATE TABLE urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        original_url TEXT NOT NULL,
        clicks INTEGER NOT NULL DEFAULT 0,
        expiry TIMESTAMP NOT NULL DEFAULT (DATETIME('now', '+2 days')),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    ''')
    
    connection.commit()
    connection.close()
