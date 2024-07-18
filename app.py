import sqlite3
from datetime import datetime, timedelta
from hashids import Hashids
from flask import Flask, render_template, request, flash, redirect, url_for, session, g, Response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

def init_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        original_url TEXT NOT NULL,
        clicks INTEGER NOT NULL DEFAULT 0,
        expiry TIMESTAMP NOT NULL DEFAULT (DATETIME('now', '+2 days')),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );
    ''')
    
    connection.commit()
    connection.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def delete_expired_urls(conn):
    conn.execute("DELETE FROM urls WHERE expiry < DATETIME('now')")
    conn.commit()

app = Flask(__name__)
app.secret_key = 'manoj'
hashids = Hashids(min_length=8, salt=app.secret_key)

# Set a flag to track app initialization
app.config['FIRST_START'] = True
app.config['SESSION_COOKIE_NAME'] = 'manoj_cookie'

@app.before_request
def load_logged_in_user():
    g.user = session.get('user_id')
    
    # Clear all sessions on first start
    if app.config['FIRST_START']:
        session.clear()
        app.config['FIRST_START'] = False
        return redirect(url_for('login'))

@app.route('/')
def home():
    if g.user is None:
        return redirect(url_for('login'))
    return redirect(url_for('shorten'))

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required!')
            return redirect(url_for('register'))

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, generate_password_hash(password)))
            conn.commit()
            conn.close()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('Username already exists!')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('shorten'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

@app.route('/shorten', methods=('GET', 'POST'))
def shorten():
    if g.user is None:
        return redirect(url_for('login'))

    conn = get_db_connection()
    delete_expired_urls(conn)

    if request.method == 'POST':
        url = request.form['url']

        if not url:
            flash('The URL is required!')
            return redirect(url_for('shorten'))

        url_data = conn.execute(
            "SELECT id FROM urls WHERE original_url = ? AND expiry >= DATETIME('now')",
            (url,)
        ).fetchone()

        if url_data:
            url_id = url_data['id']
        else:
            url_data = conn.execute(
                'INSERT INTO urls (user_id, original_url, expiry) VALUES (?, ?, ?)',
                (g.user, url, datetime.now() + timedelta(days=2))
            )
            conn.commit()
            url_id = url_data.lastrowid

        conn.close()

        hashid = hashids.encode(url_id)
        short_url = request.host_url + hashid

        return render_template('index.html', short_url=short_url)

    return render_template('index.html')

@app.route('/<id>')
def url_redirect(id):
    conn = get_db_connection()
    delete_expired_urls(conn)

    original_id = hashids.decode(id)
    if original_id:
        original_id = original_id[0]
        url_data = conn.execute(
            'SELECT original_url, clicks FROM urls WHERE id = ? AND expiry >= DATETIME("now")',
            (original_id,)
        ).fetchone()
        
        if url_data:
            original_url = url_data['original_url']
            clicks = url_data['clicks']

            conn.execute(
                'UPDATE urls SET clicks = ? WHERE id = ?',
                (clicks + 1, original_id)
            )

            conn.commit()
            conn.close()
            return redirect(original_url)

    conn.close()
    flash('Invalid or expired URL')
    return redirect(url_for('shorten'))

@app.route('/stats')
def stats():
    if g.user is None:
        return redirect(url_for('login'))

    conn = get_db_connection()
    delete_expired_urls(conn)

    db_urls = conn.execute(
        '''
        SELECT urls.id, urls.created, urls.original_url, urls.clicks, urls.expiry, users.username 
        FROM urls 
        JOIN users ON urls.user_id = users.id 
        WHERE urls.expiry >= DATETIME("now") AND urls.user_id = ?
        ''', (g.user,)
    ).fetchall()
    conn.close()

    urls = []
    for url in db_urls:
        url = dict(url)
        url['short_url'] = request.host_url + hashids.encode(url['id'])
        urls.append(url)

    return render_template('stats.html', urls=urls, hashids=hashids)

@app.route('/delete/<id>', methods=['POST'])
def delete_url(id):
    if g.user is None:
        return redirect(url_for('login'))

    conn = get_db_connection()
    delete_expired_urls(conn)

    original_id = hashids.decode(id)
    if original_id:
        original_id = original_id[0]
        conn.execute('DELETE FROM urls WHERE id = ?', (original_id,))
        conn.commit()
        conn.close()
        flash('URL deleted successfully!')
    else:
        conn.close()
        flash('Invalid URL ID!')

    return redirect(url_for('stats'))

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    static_urls = [
        {'loc': url_for('home', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'loc': url_for('register', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'loc': url_for('login', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'loc': url_for('logout', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'loc': url_for('shorten', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
        {'loc': url_for('stats', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')},
    ]

    sitemap_xml = render_template('sitemap.xml', urls=static_urls)
    response = Response(sitemap_xml, content_type='application/xml')
    return response

@app.route('/robots.txt', methods=['GET'])
def robots_txt():
    return send_from_directory(app.root_path, 'robots.txt')

# if __name__ == '__main__':
#     app.run(host="0.0.0.0",port=5000)
