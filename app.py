import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, Response

from werkzeug.security import generate_password_hash, check_password_hash
from hashids import Hashids
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure key
hashids = Hashids(min_length=8, salt='your_salt')

# Database initialization
def init_db():
    with sqlite3.connect('database.db') as connection:
        cursor = connection.cursor()
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            original_url TEXT NOT NULL,
            short_url TEXT UNIQUE NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0,
            expiry TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        ''')
        connection.commit()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    default_expiry = datetime.now() + timedelta(hours=24)
    default_expiry_str = default_expiry.strftime('%Y-%m-%d %H:%M')

    if request.method == 'POST':
        original_url = request.form['url']
        expiry = request.form.get('expiry', default_expiry_str)

        if not original_url:
            flash('Please enter a URL.')
            return redirect(url_for('index'))

        short_url_code = hashids.encode(len(get_urls()) + 1)
        short_url = url_for('redirect_url', short_url=short_url_code, _external=True)
        conn = get_db_connection()

        try:
            conn.execute('INSERT INTO urls (original_url, short_url, expiry) VALUES (?, ?, ?)', (original_url, short_url_code, expiry))
            conn.commit()
            flash('URL shortened successfully!')
        except sqlite3.IntegrityError:
            flash('Short URL already exists.')
        finally:
            conn.close()

        return render_template('index.html', short_url=short_url, expiry=expiry)

    return render_template('index.html', expiry=default_expiry_str)

@app.route('/<short_url>')
def redirect_url(short_url):
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (short_url,)).fetchone()
    conn.close()

    if url is None:
        return 'URL not found', 404
    
    expiry = datetime.strptime(url['expiry'], '%Y-%m-%d %H:%M')
    if datetime.now() > expiry:
        conn = get_db_connection()
        conn.execute('DELETE FROM urls WHERE short_url = ?', (short_url,))
        conn.commit()
        conn.close()
        return 'URL has expired', 410

    conn = get_db_connection()
    conn.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_url = ?', (short_url,))
    conn.commit()
    conn.close()

    print(f'Redirecting to: {url["original_url"]}')  # Debugging line
    return redirect(url['original_url'])


@app.route('/stats')
def stats():
    urls = get_urls()
    print(urls)  # Debugging line
    return render_template('stats.html', urls=urls, hashids=hashids)

@app.route('/sitemap.xml')
def sitemap():
    urls = [
        {'loc': url_for('home', _external=True)},
        {'loc': url_for('index', _external=True)},
        {'loc': url_for('stats', _external=True)},
        {'loc': url_for('privacy_policy', _external=True)},
    ]
    xml = render_template('sitemap.xml', urls=urls, now=datetime.now())
    return Response(xml, mimetype='application/xml')


@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/delete_url/<id>', methods=['POST'])
def delete_url(id):
    url_id = hashids.decode(id)
    if not url_id:
        flash('Invalid URL ID.')
        return redirect(url_for('stats'))

    url_id = url_id[0]
    conn = get_db_connection()
    conn.execute('DELETE FROM urls WHERE id = ?', (url_id,))
    conn.commit()
    conn.close()
    flash('URL deleted successfully.')
    return redirect(url_for('stats'))

def get_urls():
    conn = get_db_connection()
    urls = conn.execute('SELECT * FROM urls').fetchall()
    conn.close()
    return urls

if __name__ == '__main__':
    app.run(debug=True)
