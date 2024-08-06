import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from hashids import Hashids
from datetime import datetime, timedelta

import requests

def get_location_from_ip(ip_address):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}')
        data = response.json()
        return data.get('city', '') + ', ' + data.get('country', '')
    except requests.RequestException:
        return ''

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure key
hashids = Hashids(min_length=8, salt='your_salt')

# Database initialization
def init_db():
    with sqlite3.connect('database.db') as connection:
        cursor = connection.cursor()
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

@app.route('/url_shortener', methods=['GET', 'POST'])
def url_shortener():
    default_expiry = datetime.now() + timedelta(hours=24)
    default_expiry_str = default_expiry.strftime('%Y-%m-%d %H:%M')

    if request.method == 'POST':
        original_url = request.form['url']
        expiry = request.form.get('expiry', default_expiry_str)

        if not original_url:
            flash('Please enter a URL.')
            return redirect(url_for('url_shortener'))

        short_url_code = hashids.encode(len(get_urls()) + 1)
        short_url = url_for('redirect_url', short_url=short_url_code, _external=True)
        
        # Retrieve the real IP address
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        location = get_location_from_ip(ip_address)  # Get location from IP address

        conn = get_db_connection()

        try:
            conn.execute('INSERT INTO urls (original_url, short_url, expiry, ip_address, location) VALUES (?, ?, ?, ?, ?)', 
                         (original_url, short_url_code, expiry, ip_address, location))
            conn.commit()
            flash('URL shortened successfully!')
        except sqlite3.IntegrityError:
            flash('Short URL already exists.')
        finally:
            conn.close()

        return render_template('url_shortener.html', short_url=short_url, expiry=expiry)

    return render_template('url_shortener.html', expiry=default_expiry_str)

@app.route('/<short_url>')
def redirect_url(short_url):
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (short_url,)).fetchone()
    if url is None:
        return 'URL not found', 404
    
    expiry = datetime.strptime(url['expiry'], '%Y-%m-%d %H:%M')
    if datetime.now() > expiry:
        conn.execute('DELETE FROM urls WHERE short_url = ?', (short_url,))
        conn.commit()
        conn.close()
        return 'URL has expired', 410

    # Update click count only
    conn.execute('UPDATE urls SET clicks = clicks + 1 WHERE short_url = ?', (short_url,))
    conn.commit()
    conn.close()

    return redirect(url['original_url'])

@app.route('/stats')
def stats():
    urls = get_urls()
    print(urls)  # Debugging line
    return render_template('stats.html', urls=urls, hashids=hashids)

@app.route('/sitemap.xml')
def sitemap():
    urls = [
        {'loc': url_for('url_shortener', _external=True)},
        {'loc': url_for('home', _external=True)},
        {'loc': url_for('privacy_policy', _external=True)},
        {'loc': url_for('robots_txt', _external=True)},
        {'loc': url_for('sitemap', _external=True)},
    ]
    xml = render_template('sitemap.xml', urls=urls, now=datetime.now())
    return Response(xml, mimetype='application/xml')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/delete_url/<int:id>', methods=['POST'])
def delete_url(id):
    # Directly use the integer ID without decoding since it's coming as an integer
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM urls WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        flash('Failed to delete URL. It may not exist.')
    else:
        flash('URL deleted successfully.')

    return redirect(url_for('stats'))

def get_urls():
    conn = get_db_connection()
    urls = conn.execute('SELECT * FROM urls').fetchall()
    conn.close()
    return urls

@app.route('/robots.txt', methods=['GET','POST'])
def robots_txt():
    return send_from_directory(app.root_path, 'robots.txt')

@app.route('/all_urls', methods=['GET','POST'])
def all_urls():
    urls = get_urls()
    return render_template('all_urls.html', urls=urls, hashids=hashids)

# if __name__ == '__main__':
#     app.run(debug=True)
